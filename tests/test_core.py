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
        with mock.patch.dict(os.environ, {"SEARCH_PROVIDER": "YouCom"}):
            self.assertEqual(core._get_search_provider(), "youcom")


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


YOUCOM_BODY = (
    '{"results": {"web": ['
    '{"url": "https://a", "title": "A", "description": "desc a", "snippets": ["s1"]},'
    '{"url": "https://b", "title": "B", "description": "", "snippets": ["s2", "s3"]},'
    '{"title": "no url"}'
    '], "news": [{"url": "https://n", "title": "N", "description": "news", "page_age": "2026-11-13"}]}}'
)


class YouComTests(unittest.TestCase):
    def _run(self, env, body=YOUCOM_BODY, status="200", **kw):
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("subprocess.run", return_value=_proc(out=body + "\n" + status)) as run:
                results = core.youcom_search("q", **kw)
        return results, run

    def test_keyless_request_and_normalize(self):
        results, run = self._run({}, num=10)
        cmd = run.call_args[0][0]
        url = cmd[-1]
        self.assertTrue(url.startswith(core.YOUCOM_KEYLESS_URL + "?"))
        self.assertIn("count=10", url)
        self.assertIn(core.YOUCOM_USER_AGENT, cmd)
        self.assertIsNone(run.call_args.kwargs.get("input"))
        self.assertNotIn("POST", cmd)
        self.assertEqual([r["url"] for r in results], ["https://a", "https://b", "https://n"])
        self.assertEqual(results[0]["content"], "desc a")
        self.assertEqual(results[1]["content"], "s2 s3")
        self.assertEqual(results[2]["publishedDate"], "2026-11-13")

    def test_count_capped_at_50(self):
        _, run = self._run({}, num=200)
        self.assertIn("count=50", run.call_args[0][0][-1])

    def test_news_first(self):
        results, _ = self._run({}, num=2, news=True)
        self.assertEqual([r["url"] for r in results], ["https://n", "https://a"])

    def test_keyed_request(self):
        _, run = self._run({"YDC_API_KEY": "secret"}, num=5)
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[-1], core.YOUCOM_KEYED_URL)
        self.assertIn("POST", cmd)
        self.assertNotIn("secret", " ".join(cmd))
        self.assertEqual(run.call_args.kwargs["input"], "X-API-Key: secret\n")
        self.assertIn('"count": 5', " ".join(cmd))

    def test_rejected_key(self):
        with self.assertRaises(RuntimeError) as cm:
            self._run({"YDC_API_KEY": "bad"}, body='{"detail": "no"}', status="401")
        self.assertIn("YDC_API_KEY", str(cm.exception))

    def test_rate_limited(self):
        with self.assertRaises(RuntimeError) as cm:
            self._run({}, body="{}", status="429")
        self.assertIn("YDC_API_KEY", str(cm.exception))

    def test_non_json(self):
        with self.assertRaises(RuntimeError) as cm:
            self._run({}, body="<html>", status="200")
        self.assertIn("did not return JSON", str(cm.exception))

    def test_curl_failure(self):
        with mock.patch("subprocess.run", return_value=_proc(rc=6, err="could not resolve")):
            with self.assertRaises(RuntimeError) as cm:
                core.youcom_search("q")
        self.assertIn("curl failed", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
