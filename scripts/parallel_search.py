"""Anonymous Parallel Search MCP adapter."""

from urllib.parse import urlsplit

from core import VERSION

PARALLEL_MCP_URL = "https://mcp.parallel.ai/mcp"
MAX_RESPONSE_BYTES = 1024 * 1024
SEARCH_TIMEOUT = 20


async def parallel_search(query, num=10):
    if not query.strip():
        raise RuntimeError("Parallel requires a non-empty search query")
    if num < 1:
        raise RuntimeError("Parallel requires a positive result limit")

    try:
        import anyio
        import httpx
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
    except ImportError:
        raise RuntimeError("Parallel requires Python 3.10+ and pip install 'mcp>=1.30,<2'") from None

    class LimitedStream(httpx.AsyncByteStream):
        def __init__(self, stream):
            self.stream = stream

        async def __aiter__(self):
            size = 0
            async for chunk in self.stream:
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    raise RuntimeError("Parallel Search response exceeded 1 MiB")
                yield chunk

        async def aclose(self):
            await self.stream.aclose()

    async def limit_response(response):
        # Streamable HTTP can return JSON or SSE. Bound either before the SDK
        # reads it, and keep the limit meaningful by requesting identity encoding.
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            await response.aclose()
            raise RuntimeError("Unexpected Parallel Search response encoding")
        response.stream = LimitedStream(response.stream)

    result = None
    try:
        with anyio.fail_after(SEARCH_TIMEOUT):
            async with httpx.AsyncClient(
                headers={"User-Agent": f"ask-search/{VERSION}", "Accept-Encoding": "identity"},
                timeout=15,
                event_hooks={"response": [limit_response]},
            ) as client:
                async with streamable_http_client(PARALLEL_MCP_URL, http_client=client) as (reader, writer, _):
                    async with ClientSession(reader, writer) as session:
                        await session.initialize()
                        result = await session.call_tool(
                            "web_search", {"objective": query, "search_queries": [query]}
                        )
    except TimeoutError:
        if result is None:
            raise RuntimeError("Parallel Search timed out") from None
    except Exception:
        if result is None:
            raise RuntimeError("Parallel Search request failed") from None

    if result.isError:
        raise RuntimeError("Parallel Search returned a tool error")

    payload = result.structuredContent
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise RuntimeError("Invalid Parallel Search results")

    results = []
    for item in payload["results"][:num]:
        if not isinstance(item, dict):
            raise RuntimeError("Invalid Parallel Search result")
        url, title, excerpts = item.get("url"), item.get("title"), item.get("excerpts")
        try:
            source = urlsplit(url) if isinstance(url, str) else None
        except ValueError:
            source = None
        if (
            not source or source.scheme not in ("http", "https") or not source.hostname
            or source.username is not None or (title is not None and not isinstance(title, str))
            or not isinstance(excerpts, list) or not all(isinstance(text, str) for text in excerpts)
        ):
            raise RuntimeError("Invalid Parallel Search result")
        results.append({"title": title or "", "url": url, "content": "\n\n".join(excerpts)})
    return results
