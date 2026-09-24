"""Ground truth for tools/js_detection_study.py, measured the fair way.

Raw side  = the exact HTML the engine's crawler received (evidence/<raw_html_path>), so it uses the
            crawler's own User-Agent. Bot-specific pages (pre-rendered HTML for crawlers, or a
            bot-check page for browsers) are therefore judged as a crawler meets them.
Rendered  = what a human sees: the same URL in Chromium after JavaScript runs.
A page "needs JavaScript" when, counting same-site links on both sides, rendered >= 5 and raw < 60%
of rendered (the engine's own nav_links threshold), or when visible words go from raw to rendered
by >= 3x with >= 40 rendered words. Meta-refresh redirect stubs are skipped (a redirect is not
JavaScript). Rules are then scored against this truth.

Usage: python tools/js_detection_truth.py runs/jsstudy
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"
CHALLENGE = re.compile(r"just a moment|verify you are human|you have been blocked|access denied|captcha", re.I)


def slug(u: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", u.lower().split("://", 1)[-1]).strip("-")


def same_site(page_url: str, hrefs) -> int:
    host = urlparse(page_url).netloc
    base = host.removeprefix("www.")
    out = set()
    for h in hrefs:
        if not h or h.startswith(("mailto:", "javascript:", "tel:", "#")):
            continue
        a = urljoin(page_url, h).split("#")[0]
        hh = urlparse(a).netloc
        if hh == host or hh == base or hh.endswith("." + base):
            out.add(a)
    return len(out)


def words(t: str) -> int:
    return len(re.findall(r"\w+", t))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    d = Path(sys.argv[1])
    study = json.loads((d / "study.json").read_text(encoding="utf-8"))
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for row in study:
            if "error" in row:
                results.append({**row, "truth": None, "pages_measured": []})
                continue
            ev = d / slug(row["url"]) / "evidence"
            pages = [json.loads(l) for l in (ev / "pages.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
            html = [p for p in pages if p.get("status") == 200 and p.get("raw_html_path")]
            order = [row["url"]] + row["zero_link"] + row["thin"] + [p["url"] for p in html]
            byurl = {p["url"]: p for p in html}
            measured, seen = [], set()
            for u in order:
                if u in seen or u not in byurl or len(measured) >= 5:
                    continue
                seen.add(u)
                raw = (ev / byurl[u]["raw_html_path"]).read_text(encoding="utf-8", errors="replace")
                if re.search(r'http-equiv=["\']?refresh', raw, re.I) and words(re.sub(r"<[^>]+>", " ", raw)) < 30:
                    measured.append({"url": u, "skipped": "meta-refresh redirect"})
                    continue
                body = re.sub(r"<(script|style|noscript|template)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
                rw, rl = words(re.sub(r"<[^>]+>", " ", body)), same_site(u, re.findall(r'<a\s[^>]*href=["\']([^"\']*)', raw, re.I))
                try:
                    pg = browser.new_page(user_agent=UA)
                    pg.goto(u, wait_until="load", timeout=60000)
                    pg.wait_for_timeout(3000)
                    dl = same_site(u, pg.eval_on_selector_all("a[href]", "e => e.map(x => x.getAttribute('href'))"))
                    text = pg.inner_text("body")
                    pg.close()
                except Exception as exc:  # noqa: BLE001
                    measured.append({"url": u, "error": type(exc).__name__})
                    continue
                dw = words(text)
                needs = (dl >= 5 and rl < 0.6 * dl) or (dw >= 40 and dw >= 3 * max(rw, 1))
                measured.append({"url": u, "raw_links": rl, "r_links": dl, "raw_words": rw, "r_words": dw,
                                 "needs_js": needs, "rendered_is_challenge": bool(CHALLENGE.search(text[:600]))})
            truth = any(m.get("needs_js") for m in measured)
            results.append({**row, "truth": truth, "pages_measured": measured})
        browser.close()
    (d / "truth.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    rules = {
        "R1 any page with 0 same-site links": lambda r: len(r["zero_link"]) > 0,
        "R2 any page under 50 words": lambda r: len(r["thin"]) > 0,
        "R3 engine shell flag/finding": lambda r: len(r["shell_flag"]) > 0 or r["shell_finding"],
        "R1 and R2 on the same page": lambda r: bool(set(r["zero_link"]) & set(r["thin"])),
    }
    print(f"{'category':<8} {'site':<34} {'pg':>3} {'0link':>5} {'<50w':>5} {'shell':>5}  TRUTH  pages that need JS (crawler raw -> human rendered)")
    for r in results:
        if r["truth"] is None:
            print(f"{r['category']:<8} {r['url'][:34]:<34}  ENGINE ERROR {r.get('error', '')[:60]}")
            continue
        js = [m for m in r["pages_measured"] if m.get("needs_js")]
        detail = "; ".join(f"{urlparse(m['url']).netloc.split('.')[0]}{urlparse(m['url']).path[:16]} links {m['raw_links']}->{m['r_links']} words {m['raw_words']}->{m['r_words']}" for m in js[:2]) or "-"
        print(f"{r['category']:<8} {r['url'][:34]:<34} {r['n']:>3} {len(r['zero_link']):>5} {len(r['thin']):>5} "
              f"{len(r['shell_flag']) + (1 if r['shell_finding'] else 0):>5}  {'YES' if r['truth'] else 'no ':<5}  {detail}")
    scored = [r for r in results if r["truth"] is not None and r["n"] > 0]
    print(f"\nscoring over {len(scored)} sites ({sum(r['truth'] for r in scored)} truly need JavaScript)")
    for name, rule in rules.items():
        tp = sum(1 for r in scored if rule(r) and r["truth"])
        fp = sum(1 for r in scored if rule(r) and not r["truth"])
        fn = sum(1 for r in scored if not rule(r) and r["truth"])
        tn = sum(1 for r in scored if not rule(r) and not r["truth"])
        print(f"  {name:<36} caught {tp}, missed {fn}, false alarm {fp}, correct 'no' {tn}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
