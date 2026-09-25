#!/usr/bin/env python3
"""Run the UNCHANGED Round 3 engine against real websites and summarise what it found.

This is how the Round 4 demo URL was chosen and how the engine was tested for
generalisation before recording. It contains no checks of its own and never
edits a report: it unpacks submission.zip into a fresh temporary folder, runs
the marketplace entrypoint exactly as REPLAY_IT_Professionals.txt documents it,
and prints what the engine wrote.

    python3 round4/tools/live_matrix.py https://www.theguardian.com/
    python3 round4/tools/live_matrix.py --urls round4/urls/generalization.txt
    python3 round4/tools/live_matrix.py --urls FILE --out ./matrix-runs --evidence 5

Standard library only. Exit 0 when every run produced a schema-valid report,
1 otherwise. A site that blocks us still produces a report; that is exit 0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_ZIP = REPO / "round3-frozen" / "submission.zip"
PIN_FILE = REPO / "round4" / "SUBMITTED_ZIP.sha256"
ENTRYPOINT = "skills/ai-readiness-orchestrator/scripts/orchestrate.py"

# The Round 3 report floor, as the handout states it.
TOP_KEYS = ("site", "audited_at", "summary", "findings")
SUMMARY_KEYS = ("total_findings", "critical", "high", "medium", "low")
FINDING_KEYS = ("id", "title", "severity", "evidence", "suggested_action")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_hash() -> str:
    if not PIN_FILE.is_file():
        return ""
    for line in PIN_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line.split()[0]
    return ""


def slug(url: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", re.sub(r"^https?://", "", url)).strip("_")[:80]


def floor_problems(report: dict) -> list[str]:
    problems = [f"missing top-level {k!r}" for k in TOP_KEYS if k not in report]
    summary = report.get("summary") or {}
    problems += [f"missing summary.{k}" for k in SUMMARY_KEYS if k not in summary]
    for f in report.get("findings") or []:
        gap = [k for k in FINDING_KEYS if k not in f]
        if gap:
            problems.append(f"{f.get('id', '?')} missing {gap}")
    return problems


def one_line(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


# A verification line is only executed if it is a plain read-only fetch piped
# through text filters: no command substitution, no redirection, no chaining.
SAFE_VERIFY = re.compile(
    r"^curl -sI? '?https?://[^\s'`$<>;&|]+'?"
    r"(\s*\|\s*(grep|sed|head|wc|tr|sort)\b[^`$<>;&|]*)*"
    r"(\s+#[^`$]*)?$"
)


def corroborate(report: dict, limit: int) -> None:
    """Re-check the top confirmed findings against the live site.

    Two ways, both read-only: robots.txt findings cite line numbers, so those
    lines are fetched and printed; other findings carry the engine's own
    verification command, which is run when it is a plain curl-and-filter line.
    Output is printed for a human to judge. It never changes the report.
    """
    import urllib.request

    done = 0
    for f in report["findings"]:
        if done >= limit:
            break
        if f.get("confidence") != "confirmed":
            continue
        done += 1
        print(f"  ~~ corroborate {f['id']} {f.get('check_id')}")
        if (f.get("check_id") or "").startswith("reach.robots."):
            origin = f"https://{report['site']}"
            lines = sorted({int(n) for n in re.findall(r"\(line (\d+)\)", f.get("evidence", ""))})
            try:
                req = urllib.request.Request(origin + "/robots.txt", headers={"User-Agent": "round4-corroborate"})
                body = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace").splitlines()
            except Exception as exc:  # noqa: BLE001 - a failed re-check is reported, not fatal
                print(f"     could not fetch robots.txt: {exc}")
                continue
            for n in lines:
                start = max(1, n - 25)
                group = [i for i in range(start, min(n, len(body) + 1)) if body[i - 1].lower().startswith("user-agent")]
                for i in group + [n]:
                    print(f"     robots.txt:{i}: {body[i - 1] if i <= len(body) else '(beyond end of file)'}")
            continue
        for line in (f.get("suggested_action") or {}).get("verification", "").splitlines():
            line = line.strip()
            if not SAFE_VERIFY.match(line):
                continue
            try:
                proc = subprocess.run(["bash", "-c", line], capture_output=True, text=True, timeout=30)
                shown = [l for l in proc.stdout.splitlines() if l.strip()][:6]
                print(f"     $ {one_line(line, 160)}")
                for l in shown or ["(no output)"]:
                    print(f"       {one_line(l, 200)}")
            except Exception as exc:  # noqa: BLE001
                print(f"     $ {one_line(line, 160)} -> {exc}")


def summarise(url: str, out: Path, code: int, elapsed: float, stderr: str, evidence: int,
              verify: int = 0) -> dict:
    row = {"url": url, "exit": code, "elapsed_s": round(elapsed, 1), "out": str(out)}
    report_path = out / "audit-report.json"
    if not report_path.is_file():
        row["error"] = one_line(stderr, 400) or "no report written"
        print(f"  !! no report: {row['error']}")
        return row

    report = json.loads(report_path.read_text(encoding="utf-8"))
    s = report["summary"]
    ev = report.get("evidence_bundle") or {}
    row.update({
        "site": report.get("site"),
        "audit_status": report.get("audit_status"),
        "pages_fetched": ev.get("pages_fetched"),
        "pages_rendered": ev.get("pages_rendered"),
        "counts": {k: s.get(k) for k in ("total_findings", "critical", "high", "medium", "low", "info",
                                         "blocked_findings")},
        "by_category": s.get("by_category"),
        "floor_problems": floor_problems(report),
        "findings": [
            {
                "id": f["id"], "severity": f["severity"], "confidence": f.get("confidence"),
                "ice": (f.get("suggested_action") or {}).get("ice"), "stage": f.get("stage"),
                "check_id": f.get("check_id"), "blocked_by": f.get("blocked_by"),
                "affected": len(f.get("affected_urls") or []), "title": f["title"],
            }
            for f in report["findings"]
        ],
        "limitations": [one_line(l.get("reason"), 200) for l in report.get("limitations") or []],
    })

    c = row["counts"]
    print(f"  status={row['audit_status']} pages={row['pages_fetched']} "
          f"findings={c['total_findings']} (C{c['critical']} H{c['high']} M{c['medium']} "
          f"L{c['low']} I{c['info']}) blocked={c['blocked_findings']} "
          f"disc/eng={row['by_category'].get('discoverability')}/{row['by_category'].get('engagement')} "
          f"exit={code} {elapsed:.0f}s")
    if row["floor_problems"]:
        print(f"  !! schema floor: {row['floor_problems'][:3]}")
    for f in report["findings"][:12]:
        a = f.get("suggested_action") or {}
        blocked = f" blocked_by={f['blocked_by']}" if f.get("blocked_by") else ""
        print(f"  {f['id']} {f['severity']:<8} {f.get('confidence', ''):<10} ICE {a.get('ice', '-'):<4} "
              f"{f.get('check_id', '')}{blocked}")
        print(f"         {one_line(f['title'], 150)}")
    if len(report["findings"]) > 12:
        print(f"  … {len(report['findings']) - 12} more")
    for f in report["findings"][:evidence]:
        a = f.get("suggested_action") or {}
        print(f"  --- {f['id']} evidence: {one_line(f['evidence'], 700)}")
        print(f"      fix: {one_line(a.get('summary'), 200)}")
        print(f"      verify: {one_line(a.get('verification'), 200)}")
    for lim in row["limitations"]:
        print(f"  LIMITATION: {lim}")
    if verify:
        corroborate(report, verify)
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="*", help="URLs to audit")
    ap.add_argument("--urls", dest="url_file", type=Path, help="file with one URL per line (# comments allowed)")
    ap.add_argument("--zip", type=Path, default=DEFAULT_ZIP, help="the Round 3 submission.zip")
    ap.add_argument("--out", type=Path, default=None, help="keep reports here (default: a temp dir, deleted)")
    ap.add_argument("--time-budget", default="300")
    ap.add_argument("--render", action="store_true",
                    help="let the engine render with Playwright (default passes --no-render, as the REPLAY does)")
    ap.add_argument("--evidence", type=int, default=3, help="print full evidence for the top N findings")
    ap.add_argument("--json", type=Path, default=None, help="write the per-URL summary here")
    ap.add_argument("--verify", type=int, default=0,
                    help="re-check the top N confirmed findings against the live site (needs bash + curl)")
    args = ap.parse_args(argv)

    urls = list(args.urls)
    if args.url_file:
        for line in args.url_file.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                urls.append(line)
    if not urls:
        ap.error("give at least one URL, or --urls FILE")

    if not args.zip.is_file():
        print(f"error: {args.zip} not found", file=sys.stderr)
        return 1
    digest = sha256(args.zip)
    pin = pinned_hash()
    verdict = "matches the pinned Round 3 submission" if pin == digest else (
        "DOES NOT MATCH the pinned Round 3 submission" if pin else "no pin to compare against")
    print(f"engine: {args.zip.name} sha256 {digest} ({verdict})")
    if pin and pin != digest:
        return 1

    work = Path(tempfile.mkdtemp(prefix="round4-engine-"))
    keep = args.out.resolve() if args.out else None
    rows: list[dict] = []
    try:
        engine = work / "marketplace"
        with zipfile.ZipFile(args.zip) as zf:
            zf.extractall(engine)
        print(f"unpacked {sum(1 for p in engine.rglob('*') if p.is_file())} files into a fresh folder\n")

        runs = keep or (work / "runs")
        runs.mkdir(parents=True, exist_ok=True)
        for url in urls:
            out = runs / slug(url)
            if out.exists():
                shutil.rmtree(out)
            cmd = [sys.executable, ENTRYPOINT, url, "--out", str(out), "--time-budget", args.time_budget]
            if not args.render:
                cmd.append("--no-render")
            print(f"== {url}")
            print(f"   $ python {' '.join(cmd[1:3])} --out <dir> --time-budget {args.time_budget}"
                  f"{'' if args.render else ' --no-render'}")
            started = time.monotonic()
            try:
                proc = subprocess.run(cmd, cwd=str(engine), capture_output=True, text=True,
                                      timeout=float(args.time_budget) + 120)
                code, stderr = proc.returncode, proc.stderr
            except subprocess.TimeoutExpired:
                code, stderr = -9, "hard timeout: the run exceeded its time budget + 120 s"
            rows.append(summarise(url, out, code, time.monotonic() - started, stderr, args.evidence,
                                  args.verify))
            print()
    finally:
        if not keep:
            shutil.rmtree(work, ignore_errors=True)

    failed = [r for r in rows if r.get("exit") != 0 or "error" in r or r.get("floor_problems")]
    print("== summary")
    for r in rows:
        c = r.get("counts") or {}
        print(f"  {'FAIL' if r in failed else 'ok  '} {r['url']:<48} "
              f"{r.get('audit_status', '-'):<21} C{c.get('critical', '-')} H{c.get('high', '-')} "
              f"M{c.get('medium', '-')} total {c.get('total_findings', '-'):<3} {r['elapsed_s']}s")
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
