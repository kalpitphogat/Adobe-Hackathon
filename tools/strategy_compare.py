"""Compare three ways of running the frozen engine: always Python-only, always Playwright, and
two-step (Python-only first; a second, Playwright run only when any page has 0 same-site links
in the crawler's raw HTML). Uses only existing engine flags; the engine is not modified.

  python tools/strategy_compare.py run  OUT_DIR url [url ...]   # performs the runs (batchable)
  python tools/strategy_compare.py eval OUT_DIR                 # verifies findings, prints table

`run` writes OUT_DIR/<slug>/{py,pw,two}/ (two/ only when the trigger fires; otherwise the
two-step result IS the py/ run) and appends to OUT_DIR/runs.jsonl.
`eval` checks every browser-dependent finding (read.render.nav_links_js_only,
read.render.raw_text_gap) against the live page: same-site links / visible words in the raw HTML
the engine's crawler saved vs the page a human sees in Chromium. Same thresholds as
tools/js_detection_truth.py.
"""
import json
import re
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"
RENDER_CHECKS = ("read.render.nav_links_js_only", "read.render.raw_text_gap", "act.perf.above_fold_weight")


def slug(u: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", u.lower().split("://", 1)[-1]).strip("-")


def engine(market: Path, url: str, out: Path, render: bool) -> dict:
    args = [sys.executable, "skills/ai-readiness-orchestrator/scripts/orchestrate.py", url, "--out", str(out)]
    if not render:
        args.append("--no-render")
    p = subprocess.run(args, cwd=market, capture_output=True, text=True, encoding="utf-8", errors="replace")
    rep = out / "audit-report.json"
    return {"exit": p.returncode, "ok": rep.exists(), "err": p.stderr.strip()[-150:] if not rep.exists() else ""}


def zero_link_pages(out: Path) -> list:
    pj = out / "evidence" / "pages.jsonl"
    if not pj.exists():
        return []
    pages = [json.loads(l) for l in pj.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [p["url"] for p in pages if p.get("status") == 200 and p.get("raw_html_path")
            and not (p.get("links") or {}).get("internal")]


def do_site(market: Path, out_dir: Path, url: str) -> dict:
    base = out_dir / slug(url)
    py = engine(market, url, (base / "py").resolve(), render=False)
    zl = zero_link_pages(base / "py") if py["ok"] else []
    trigger = bool(zl)
    two = engine(market, url, (base / "two").resolve(), render=True) if trigger else {"reused": "py"}
    pw = engine(market, url, (base / "pw").resolve(), render=True)
    return {"url": url, "py": py, "pw": pw, "two": two, "trigger": trigger, "zero_link_pages": zl[:5]}


def cmd_run(out_dir: Path, urls: list) -> None:
    market = out_dir / "marketplace"
    if not market.exists():
        with zipfile.ZipFile(ROOT / "round3-frozen" / "submission.zip") as z:
            z.extractall(market)
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(lambda u: do_site(market, out_dir, u), urls))
    with open(out_dir / "runs.jsonl", "a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
            print(f"{r['url']:<40} trigger={'YES' if r['trigger'] else 'no ':<3} py={r['py']['ok']} pw={r['pw']['ok']} two={r['two'].get('ok', 'reused py')}")


def same_site(page_url: str, hrefs) -> int:
    host = urlparse(page_url).netloc
    b = host.removeprefix("www.")
    s = set()
    for h in hrefs:
        if not h or h.startswith(("mailto:", "javascript:", "tel:", "#")):
            continue
        a = urljoin(page_url, h).split("#")[0]
        hh = urlparse(a).netloc
        if hh == host or hh == b or hh.endswith("." + b):
            s.add(a)
    return len(s)


def words(t: str) -> int:
    return len(re.findall(r"\w+", t))


def cmd_eval(out_dir: Path) -> None:
    from playwright.sync_api import sync_playwright

    sys.stdout.reconfigure(encoding="utf-8")
    rows = {}
    for line in (out_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        rows[r["url"]] = r  # last run wins

    def report(url, strat):
        folder = out_dir / slug(url) / ("py" if strat == "two" and not rows[url]["trigger"] else strat)
        f = folder / "audit-report.json"
        return (json.loads(f.read_text(encoding="utf-8")), folder) if f.exists() else (None, folder)

    cache = {}
    verdicts = {}  # (strategy, url, check, page) -> True/False/None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        def rendered(u):
            if u not in cache:
                try:
                    pg = browser.new_page(user_agent=UA)
                    pg.goto(u, wait_until="load", timeout=60000)
                    pg.wait_for_timeout(3000)
                    cache[u] = (same_site(u, pg.eval_on_selector_all("a[href]", "e => e.map(x => x.getAttribute('href'))")), words(pg.inner_text("body")))
                    pg.close()
                except Exception:  # noqa: BLE001
                    cache[u] = None
            return cache[u]

        for url in rows:
            for strat in ("pw", "two"):
                rep, folder = report(url, strat)
                if not rep:
                    continue
                pages = {json.loads(l)["url"]: json.loads(l) for l in (folder / "evidence" / "pages.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
                for f in rep["findings"]:
                    if f["check_id"] not in RENDER_CHECKS or not f.get("affected_urls"):
                        continue
                    page = f["affected_urls"][0]
                    v = None
                    if f["check_id"] != "act.perf.above_fold_weight" and page in pages and pages[page].get("raw_html_path"):
                        raw = (folder / "evidence" / pages[page]["raw_html_path"]).read_text(encoding="utf-8", errors="replace")
                        body = re.sub(r"<(script|style|noscript|template)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
                        rl, rw = same_site(page, re.findall(r'<a\s[^>]*href=["\']([^"\']*)', raw, re.I)), words(re.sub(r"<[^>]+>", " ", body))
                        got = rendered(page)
                        if got:
                            dl, dw = got
                            if f["check_id"].endswith("nav_links_js_only"):
                                v = dl >= 5 and rl < 0.6 * dl
                            else:
                                v = dw >= 40 and dw >= 3 * max(rw, 1)
                    verdicts[(strat, url, f["check_id"], page)] = v
        browser.close()

    print(f"{'site':<34} {'trigger':<7} | {'py: total/high':<15} | {'pw: total/high  render T/F/?':<30} | {'two-step: total/high  render T/F/?':<34}")
    totals = {s: {"tot": 0, "high": 0, "T": 0, "F": 0, "U": 0} for s in ("py", "pw", "two")}
    missed = []
    for url, r in rows.items():
        cells = []
        for strat in ("py", "pw", "two"):
            rep, _ = report(url, strat)
            if not rep:
                cells.append("n/a")
                continue
            s = rep["summary"]
            t = totals[strat]
            t["tot"] += s["total_findings"]
            t["high"] += s["high"] + s["critical"]
            if strat == "py":
                cells.append(f"{s['total_findings']}/{s['high'] + s['critical']}")
                continue
            vs = [v for (st, u, c, p), v in verdicts.items() if st == strat and u == url]
            T, F, U = vs.count(True), vs.count(False), vs.count(None)
            t["T"] += T; t["F"] += F; t["U"] += U
            cells.append(f"{s['total_findings']}/{s['high'] + s['critical']}  render {T}/{F}/{U}")
        pw_true = {(c, p) for (st, u, c, p), v in verdicts.items() if st == "pw" and u == url and v}
        two_true = {(c, p) for (st, u, c, p), v in verdicts.items() if st == "two" and u == url and v}
        if pw_true - two_true:
            missed.append((url, sorted(pw_true - two_true)))
        print(f"{url[:34]:<34} {'YES' if r['trigger'] else 'no':<7} | {cells[0]:<15} | {cells[1]:<30} | {cells[2]:<34}")
    print("\nTOTALS (all sites)")
    for s, lab in (("py", "always Python-only"), ("pw", "always Playwright"), ("two", "two-step")):
        t = totals[s]
        extra = "" if s == "py" else f"  browser findings: {t['T']} true, {t['F']} false, {t['U']} unverified"
        print(f"  {lab:<20} findings {t['tot']:<4} high+critical {t['high']:<4}{extra}")
    print("\nReal browser findings that always-Playwright found but two-step did not:")
    for url, items in missed:
        for c, p in items:
            print(f"  {url}  {c}  {p}")
    if not missed:
        print("  none")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    mode, out_dir = sys.argv[1], Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    if mode == "run":
        cmd_run(out_dir, sys.argv[3:])
    else:
        cmd_eval(out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
