"""Run the frozen engine against many candidate URLs and tabulate the results.

Invokes the engine exactly as a judge would (cwd = marketplace root, documented
command); it never imports or modifies engine code. Writes each run to
runs/<slug>/ and a table to runs/scout.json.

Usage: python tools/scout.py --parallel 3 category=https://url [category=https://url ...]
"""
import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / "demo"
ORCH = "skills/ai-readiness-orchestrator/scripts/orchestrate.py"


def slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", url.lower().split("://", 1)[-1]).strip("-")


def run_one(category: str, url: str) -> dict:
    out = ROOT / "runs" / slug(url)
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, ORCH, url, "--out", str(out)],
        cwd=MARKETPLACE, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    row = {"category": category, "url": url, "exit": proc.returncode,
           "elapsed_s": round(time.monotonic() - started), "out": str(out)}
    report = out / "audit-report.json"
    if not report.exists():
        row["error"] = proc.stderr.strip()[-300:]
        return row
    r = json.loads(report.read_text(encoding="utf-8"))
    s, gen = r["summary"], r.get("generator", {})
    findings = r["findings"]
    row.update({
        "status": r.get("audit_status"),
        "renderer": gen.get("tool_versions", {}).get("renderer"),
        "checks_run": gen.get("checks_run"),
        "total": s["total_findings"],
        "critical": s.get("critical", 0),
        "high": s.get("high", 0),
        "confirmed_high_plus": sum(1 for f in findings
                                   if f["severity"] in ("critical", "high") and f.get("confidence") == "confirmed"),
        "top": [f"{f['severity']}/{f.get('confidence')} {f.get('check_id')}" for f in findings[:6]],
    })
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("targets", nargs="+", help="category=url")
    args = ap.parse_args()
    pairs = [t.split("=", 1) for t in args.targets]

    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        rows = list(pool.map(lambda p: run_one(*p), pairs))

    table = ROOT / "runs" / "scout.json"
    prior = json.loads(table.read_text(encoding="utf-8")) if table.exists() else []
    merged = {r["url"]: r for r in prior} | {r["url"]: r for r in rows}
    table.write_text(json.dumps(list(merged.values()), indent=2), encoding="utf-8")

    for r in rows:
        if "error" in r:
            print(f"{r['category']:<10} {r['url']:<45} exit={r['exit']} ERROR {r['error'][:120]}")
        else:
            print(f"{r['category']:<10} {r['url']:<45} {r['elapsed_s']:>4}s {r['status']:<9} "
                  f"render={r['renderer']:<10} total={r['total']:<3} crit={r['critical']} high={r['high']} "
                  f"confirmed_high+={r['confirmed_high_plus']}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
