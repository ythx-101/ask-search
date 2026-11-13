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
  SEARXNG_URL       SearxNG endpoint (default: http://localhost:8080)
  SEARCH_PROVIDER   "searxng" (default), "tavily" or "youcom"
  TAVILY_API_KEY    Tavily API key (required when SEARCH_PROVIDER=tavily)
  YDC_API_KEY       You.com API key (optional when SEARCH_PROVIDER=youcom; works without one)
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
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY env var is not set")
    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=min(num, 20), search_depth="basic")
    return response.get("results", [])

# --- You.com support (opt-in via SEARCH_PROVIDER=youcom; no key needed) ---

YOUCOM_KEYLESS_URL = "https://api.you.com/v1/agents/search"
YOUCOM_KEYED_URL = "https://ydc-index.io/v1/search"
YOUCOM_USER_AGENT = "youdotcom-integration/ythx-101-ask-search"
YOUCOM_MAX_COUNT = 50  # keyless endpoint rejects count > 50


def _youcom_normalize(item):
    snippets = item.get("snippets") or []
    content = (item.get("description") or "").strip()
    if not content and snippets:
        content = " ".join(s.strip() for s in snippets if s)
    out = {"title": item.get("title", ""), "url": item.get("url", ""), "content": content}
    if item.get("page_age"):
        out["publishedDate"] = item["page_age"]
    return out


def youcom_search(query, num=10, news=False):
    """Search via You.com. Keyless by default; YDC_API_KEY switches to the keyed API."""
    count = max(1, min(int(num), YOUCOM_MAX_COUNT))
    api_key = os.environ.get("YDC_API_KEY", "").strip()
    cmd = ["curl", "-sS", "--max-time", "15", "-w", "\n%{http_code}",
           "-A", YOUCOM_USER_AGENT]
    stdin = None
    if api_key:
        # Key goes in via stdin so it doesn't show up in the process list.
        cmd += ["-X", "POST", "-H", "Content-Type: application/json", "-H", "@-",
                "--data-raw", json.dumps({"query": query, "count": count}), YOUCOM_KEYED_URL]
        stdin = f"X-API-Key: {api_key}\n"
    else:
        cmd += [YOUCOM_KEYLESS_URL + "?" + urllib.parse.urlencode({"query": query, "count": count})]
    result = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=20)
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr[:200]}")
    body, _, status = result.stdout.rpartition("\n")
    if status in ("401", "403"):
        raise RuntimeError("You.com rejected YDC_API_KEY (HTTP %s)" % status)
    if status == "429":
        raise RuntimeError("You.com rate limit hit (HTTP 429). Set YDC_API_KEY for higher limits.")
    if not status.startswith("2"):
        raise RuntimeError(f"You.com returned HTTP {status}: {body[:120]}")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise RuntimeError("You.com did not return JSON: " + body[:120])
    sections = data.get("results") or {}
    web = sections.get("web") or []
    news_items = sections.get("news") or []
    items = news_items + web if news else web + news_items
    results = [_youcom_normalize(i) for i in items if i.get("url")]
    return results[:num]

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
        ["curl", "-sS", "--max-time", "15", url],
        capture_output=True, text=True, timeout=20
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr[:200]}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(
            "SearxNG did not return JSON (is 'json' enabled in search.formats?): "
            + result.stdout[:120]
        )
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
        provider = _get_search_provider()
        if provider == "tavily":
            results = tavily_search(args.query, args.num)
        elif provider == "youcom":
            results = youcom_search(args.query, args.num,
                                    news="news" in (args.categories or ""))
        else:
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
