#!/usr/bin/env python3
"""Condense a folder of audit reports into one table a person can review.

    python3 round4/tools/digest.py RUNS_DIR [--evidence 3]

Finds every audit-report.json below RUNS_DIR (as written by live_matrix.py or
by the entrypoint itself) and prints, per site: status, pages, severity counts,
the cascade, a histogram of which checks fired at which severity/confidence,
and the evidence behind the top findings. Read-only; standard library only.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

SEV = ["critical", "high", "medium", "low", "info"]

# Titles CDNs and WAFs give the page they serve a crawler instead of the real one.
CHALLENGE = re.compile(r"client challenge|just a moment|attention required|access denied|"
                       r"are you a (human|robot)|verify you are human|request blocked|you have been blocked|"
                       r"pardon our interruption", re.I)


def challenge_pages(report_path: Path) -> list[str]:
    """Pages in the evidence bundle whose title says a bot check answered, not the site."""
    pages = report_path.parent / "evidence" / "pages.jsonl"
    if not pages.is_file():
        return []
    hits = []
    for line in pages.read_text(encoding="utf-8").splitlines():
        try:
            page = json.loads(line)
        except json.JSONDecodeError:
            continue
        if CHALLENGE.search(page.get("title") or ""):
            hits.append(f"{page.get('url')} ({page.get('title')!r})")
    return hits


def one_line(text, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--evidence", type=int, default=3)
    args = ap.parse_args(argv)

    reports = sorted(args.root.rglob("audit-report.json"))
    if not reports:
        print(f"no audit-report.json under {args.root}")
        return 1

    table = []
    for path in reports:
        r = json.loads(path.read_text(encoding="utf-8"))
        s, ev = r["summary"], r.get("evidence_bundle") or {}
        findings = r["findings"]
        blockers = collections.Counter(f["blocked_by"] for f in findings if f.get("blocked_by"))
        print(f"\n### {r['site']}  status={r['audit_status']}  pages={ev.get('pages_fetched')}  "
              f"findings={s['total_findings']} (C{s['critical']} H{s['high']} M{s['medium']} L{s['low']} "
              f"I{s['info']})  disc/eng={s['by_category']['discoverability']}/{s['by_category']['engagement']}  "
              f"capped={s['blocked_findings']} {dict(blockers) if blockers else ''}")
        hist = collections.Counter((f["severity"], f.get("confidence"), f.get("check_id")) for f in findings)
        for (sev, conf, cid), n in sorted(hist.items(), key=lambda kv: (SEV.index(kv[0][0]), kv[0][2])):
            print(f"   {sev:<8} {conf:<10} x{n:<3} {cid}")
        for f in findings[: args.evidence]:
            a = f.get("suggested_action") or {}
            print(f"   > {f['id']} {f['severity']}/{f.get('confidence')} ICE {a.get('ice')} {f.get('check_id')}: "
                  f"{one_line(f['title'], 120)}")
            print(f"     evidence: {one_line(f['evidence'], 420)}")
        bot_checks = challenge_pages(path)
        if bot_checks:
            print(f"   !! {len(bot_checks)} sampled page(s) were a bot-check page, audited as content: "
                  f"{'; '.join(bot_checks[:4])}")
        for lim in r.get("limitations") or []:
            if "probe-bot-ua" not in (lim.get("reason") or ""):
                print(f"   limitation: {one_line(lim.get('reason'), 220)}")
        table.append((r["site"], r["audit_status"], ev.get("pages_fetched"), s, findings[0] if findings else None))

    print("\n### overview")
    print(f"   {'site':<32} {'status':<21} pages  C  H   M   L  I  total  top finding")
    for site, status, pages, s, top in table:
        head = f"{top['severity']}/{top.get('confidence')} {top.get('check_id')}" if top else "-"
        print(f"   {site:<32} {status:<21} {pages!s:>5} {s['critical']:>2} {s['high']:>2} {s['medium']:>3} "
              f"{s['low']:>3} {s['info']:>2} {s['total_findings']:>6}  {head}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
