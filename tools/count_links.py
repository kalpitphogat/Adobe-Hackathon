"""Count same-host <a href> links in raw HTML vs Playwright-rendered DOM, independently of the engine."""
import re
import sys
import urllib.request
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"


def split(url, hrefs):
    host = urlparse(url).netloc
    abs_ = [urljoin(url, h) for h in hrefs if not h.startswith(("mailto:", "javascript:", "tel:"))]
    same = {h.split("#")[0] for h in abs_ if urlparse(h).netloc == host}
    other = {h.split("#")[0] for h in abs_ if urlparse(h).netloc != host}
    return len(abs_), len(same), len(other)


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    for url in sys.argv[1:]:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20).read().decode("utf-8", "replace")
        raw_hrefs = re.findall(r'<a\s[^>]*href=["\']([^"\']+)', raw, re.I)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=45000)
        ren_hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
        page.close()
        r, rs, ro = split(url, raw_hrefs)
        d, ds, do = split(url, ren_hrefs)
        print(f"{url}\n  raw:      anchors={r} unique_same_host={rs} unique_other_host={ro}"
              f"\n  rendered: anchors={d} unique_same_host={ds} unique_other_host={do}")
    browser.close()
