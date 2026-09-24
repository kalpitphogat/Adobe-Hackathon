"""Print a one-screen summary of an audit-report.json, for comparing candidate demo URLs.

Reads the engine's output only; never touches the engine.
Usage: python tools/summarize.py runs/<name>/audit-report.json [--top N]
"""
import argparse
import json
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()

    with open(args.report, encoding="utf-8") as f:
        r = json.load(f)

    s = r["summary"]
    gen = r.get("generator", {})
    tv = gen.get("tool_versions", {})
    print(f"site={r['site']}  status={r.get('audit_status')}  renderer={tv.get('renderer')}  "
          f"checks_run={gen.get('checks_run')}/{gen.get('checks_available')}")
    print(f"total={s['total_findings']}  critical={s.get('critical', 0)}  high={s.get('high', 0)}  "
          f"medium={s.get('medium', 0)}  low={s.get('low', 0)}  by_stage={s.get('by_stage')}")
    for f in r["findings"][: args.top]:
        blocked = f" blocked_by={f['blocked_by']}" if f.get("blocked_by") else ""
        print(f"  {f['id']} [{f['severity']}/{f.get('confidence')}] {f.get('check_id')}{blocked}")
        print(f"      {f['title'][:140]}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
