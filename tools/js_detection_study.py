"""Can a Python-only run of the frozen engine tell that a site depends on JavaScript?

For each URL:
  1. PREDICT: run the engine with --no-render (an existing flag; engine unchanged) and read its
     own evidence/pages.jsonl: pages with 0 internal links in raw HTML, pages with < 50 main-content
     words, and the engine's looks_like_spa_shell flag.
  2. MEASURE (ground truth): for the homepage and up to 3 more crawled pages (thin/zero-link pages
     first), count same-site links and visible words in the raw HTML and in the Playwright-rendered
     DOM. A page "needs JavaScript" if rendered links >= 5 and raw < 60% of rendered (the engine's
     own nav_links threshold, counted fairly), or rendered words >= 100 and >= 2x raw.
  3. Compare the prediction rules with the measurement.

Usage: python tools/js_detection_study.py out_dir category=url [category=url ...]
"""
import json
import re
import subprocess
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"


def slug(u: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", u.lower().split("://", 1)[-1]).strip("-")


def run_engine(market: Path, url: str, out: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, "skills/ai-readiness-orchestrator/scripts/orchestrate.py", url,
         "--out", str(out), "--no-render"],
        cwd=market, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    pj = out / "evidence" / "pages.jsonl"
    if not pj.exists():
        return {"error": f"exit {proc.returncode}: {proc.stderr.strip()[-160:]}"}
    pages = [json.loads(l) for l in pj.read_text(encoding="utf-8").splitlines() if l.strip()]
    html = [p for p in pages if p.get("status") == 200 and (p.get("content_type") or "text/html").startswith("text/html")]
    rep = json.loads((out / "audit-report.json").read_text(encoding="utf-8"))
    return {
        "status": rep.get("audit_status"),
        "pages": html,
        "n": len(html),
        "zero_link": [p["url"] for p in html if not (p.get("links") or {}).get("internal")],
        "thin": [p["url"] for p in html if (p.get("main_wordcount") or 0) < 50],
        "shell_flag": [p["url"] for p in html if p.get("looks_like_spa_shell")],
        "shell_finding": any(f["check_id"] == "read.render.empty_spa_shell" for f in rep["findings"]),
    }


def same_site_links(page_url: str, hrefs: list) -> int:
    host = urlparse(page_url).netloc
    base = host.removeprefix("www.")
    out = set()
    for h in hrefs:
        if not h or h.startswith(("mailto:", "javascript:", "tel:", "#")):
            continue
        a = urljoin(page_url, h).split("#")[0]
        hh = urlparse(a).netloc
        if hh == host or hh.endswith("." + base) or hh == base:
            out.add(a)
    return len(out)


def words(t: str) -> int:
    return len(re.findall(r"\w+", t))


def measure(browser, url: str) -> dict:
    raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read().decode("utf-8", "replace")
    body = re.sub(r"<(script|style|noscript|template)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    raw_words = words(re.sub(r"<[^>]+>", " ", body))
    raw_links = same_site_links(url, re.findall(r'<a\s[^>]*href=["\']([^"\']*)', raw, re.I))
    page = browser.new_page(user_agent=UA)
    page.goto(url, wait_until="load", timeout=60000)
    page.wait_for_timeout(3000)
    r_links = same_site_links(url, page.eval_on_selector_all("a[href]", "e => e.map(x => x.getAttribute('href'))"))
    r_words = words(page.inner_text("body"))
    page.close()
    needs = (r_links >= 5 and raw_links < 0.6 * r_links) or (r_words >= 100 and r_words >= 2 * raw_words)
    return {"url": url, "raw_links": raw_links, "r_links": r_links, "raw_words": raw_words, "r_words": r_words, "needs_js": needs}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    out_dir = Path(sys.argv[1])
    targets = [t.split("=", 1) for t in sys.argv[2:]]
    market = out_dir / "marketplace"
    if not market.exists():
        with zipfile.ZipFile(ROOT / "round3-frozen" / "submission.zip") as z:
            z.extractall(market)

    with ThreadPoolExecutor(max_workers=3) as pool:
        engine = dict(zip([u for _, u in targets],
                          pool.map(lambda cu: run_engine(market, cu[1], (out_dir / slug(cu[1])).resolve()), targets)))

    rows = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for cat, url in targets:
            e = engine[url]
            row = {"category": cat, "url": url, **{k: v for k, v in e.items() if k != "pages"}}
            if "error" in e:
                rows.append(row)
                continue
            sample = [url] + [u for u in e["zero_link"] + e["thin"] if u != url]
            sample += [p["url"] for p in e["pages"] if p["url"] not in sample]
            seen, meas = set(), []
            for u in sample:
                if u in seen or len(meas) >= 4:
                    continue
                seen.add(u)
                try:
                    meas.append(measure(browser, u))
                except Exception as exc:  # noqa: BLE001
                    meas.append({"url": u, "error": type(exc).__name__})
            row["measured"] = meas
            row["truth_needs_js"] = any(m.get("needs_js") for m in meas)
            rows.append(row)
        browser.close()

    (out_dir / "study.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"{'category':<10} {'site':<34} {'st':<8} {'pg':>3} {'0link':>5} {'<50w':>5} {'shell':>5}  truth(JS needed?)  sample raw->rendered links | words")
    for r in rows:
        if "error" in r:
            print(f"{r['category']:<10} {r['url']:<34} ENGINE {r['error']}")
            continue
        m = "; ".join(
            f"{urlparse(x['url']).path[:18] or '/'} {x['raw_links']}->{x['r_links']}|{x['raw_words']}->{x['r_words']}" if "error" not in x else f"{x['url'][:25]} ERR {x['error']}"
            for x in r["measured"][:3])
        print(f"{r['category']:<10} {r['url'][:34]:<34} {str(r['status'])[:8]:<8} {r['n']:>3} {len(r['zero_link']):>5} {len(r['thin']):>5} "
              f"{len(r['shell_flag']) + (1 if r['shell_finding'] else 0):>5}  {'YES' if r['truth_needs_js'] else 'no ':<17}  {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
