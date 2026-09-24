"""Independently re-check every Playwright-only finding in our runs against the live pages.

For read.render.nav_links_js_only: count unique same-site links (the page's host and its
subdomains, like the engine's own "internal" rule) in the raw HTML and in the Playwright-rendered
DOM, then apply the engine's own threshold (rendered >= 5 and raw < 60% of rendered).
For read.render.raw_text_gap: count visible words in the raw HTML (scripts/styles removed) and in
the rendered page's innerText; a real gap is rendered >= 2x raw.
Pages change, so this reflects the live site on the day it runs.

Usage: python tools/audit_render_findings.py [runs_dir]
"""
import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"
CHECKS = ("read.render.nav_links_js_only", "read.render.raw_text_gap")


def same_site(page_host: str, href_host: str) -> bool:
    return href_host == page_host or href_host.endswith("." + page_host.removeprefix("www."))


def links(url: str, hrefs: list[str]) -> int:
    host = urlparse(url).netloc
    out = set()
    for h in hrefs:
        if not h or h.startswith(("mailto:", "javascript:", "tel:", "#")):
            continue
        a = urljoin(url, h).split("#")[0]
        if same_site(host, urlparse(a).netloc):
            out.add(a)
    return len(out)


def words(text: str) -> int:
    return len(re.findall(r"\w+", text))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    runs = Path(sys.argv[1] if len(sys.argv) > 1 else "runs")
    todo = {}
    for p in sorted(runs.rglob("audit-report.json")):
        r = json.load(open(p, encoding="utf-8"))
        if r["generator"]["tool_versions"].get("renderer") != "playwright":
            continue
        for f in r["findings"]:
            if f["check_id"] in CHECKS and f.get("affected_urls"):
                todo.setdefault((f["check_id"], f["affected_urls"][0]), f["evidence"][:90])

    tally = {c: {"true": 0, "false": 0, "error": 0} for c in CHECKS}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for (check, url), ev in todo.items():
            try:
                raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read().decode("utf-8", "replace")
                page = browser.new_page()
                page.goto(url, wait_until="load", timeout=60000)
                page.wait_for_timeout(3000)
                if check.endswith("nav_links_js_only"):
                    r_n = links(url, re.findall(r'<a\s[^>]*href=["\']([^"\']*)', raw, re.I))
                    d_n = links(url, page.eval_on_selector_all("a[href]", "e => e.map(x => x.getAttribute('href'))"))
                    real = d_n >= 5 and r_n < 0.6 * d_n
                    got = f"same-site links raw {r_n} -> rendered {d_n}"
                else:
                    body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
                    r_n = words(re.sub(r"<[^>]+>", " ", body))
                    d_n = words(page.inner_text("body"))
                    real = d_n >= 2 * max(r_n, 1)
                    got = f"words raw {r_n} -> rendered {d_n}"
                page.close()
                verdict = "TRUE " if real else "FALSE"
                tally[check]["true" if real else "false"] += 1
            except Exception as exc:  # noqa: BLE001
                verdict, got = "ERROR", f"{type(exc).__name__}"
                tally[check]["error"] += 1
            print(f"{verdict} {check.split('.')[-1]:<18} {url[:70]:<70} {got}  | engine: {ev[len(url)+2:][:60] if ev.startswith(url) else ev[:60]}")
        browser.close()
    print("\nsummary:", json.dumps(tally))
    return 0


if __name__ == "__main__":
    sys.exit(main())
