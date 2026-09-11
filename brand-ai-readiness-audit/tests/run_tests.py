#!/usr/bin/env python3
"""
Automated test suite for the brand-ai-readiness-audit marketplace.

Runs entirely offline against two local fixture sites:
  - tests/fixtures/badsite : deliberately broken -> should trip many checks
  - tests/fixtures/goodsite : reasonably healthy -> should be much cleaner

For each, it boots a local HTTP server, runs the real end-to-end audit
(crawler + all sub-audits + orchestrator), and asserts on the report. Also
validates the marketplace manifest and the HTML renderer.

Usage:  python tests/run_tests.py            # standard library only; no network
Exit 0 = all pass. Add --render to also exercise the headless-Chromium path.
"""
import functools
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "skills", "audit-orchestrator", "scripts")
FIXTURES = os.path.join(HERE, "fixtures")
RENDER = "--render" in sys.argv

# keep test fetches off the outbound proxy
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass


def serve(directory, port=0):
    """Start a background HTTP server for `directory`; return (base_url, shutdown).
    A fixed port is used when the fixture's sitemap references absolute URLs."""
    handler = functools.partial(_QuietHandler, directory=directory)
    # Threaded so overlapping requests (e.g. the broken-link HEAD sweep) never race,
    # matching `python -m http.server` behavior.
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return f"http://127.0.0.1:{port}", httpd.shutdown


def run_audit(base_url, max_pages=8):
    cache = tempfile.mkdtemp(prefix="test_cache_")
    out = os.path.join(cache, "report.json")
    html = os.path.join(cache, "report.html")
    cmd = [sys.executable, os.path.join(SCRIPTS, "run_audit.py"), base_url,
           "--max-pages", str(max_pages), "--cache", cache, "--out", out, "--html", html]
    if RENDER:
        cmd.append("--render")
    subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=os.environ)
    with open(out, encoding="utf-8") as f:
        return json.load(f), html


def titles(report):
    return [f["title"] for f in report["findings"]]


def has(report, substr):
    return any(substr.lower() in t.lower() for t in titles(report))


class TestMarketplaceStructure(unittest.TestCase):
    def test_validator_passes(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "validate.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("1 entrypoint", r.stdout)


class TestBadSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.stop = serve(os.path.join(FIXTURES, "badsite"))
        cls.report, cls.html = run_audit(cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.stop()

    def test_schema_floor(self):
        r = self.report
        for k in ("site", "audited_at", "summary", "findings"):
            self.assertIn(k, r)
        for k in ("total_findings", "critical", "high", "medium", "low"):
            self.assertIn(k, r["summary"])
        for f in r["findings"]:
            for k in ("id", "title", "severity", "evidence", "suggested_action"):
                self.assertIn(k, f)
            self.assertIn("summary", f["suggested_action"])
            self.assertIn("priority", f["suggested_action"])

    def test_ids_sorted_and_stable(self):
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sevs = [f["severity"] for f in self.report["findings"]]
        self.assertEqual(sevs, sorted(sevs, key=lambda s: order[s]))
        ids = [f["id"] for f in self.report["findings"]]
        self.assertEqual(ids, [f"F-{i:03d}" for i in range(1, len(ids) + 1)])

    def test_expected_findings_detected(self):
        r = self.report
        self.assertTrue(has(r, "AI assistant crawlers are restricted"))
        self.assertTrue(has(r, "noindex"))
        self.assertTrue(has(r, "near-empty in raw HTML"))
        self.assertTrue(has(r, "No structured data"))
        self.assertTrue(has(r, "Stale copyright"))
        self.assertTrue(has(r, "sitemap"))
        self.assertTrue(has(r, "Broken internal links"))
        self.assertTrue(has(r, "multiple H1"))

    def test_both_dimensions_and_severity(self):
        r = self.report
        self.assertGreaterEqual(r["summary"]["critical"], 1)
        self.assertGreater(r["summary"]["by_dimension"]["discoverability"], 0)
        self.assertGreater(r["summary"]["by_dimension"]["engagement"], 0)

    def test_html_report_written(self):
        self.assertTrue(os.path.exists(self.html))
        doc = open(self.html, encoding="utf-8").read()
        self.assertIn("<!doctype html>", doc.lower())
        self.assertIn("AI-Readiness Audit", doc)


class TestRobotsGuardrail(unittest.TestCase):
    """A URL disallowed by robots.txt must be recorded as blocked and never fetched."""

    def test_disallowed_url_not_fetched(self):
        base, stop = serve(os.path.join(FIXTURES, "robotssite"))
        cache = tempfile.mkdtemp(prefix="robots_")
        try:
            subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "crawler.py"), base, cache, "--max-pages", "5"],
                capture_output=True, text=True, timeout=60, env=os.environ)
            meta = json.load(open(os.path.join(cache, "meta.json"), encoding="utf-8"))
        finally:
            stop()
        blocked = [p for p in meta["pages"] if "/private/" in p["url"]]
        self.assertTrue(blocked, "disallowed URL should still be recorded")
        for p in blocked:
            self.assertTrue(p["robots_blocked"])
            self.assertIsNone(p["status"], "disallowed URL must not be fetched")
            html = os.path.join(cache, "pages", p["slug"] + ".html")
            self.assertFalse(os.path.exists(html), "no body may be cached for a disallowed URL")


class TestEdgeBlock(unittest.TestCase):
    """A CDN/WAF that serves a browser but 403s an AI-bot UA must be flagged, even
    when robots.txt says nothing."""

    def test_edge_block_detected(self):
        directory = os.path.join(FIXTURES, "goodsite")

        class Handler(_QuietHandler):
            def do_GET(self):  # noqa: N802
                if "GPTBot" in self.headers.get("User-Agent", ""):
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b"blocked")
                    return
                return super().do_GET()

        httpd = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(Handler, directory=directory))
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            report, _ = run_audit(base, max_pages=4)
        finally:
            httpd.shutdown()
        self.assertTrue(has(report, "blocked at the edge"),
                        "edge/CDN AI-bot block should be detected")


class TestIntegrity(unittest.TestCase):
    """Prompt-injection, hidden/cloaked text, and zero-width Unicode must be detected."""

    @classmethod
    def setUpClass(cls):
        cls.base, cls.stop = serve(os.path.join(FIXTURES, "integritysite"))
        cls.report, _ = run_audit(cls.base, max_pages=3)

    @classmethod
    def tearDownClass(cls):
        cls.stop()

    def test_injection_detected(self):
        self.assertTrue(has(self.report, "Prompt-injection"))

    def test_hidden_and_zerowidth_detected(self):
        self.assertTrue(has(self.report, "visually-hidden text"))
        self.assertTrue(has(self.report, "zero-width Unicode"))


class TestGoodSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # goodsite's sitemap.xml uses absolute URLs on port 8091, so pin the port
        cls.base, cls.stop = serve(os.path.join(FIXTURES, "goodsite"), port=8091)
        cls.report, cls.html = run_audit(cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.stop()

    def test_healthy_site_is_clean(self):
        r = self.report
        # A healthy site must not trip the severe structural checks.
        self.assertFalse(has(r, "AI assistant crawlers are blocked"))
        self.assertFalse(has(r, "noindex"))
        self.assertFalse(has(r, "No structured data"))
        self.assertFalse(has(r, "near-empty raw HTML"))
        self.assertFalse(has(r, "No llms.txt"))
        self.assertEqual(r["summary"]["critical"], 0)

    def test_relative_severity(self):
        # sanity: good site should have far fewer critical/high than the number of pages
        r = self.report
        self.assertLessEqual(r["summary"]["critical"] + r["summary"]["high"], 3)


if __name__ == "__main__":
    argv = [a for a in sys.argv if a != "--render"]
    unittest.main(argv=argv, verbosity=2)
