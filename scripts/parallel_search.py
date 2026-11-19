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

    response_error = None

    def reject_response(method, error):
        nonlocal response_error
        if method == "POST":
            # The SDK can consume transport errors without waking the pending RPC.
            response_error = error
            search_scope.cancel()
        raise RuntimeError(error)

    class LimitedStream(httpx.AsyncByteStream):
        def __init__(self, stream, method):
            self.stream = stream
            self.method = method

        async def __aiter__(self):
            size = 0
            async for chunk in self.stream:
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    reject_response(self.method, "Parallel Search response exceeded 1 MiB")
                yield chunk

        async def aclose(self):
            await self.stream.aclose()

    async def limit_response(response):
        method = response.request.method
        if method == "POST" and response.is_error:
            if response.status_code == 429:
                reject_response(method, "Parallel Search is rate limited (HTTP 429)")
            reject_response(method, f"Parallel Search request failed (HTTP {response.status_code})")

        # Streamable HTTP can return JSON or SSE. Bound either before the SDK
        # reads it, and keep the limit meaningful by requesting identity encoding.
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            await response.aclose()
            reject_response(method, "Unexpected Parallel Search response encoding")
        response.stream = LimitedStream(response.stream, method)

    result = None
    try:
        with anyio.move_on_after(SEARCH_TIMEOUT) as search_scope:
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
    except Exception:
        if result is None:
            raise RuntimeError(response_error or "Parallel Search request failed") from None

    if result is None:
        raise RuntimeError(response_error or "Parallel Search timed out")
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
        if not isinstance(url, str) or any(char.isspace() or ord(char) < 32 or char == "\x7f" for char in url):
            raise RuntimeError("Invalid Parallel Search result")
        try:
            source = urlsplit(url)
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
