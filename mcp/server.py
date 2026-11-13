#!/usr/bin/env python3
"""
ask-search MCP Server — for Antigravity / Claude Code MCP integration

Requires Python 3.10+ (required by the `mcp` package).

Install:
  pip install mcp

Optional: set TAVILY_API_KEY in the "env" block to enable the web_search_tavily tool.
The web_search_youcom tool works with no key; set YDC_API_KEY for higher limits.

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

from core import searxng_search, search, tavily_search, youcom_search

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
def web_search_youcom(query: str, num_results: int = 10) -> str:
    """
    Search the web via You.com. Returns JSON array of results with title, url, content.
    Works without an API key. Set YDC_API_KEY for higher limits.

    Args:
        query: Search query string
        num_results: Number of results to return (default 10, max 20)
    """
    import json
    try:
        results = youcom_search(query, min(num_results, 20))
        return json.dumps({"query": query, "results": results}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()
