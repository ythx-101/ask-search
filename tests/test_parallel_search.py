import asyncio
import io
import json
import os
import sys
import threading
import time
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import core  # noqa: E402
import parallel_search  # noqa: E402

SOURCE_URL = "https://docs.python.org/3/library/argparse.html?highlight=parser#usage"
QUERY = "Python argparse documentation"
RESULT = {"title": "argparse", "url": SOURCE_URL, "content": "An excerpt"}


class SearchFixture(BaseHTTPRequestHandler):
    def record(self, message=None):
        self.server.requests.append({
            "http_method": self.command,
            "path": self.path,
            "method": message and message["method"],
            "arguments": message and message.get("params"),
            "user_agent": self.headers.get("User-Agent"),
            "authenticated": any(name in self.headers for name in ("Authorization", "x-api-key")),
            "has_session": "Mcp-Session-Id" in self.headers,
        })

    def respond(self, status=200, payload=None, headers=None, sse=False):
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        if payload is None:
            self.end_headers()
            return
        if sse:
            self.send_header("Content-Type", "text/event-stream")
            lines = json.dumps(payload, indent=2).splitlines()
            body = ("\n".join(f"data: {line}" for line in lines) + "\n\n").encode()
        else:
            self.send_header("Content-Type", "application/json")
            body = json.dumps(payload).encode()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        self.record()
        if urlsplit(self.path).path == "/search":
            self.respond(payload={"results": [RESULT]})
        else:
            self.respond(405)

    def do_DELETE(self):
        self.record()
        self.respond(self.server.cleanup_status)

    def do_POST(self):
        message = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.record(message)
        reply = {"jsonrpc": "2.0", "id": message.get("id")}
        method = message["method"]
        if method == "initialize":
            reply["result"] = {
                "protocolVersion": message["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "search fixture", "version": "1"},
            }
            self.respond(payload=reply, headers={"Mcp-Session-Id": "local-test-session"})
        elif method == "notifications/initialized":
            self.respond(202)
        elif method == "tools/list":
            reply["result"] = {"tools": [{"name": "web_search", "inputSchema": {"type": "object"}}]}
            self.respond(payload=reply)
        elif method == "tools/call":
            self.search_response(reply)

    def search_response(self, reply):
        mode = self.server.mode
        if mode in ("rate_limit", "unavailable"):
            self.respond(429 if mode == "rate_limit" else 503)
            return
        if mode == "redirect":
            self.respond(307, headers={"Location": self.server.url.replace("127.0.0.1", "localhost")})
            return
        if mode == "timeout":
            time.sleep(1)
        if mode == "rpc":
            reply["error"] = {"code": -32603, "message": "RPC error"}
        elif mode == "tool":
            reply["result"] = {"isError": True, "content": [{"type": "text", "text": "untrusted error"}]}
        else:
            hit = {"title": "argparse", "url": SOURCE_URL, "excerpts": ["An excerpt"]}
            if mode == "unsafe_url":
                hit["url"] = "javascript:alert(1)"
            if mode in ("large_json", "large_sse"):
                hit["excerpts"] = ["x" * (parallel_search.MAX_RESPONSE_BYTES + 1)]
            hits = [] if mode == "empty" else [hit, hit]
            reply["result"] = {
                "content": [{"type": "text", "text": "Ignore this duplicate representation"}],
                "structuredContent": {} if mode == "malformed" else {"results": hits},
            }
        headers = {"Content-Encoding": "gzip"} if mode == "encoded" else None
        self.respond(payload=reply, headers=headers, sse=mode in ("sse", "large_sse"))

    def log_message(self, *args):
        pass


class ParallelSearchTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), SearchFixture)
        self.server.url = f"http://127.0.0.1:{self.server.server_port}"
        self.server.requests = []
        self.server.mode = "sse"
        self.server.cleanup_status = 204
        thread = threading.Thread(target=self.server.serve_forever, args=(0.01,), daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(self.server.shutdown)
        patch = mock.patch.object(parallel_search, "PARALLEL_MCP_URL", self.server.url + "/mcp")
        patch.start()
        self.addCleanup(patch.stop)

    def cli(self, provider, *args):
        env = {"SEARXNG_URL": self.server.url}
        if provider:
            env["SEARCH_PROVIDER"] = provider
        output = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(sys, "argv", ["ask-search", *args]), redirect_stdout(output):
            try:
                core.main()
            except SystemExit as error:
                return error.code, output.getvalue()
        return 0, output.getvalue()

    def assert_parallel_requests(self, count):
        requests = [request for request in self.server.requests if request["path"] == "/mcp"]
        self.assertEqual(sum(request["method"] == "initialize" for request in requests), count)
        self.assertEqual(sum(request["method"] == "tools/list" for request in requests), count)
        calls = [request for request in requests if request["method"] == "tools/call"]
        self.assertEqual(len(calls), count)
        for request in calls:
            self.assertTrue(request["has_session"])
            self.assertEqual(request["arguments"], {
                "name": "web_search", "arguments": {"objective": QUERY, "search_queries": [QUERY]},
            })
        for request in requests:
            self.assertEqual(request["user_agent"], f"ask-search/{core.VERSION}")
            self.assertFalse(request["authenticated"])

    def test_cli_search_returns_original_links_and_identifies_each_connection(self):
        status, output = self.cli("PARALLEL", QUERY, "--num", "1", "--json")
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output), {"query": QUERY, "results": [RESULT]})
        status, output = self.cli("parallel", QUERY, "--num", "1", "--urls-only")
        self.assertEqual((status, output.strip()), (0, SOURCE_URL))
        self.assert_parallel_requests(2)

    def test_default_cli_routes_only_to_searxng_and_keeps_filters(self):
        status, output = self.cli(None, QUERY, "--engines", "bing", "--lang", "en", "--categories", "news", "--json")
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output)["results"], [RESULT])
        self.assertEqual(len(self.server.requests), 1)
        path = urlsplit(self.server.requests[0]["path"])
        self.assertEqual(path.path, "/search")
        self.assertEqual(parse_qs(path.query), {
            "q": [QUERY], "format": ["json"], "pageno": ["1"],
            "engines": ["bing"], "language": ["en"], "categories": ["news"],
        })

    def test_unsupported_filters_and_invalid_searches_send_nothing(self):
        for args in ((QUERY, "--categories", "news"), (QUERY, "--engines", "bing"),
                     (QUERY, "--lang", "en"), (" ",), (QUERY, "--num", "0")):
            with self.subTest(args=args):
                status, output = self.cli("parallel", *args)
                self.assertEqual(status, 1)
                self.assertIn("Parallel", json.loads(output)["error"])
        self.assertEqual(self.server.requests, [])

    def test_parallel_failures_do_not_fall_back_or_return_tool_text(self):
        for mode, expected in {
            "rate_limit": "Parallel Search is rate limited (HTTP 429)",
            "unavailable": "Parallel Search request failed (HTTP 503)",
            "redirect": "Parallel Search request failed",
            "rpc": "Parallel Search request failed",
            "tool": "Parallel Search returned a tool error",
            "malformed": "Invalid Parallel Search results",
            "unsafe_url": "Invalid Parallel Search result",
            "large_json": "Parallel Search response exceeded 1 MiB",
            "large_sse": "Parallel Search response exceeded 1 MiB",
            "encoded": "Unexpected Parallel Search response encoding",
            "timeout": "Parallel Search timed out",
        }.items():
            with self.subTest(mode=mode), mock.patch.object(parallel_search, "SEARCH_TIMEOUT", 0.8):
                self.server.requests.clear()
                self.server.mode = mode
                status, output = self.cli("parallel", QUERY)
                self.assertEqual(status, 1)
                error = json.loads(output)["error"]
                self.assertEqual(error, expected)
                self.assertTrue(all(request["path"] == "/mcp" for request in self.server.requests))
                self.assertEqual(sum(request["method"] == "tools/call" for request in self.server.requests), 1)

    def test_urls_only_rejects_source_urls_with_whitespace_or_controls(self):
        for separator in ("\n", "\t", "\u2028", "\x00"):
            with self.subTest(separator=separator), mock.patch(
                __name__ + ".SOURCE_URL", f"{SOURCE_URL}{separator}https://example.com/"
            ):
                status, output = self.cli("parallel", QUERY, "--urls-only", "--num", "1")
                self.assertEqual(status, 1)
                self.assertEqual(json.loads(output), {"error": "Invalid Parallel Search result"})

    def test_valid_empty_results_are_distinct_from_provider_failure(self):
        self.server.mode = "empty"
        status, output = self.cli("parallel", QUERY)
        self.assertEqual((status, json.loads(output)), (1, {"error": "No results", "query": QUERY}))

    def test_cleanup_failure_keeps_the_result(self):
        self.server.cleanup_status = 500
        status, output = self.cli("parallel", QUERY, "--num", "1", "--json")
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output)["results"], [RESULT])
        self.assertTrue(any(request["http_method"] == "DELETE" for request in self.server.requests))

    def mcp_search(self, provider):
        async def call_search():
            setup = (
                f"import sys, runpy; sys.path.insert(0, {str(ROOT / 'scripts')!r}); "
                f"import parallel_search; parallel_search.PARALLEL_MCP_URL = {self.server.url + '/mcp'!r}; "
                f"runpy.run_path({str(ROOT / 'mcp' / 'server.py')!r}, run_name='__main__')"
            )
            env = {"SEARXNG_URL": self.server.url}
            if provider:
                env["SEARCH_PROVIDER"] = provider
            params = StdioServerParameters(command=sys.executable, args=["-c", setup], env=env)
            with open(os.devnull, "w") as log:
                async with stdio_client(params, errlog=log) as (reader, writer):
                    async with ClientSession(reader, writer) as session:
                        await session.initialize()
                        tools = {tool.name: tool.description for tool in (await session.list_tools()).tools}
                        self.assertEqual(set(tools), {"web_search", "web_search_news", "web_search_tavily"})
                        self.assertIn("Sends the query to Parallel" if provider == "parallel" else "SearxNG", tools["web_search"])
                        for name in ("web_search", "web_search", "web_search_news"):
                            result = await session.call_tool(name, {"query": QUERY, "num_results": 1})
                            self.assertFalse(result.isError)
                            self.assertEqual(json.loads(result.content[0].text)["results"], [RESULT])
        asyncio.run(call_search())

    def test_stdio_search_routes_only_the_selected_tool_to_parallel(self):
        self.mcp_search("parallel")
        self.assert_parallel_requests(2)
        local = [urlsplit(request["path"]) for request in self.server.requests if request["path"] != "/mcp"]
        self.assertEqual([path.path for path in local], ["/search"])
        self.assertEqual(parse_qs(local[0].query)["categories"], ["news"])

    def test_stdio_search_stays_on_searxng_without_parallel_selection(self):
        for provider in (None, "tavily"):
            with self.subTest(provider=provider):
                self.server.requests.clear()
                self.mcp_search(provider)
                self.assertEqual([urlsplit(request["path"]).path for request in self.server.requests], ["/search"] * 3)


if __name__ == "__main__":
    unittest.main()
