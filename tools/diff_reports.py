"""Compare two audit-report.json files by their findings (check_id, severity, confidence, affected URLs).

Usage: python tools/diff_reports.py A/audit-report.json B/audit-report.json
"""
import json
import sys
from collections import Counter


def key(f: dict) -> tuple:
    return (f.get("check_id"), f.get("severity"), f.get("confidence"), tuple(sorted(f.get("affected_urls") or [])))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    a, b = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3])
    ka, kb = Counter(map(key, a["findings"])), Counter(map(key, b["findings"]))
    only_a, only_b = ka - kb, kb - ka
    for label, r in (("A", a), ("B", b)):
        s = r["summary"]
        print(f"{label}: status={r['audit_status']} renderer={r['generator']['tool_versions'].get('renderer')} "
              f"total={s['total_findings']} high={s['high']} critical={s['critical']}")
    print(f"shared findings: {sum((ka & kb).values())}")
    for label, extra in (("only in A", only_a), ("only in B", only_b)):
        for (check, sev, conf, urls), n in sorted(extra.items()):
            print(f"  {label}: {check} [{sev}/{conf}] x{n} {list(urls)[:2]}")
    order_same = [key(f) for f in a["findings"] if key(f) in kb] == [key(f) for f in b["findings"] if key(f) in ka]
    print(f"shared findings in the same order: {order_same}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
