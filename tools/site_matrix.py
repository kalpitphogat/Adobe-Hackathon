"""Run the frozen engine on a set of sites with and without Playwright, and verify every
browser-dependent finding against the engine's own saved raw and rendered HTML.

  python tools/site_matrix.py run  MARKETPLACE OUT_DIR url [url ...]
  python tools/site_matrix.py eval OUT_DIR

MARKETPLACE is a folder unzipped from submission.zip (the engine is not modified; only existing
flags are used: --no-render, and --allow-private-hosts for http://127.0.0.1 test sites).
`run` writes OUT_DIR/<slug>/{py,pw}/. `eval` prints one row per site.

A read.render.nav_links_js_only finding is counted TRUE when, on the page it names, the rendered
HTML has at least 5 same-site links and the raw HTML fewer than 60% of them (the engine's own
thresholds, applied to same-site links on both sides). A read.render.raw_text_gap finding is
TRUE when the page's visible words grow at least 3x to 200 or more.
"""
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit


def slug(u: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", u.lower().split("://", 1)[-1]).strip("-")


def engine(market: Path, url: str, out: Path, render: bool) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    args = [sys.executable, "skills/ai-readiness-orchestrator/scripts/orchestrate.py", url,
            "--out", str(out)]
    if not render:
        args.append("--no-render")
    if urlsplit(url).hostname in ("127.0.0.1", "localhost"):
        args.append("--allow-private-hosts")
    p = subprocess.run(args, cwd=market, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return {"exit": p.returncode, "ok": (out / "audit-report.json").exists(),
            "err": p.stderr.strip()[-200:]}


def run(market: Path, out_dir: Path, urls: list) -> None:
    def one(job):
        url, mode = job
        return url, mode, engine(market, url, (out_dir / slug(url) / mode).resolve(), mode == "pw")
    jobs = [(u, m) for u in urls for m in ("py", "pw")]
    with ThreadPoolExecutor(4) as ex:
        for url, mode, res in ex.map(one, jobs):
            print(mode, url, res["exit"], res["err"][-80:] if not res["ok"] else "")


class _Parse(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.words, self._skip = [], 0, 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "template"):
            self._skip += 1
        if tag == "a":
            h = dict(attrs).get("href")
            if h:
                self.hrefs.append(h)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.words += len(data.split())


def measure(html: str, page_url: str) -> tuple:
    p = _Parse()
    p.feed(html)
    host = (urlsplit(page_url).hostname or "").lower().removeprefix("www.")
    same = set()
    for h in p.hrefs:
        u = urljoin(page_url, h)
        s = urlsplit(u)
        if s.scheme in ("http", "https") and (s.hostname or "").lower().removeprefix("www.") == host:
            same.add(s._replace(fragment="").geturl())
    return len(same), p.words


def verify(run_dir: Path, finding: dict) -> bool | None:
    pages = {}
    for line in (run_dir / "evidence" / "pages.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            pages[rec["url"]] = rec
    url = (finding.get("affected_urls") or [None])[0]
    rec = pages.get(url)
    if not rec or not rec.get("rendered_html_path") or not rec.get("raw_html_path"):
        return None
    raw = (run_dir / "evidence" / rec["raw_html_path"]).read_text(encoding="utf-8", errors="replace")
    ren = (run_dir / "evidence" / rec["rendered_html_path"]).read_text(encoding="utf-8", errors="replace")
    (rl, rw), (nl, nw) = measure(raw, url), measure(ren, url)
    if finding["check_id"] == "read.render.nav_links_js_only":
        return nl >= 5 and rl < 0.6 * nl
    if finding["check_id"] == "read.render.raw_text_gap":
        return nw >= 200 and nw >= 3 * max(rw, 1)
    return None


def summary(run_dir: Path) -> dict:
    rep = json.loads((run_dir / "audit-report.json").read_text(encoding="utf-8"))
    f = rep["findings"]
    render = [x for x in f if x["check_id"].startswith("read.render.") and
              x["check_id"] != "read.render.empty_spa_shell"]
    verdicts = [verify(run_dir, x) for x in render]
    pages = [json.loads(l) for l in (run_dir / "evidence" / "pages.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    return {
        "status": rep.get("audit_status"),
        "total": len(f),
        "high+": sum(x["severity"] in ("critical", "high") for x in f),
        "act": sum(x["check_id"].startswith("act.") for x in f),
        "shell": sum(x["check_id"] == "read.render.empty_spa_shell" for x in f),
        "true": verdicts.count(True), "false": verdicts.count(False),
        "false_ids": [x["check_id"].split(".")[-1] for x, v in zip(render, verdicts) if v is False],
        "zero_link_pages": sum(1 for p in pages if p.get("status") == 200 and p.get("raw_html_path")
                               and not (p.get("links") or {}).get("internal")),
        "pages": sum(1 for p in pages if p.get("status") == 200),
    }


def evaluate(out_dir: Path) -> None:
    print("| site | pages | 0-link pages | --no-render: status, total/high+, act | "
          "Playwright: status, total/high+, act | browser findings true/false | false ones |")
    print("|---|---|---|---|---|---|---|")
    for d in sorted(p for p in out_dir.iterdir() if p.is_dir()):
        try:
            py, pw = summary(d / "py"), summary(d / "pw")
        except FileNotFoundError as e:
            print(f"| {d.name} | run incomplete: {e.filename} |")
            continue
        print(f"| {d.name} | {py['pages']} | {py['zero_link_pages']} | "
              f"{py['status']}, {py['total']}/{py['high+']}, {py['act']} | "
              f"{pw['status']}, {pw['total']}/{pw['high+']}, {pw['act']} | "
              f"{pw['true']}/{pw['false']} | {', '.join(pw['false_ids']) or '-'} |")


if __name__ == "__main__":
    if sys.argv[1:2] == ["run"]:
        run(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve(), sys.argv[4:])
    elif sys.argv[1:2] == ["eval"]:
        evaluate(Path(sys.argv[2]).resolve())
    else:
        print(__doc__)
