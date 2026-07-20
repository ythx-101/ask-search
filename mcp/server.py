#!/usr/bin/env python3
"""
ask-search MCP Server — for Antigravity / Claude Code MCP integration

Install:
  pip install mcp

Add to your MCP config:
  {
    "mcpServers": {
      "ask-search": {
        "command": "python3",
        "args": ["/path/to/ask-search/mcp/server.py"],
        "env": {"SEARXNG_URL": "http://localhost:8080"}
      }
    }
  }
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

from core import searxng_search, search, fmt_results, tavily_search

# Router de datasources — fuente de verdad para búsqueda regional y
# triangulación (instalado via `pip install -e datasources/`). Import lazy:
# si datasources no está instalado, las tools regionales fallan con error
# claro pero las tools SearxNG/Tavily básicas siguen operando.
_router = None
def _get_router():
    global _router
    if _router is None:
        from datasources.router import SocialRouter
        _router = SocialRouter()
    return _router

mcp = FastMCP("ask-search")

@mcp.tool()
def web_search(query: str, num_results: int = 10) -> str:
    """
    Search the web via SearxNG. Returns JSON array of results with title, url, content.
    Aggregates Google, Bing, DuckDuckGo, Brave and more.

    Args:
        query: Search query string
        num_results: Number of results to return (default 10, max 20)
    """
    return searxng_search(query, min(num_results, 20))

@mcp.tool()
def web_search_news(query: str, num_results: int = 10) -> str:
    """
    Search recent news via SearxNG news category.

    Args:
        query: News search query
        num_results: Number of results (default 10)
    """
    try:
        results = search(query, num_results, categories="news")
        import json
        return json.dumps({"query": query, "category": "news", "results": results}, ensure_ascii=False, indent=2)
    except Exception as e:
        import json
        return json.dumps({"error": str(e)})

@mcp.tool()
def web_search_tavily(query: str, num_results: int = 10) -> str:
    """
    Search the web via Tavily API. Returns JSON array of results with title, url, content.
    Requires TAVILY_API_KEY env var to be set.

    Args:
        query: Search query string
        num_results: Number of results to return (default 10, max 20)
    """
    import json
    try:
        results = tavily_search(query, min(num_results, 20))
        return json.dumps({"query": query, "results": results}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def list_regions() -> str:
    """
    List region codes supported by search_regional (regional search via SearxNG).

    Returns a JSON array of region codes (RU/CN/KR/JP/EU/US) with labels and
    which SearxNG engines each region targets.
    """
    import json
    try:
        from datasources.social.regional_search import REGIONS
        info = [
            {"code": code, "label": cfg["label"], "engines": cfg["engines"], "lang": cfg["lang"]}
            for code, cfg in REGIONS.items()
        ]
        return json.dumps({"regions": info}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def search_regional(query: str, region: str, num_results: int = 10) -> str:
    """
    Search a query on the search engines of a specific region via SearxNG.

    Use this to contrast information across regions — same query, different
    origins (Yandex for RU, Baidu/Sogou for CN, Naver for KR, etc.). Each
    result carries metadata: region, region_label, engines_responded (which
    engines actually returned data).

    Args:
        query: Search query. Use the region's language for better coverage
               (e.g. Cyrillic for RU, Chinese for CN, Korean for KR).
        region: Region code — RU, CN, KR, JP, EU, or US.
        num_results: Number of results (default 10).
    """
    import json
    try:
        router = _get_router()
        items = router.search_regional(query, region.upper(), count=min(num_results, 20))
        if not items:
            return json.dumps({
                "query": query, "region": region.upper(),
                "results": [],
                "note": "No results — regional engines may be blocked from this IP. "
                        "Check engines_responded metadata when results exist.",
            }, ensure_ascii=False, indent=2)
        return json.dumps({
            "query": query, "region": region.upper(),
            "region_label": items[0].get("region_label", ""),
            "engines_tried": items[0].get("region_engines_tried", []),
            "results": items,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def search_engines(query: str, engines: str, lang: str = "en", num_results: int = 10) -> str:
    """
    Search a query on specific SearxNG engines (low-level, power-user).

    Use this when you need exact control over which engines to query (e.g.
    "yandex,bing" or "google scholar,semantic scholar"). For regional
    presets, prefer search_regional.

    Args:
        query: Search query string.
        engines: Comma-separated SearxNG engine names (e.g. "yandex,baidu").
        lang: BCP47 language code (ru-RU, zh-CN, ko-KR, ja-JP, en, es, ...).
        num_results: Number of results (default 10).
    """
    import json
    try:
        from datasources.social.searxng import search_with_engines
        engine_list = [e.strip() for e in engines.split(",") if e.strip()]
        items = search_with_engines(query, engine_list, lang=lang, limit=min(num_results, 20))
        if not items:
            return json.dumps({"query": query, "engines": engine_list, "results": []},
                              ensure_ascii=False, indent=2)
        return json.dumps({"query": query, "engines": engine_list, "results": items},
                          ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def triangulate(query: str, regions: str = "", limit_per_region: int = 5) -> str:
    """
    Run the same query across multiple regions in parallel and contrast results.

    Designed for deep research: identifies claims circulating in one geographic
    block but not another (information divergence). De-duplicates by URL.
    Each claim carries: regions_covering, engines_covering, coverage_score,
    divergence_flag (appeared in eastern XOR western block, not both),
    eastern_only, western_only.

    Eastern block = RU/CN/KR/JP. Western block = US/EU. Claims with
    divergence_flag=True appear on top (most interesting for contrasting
    sources).

    Args:
        query: Search query (neutral-language or run multiple times with
               translations for best regional coverage).
        regions: Comma-separated region codes. Empty = all 6 (RU,CN,KR,JP,EU,US).
        limit_per_region: Max results per region (default 5).
    """
    import json
    try:
        router = _get_router()
        region_list = [r.strip().upper() for r in regions.split(",") if r.strip()] or None
        result = router.triangulate(query, regions=region_list, limit_per_region=limit_per_region)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()