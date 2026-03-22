#!/usr/bin/env python3
"""
ask-search v1.0.0 — Cross-environment SearxNG search skill

Works in: OpenClaw (CLI) | Claude Code (CLI) | Antigravity (MCP)

Usage:
  ask-search "query"                    # top 10 results
  ask-search "query" --num 5            # limit results
  ask-search "AI news" --categories news
  ask-search "query" --lang zh-CN
  ask-search "query" --urls-only        # URL list only (pipe to web_fetch)
  ask-search "query" --json             # raw JSON output

Environment:
  SEARXNG_URL   SearxNG endpoint (default: http://localhost:8080)
"""
import sys, json, urllib.parse, argparse, os, subprocess

VERSION = "1.0.0"

# --- Tavily support (opt-in via SEARCH_PROVIDER=tavily + TAVILY_API_KEY) ---

def _get_search_provider():
    return os.environ.get("SEARCH_PROVIDER", "searxng").lower()

def tavily_search(query, num=10):
    """Search via Tavily API. Requires tavily-python and TAVILY_API_KEY."""
    try:
        from tavily import TavilyClient
    except ImportError:
        raise RuntimeError("tavily-python not installed. Run: pip install tavily-python")
    client = TavilyClient()
    response = client.search(query=query, max_results=min(num, 20), search_depth="basic")
    return response.get("results", [])

def _search_url():
    base = os.environ.get("SEARXNG_URL", "http://localhost:8080")
    return base.rstrip("/") + "/search"

def search(query, num=10, engines=None, lang=None, categories=None):
    params = {"q": query, "format": "json", "pageno": 1}
    if engines:    params["engines"] = engines
    if lang:       params["language"] = lang
    if categories: params["categories"] = categories

    url = _search_url() + "?" + urllib.parse.urlencode(params)
    # Use subprocess curl to avoid urllib HTTP/1.0 compatibility issues
    result = subprocess.run(
        ["curl", "-s", "--max-time", "15", url],
        capture_output=True, text=True, timeout=20
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr[:200]}")
    data = json.loads(result.stdout)
    return data.get("results", [])[:num]

def fmt_results(results, urls_only=False):
    if urls_only:
        return "\n".join(r.get("url", "") for r in results)
    lines = []
    for i, r in enumerate(results, 1):
        title   = r.get("title", "").strip()
        url     = r.get("url", "")
        content = r.get("content", "").strip()
        engines = ",".join(r.get("engines", []))
        lines.append(f"[{i}] {title}")
        lines.append(f"    {url}")
        if content: lines.append(f"    {content[:200]}")
        if engines: lines.append(f"    [{engines}]")
        lines.append("")
    return "\n".join(lines).strip()

def searxng_search(query, num=15):
    """MCP/legacy interface — returns JSON string"""
    try:
        results = search(query, num)
        return json.dumps({"query": query, "results": results}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

def main():
    p = argparse.ArgumentParser(description="SearxNG search (cross-environment)")
    p.add_argument("query")
    p.add_argument("--num",        "-n", type=int, default=10)
    p.add_argument("--engines",    "-e", help="google,bing,duckduckgo,brave")
    p.add_argument("--lang",       "-l", help="zh-CN, en, ja, ko")
    p.add_argument("--categories", "-c", help="general,news,images,science")
    p.add_argument("--json",       "-j", action="store_true")
    p.add_argument("--urls-only",  "-u", action="store_true")
    p.add_argument("--version",    "-V", action="version", version=f"ask-search {VERSION}")
    args = p.parse_args()

    try:
        results = search(args.query, args.num, args.engines, args.lang, args.categories)
    except Exception as e:
        print(json.dumps({"error": str(e)})); sys.exit(1)

    if not results:
        print(json.dumps({"error": "No results", "query": args.query})); sys.exit(1)

    if getattr(args, "json"):
        print(json.dumps({"query": args.query, "results": results}, ensure_ascii=False, indent=2))
    else:
        print(fmt_results(results, args.urls_only))

if __name__ == "__main__":
    main()
