import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import core  # noqa: E402


class FmtResultsTests(unittest.TestCase):
    def test_normal(self):
        out = core.fmt_results([{"title": " T ", "url": "https://example.com", "content": "c", "engines": ["a", "b"]}])
        self.assertEqual(out.splitlines(), ["[1] T", "    https://example.com", "    c", "    [a,b]"])

    def test_urls_only(self):
        out = core.fmt_results([{"url": "https://a"}, {"url": "https://b"}], urls_only=True)
        self.assertEqual(out, "https://a\nhttps://b")

    def test_missing_fields(self):
        out = core.fmt_results([{}])
        self.assertEqual(out, "[1]")


class EnvTests(unittest.TestCase):
    def test_search_url_trailing_slash(self):
        with mock.patch.dict(os.environ, {"SEARXNG_URL": "http://x:1/"}):
            self.assertEqual(core._search_url(), "http://x:1/search")

    def test_search_url_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(core._search_url(), "http://localhost:8080/search")

    def test_provider_default_and_case(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(core._get_search_provider(), "searxng")
        with mock.patch.dict(os.environ, {"SEARCH_PROVIDER": "TAVILY"}):
            self.assertEqual(core._get_search_provider(), "tavily")


def _proc(rc=0, out="", err=""):
    return mock.Mock(returncode=rc, stdout=out, stderr=err)


class SearchTests(unittest.TestCase):
    def test_valid_json_truncates(self):
        body = '{"results": [{"url": "1"}, {"url": "2"}, {"url": "3"}]}'
        with mock.patch("subprocess.run", return_value=_proc(out=body)):
            self.assertEqual(len(core.search("q", num=2)), 2)

    def test_html_raises(self):
        with mock.patch("subprocess.run", return_value=_proc(out="<html>nope</html>")):
            with self.assertRaises(RuntimeError) as cm:
                core.search("q")
        self.assertIn("did not return JSON", str(cm.exception))

    def test_curl_failure(self):
        with mock.patch("subprocess.run", return_value=_proc(rc=7, err="connection refused")):
            with self.assertRaises(RuntimeError) as cm:
                core.search("q")
        self.assertIn("curl failed", str(cm.exception))


class TavilyTests(unittest.TestCase):
    def test_missing_key(self):
        fake = mock.MagicMock()
        with mock.patch.dict(sys.modules, {"tavily": fake}):
            with mock.patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(RuntimeError) as cm:
                    core.tavily_search("q")
        self.assertIn("TAVILY_API_KEY", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
