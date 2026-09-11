#!/usr/bin/env python3
"""Render report.json as a GitHub Actions job summary.

Kept as a real file rather than an inline heredoc so it can be linted, compiled by
CI, and read without YAML escaping getting in the way. Tolerates a missing report
and a failure report, because the audit step runs with `if: always()`.
"""
import json
import sys


def main():
    try:
        with open("report.json", encoding="utf-8") as fh:
            r = json.load(fh)
    except Exception as e:  # noqa: BLE001 - the run may have produced nothing at all
        print(f"No report produced: {e}")
        return 0

    out = sys.stdout
    try:
        out.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    s = r.get("summary", {}) or {}
    sc = r.get("scope", {}) or {}
    print(f"## Audit — {r.get('site', '?')}")

    if r.get("status") == "failed":
        fail = r.get("failure", {}) or {}
        print(f"\n**No audit was produced.** `{fail.get('reason', 'unknown')}` — "
              f"{fail.get('detail', '')}")
        return 0

    print(f"\nAnalysed **{sc.get('html_pages_analyzed', '?')}** HTML pages of "
          f"**{sc.get('pages_crawled', '?')}** resources crawled "
          f"({sc.get('non_html_resources', 0)} non-HTML) · "
          f"render used: {str(sc.get('render_used', False)).lower()} · "
          f"status: {r.get('status', 'ok')}\n")
    print(f"**{s.get('total_findings', 0)} findings** — "
          f"{s.get('critical', 0)} critical · {s.get('high', 0)} high · "
          f"{s.get('medium', 0)} medium · {s.get('low', 0)} low")

    bt = s.get("by_type", {}) or {}
    bd = s.get("by_dimension", {}) or {}
    print(f"\n{bt.get('defects', 0)} defects · {bt.get('improvements', 0)} improvements "
          f"| discoverability {bd.get('discoverability', 0)} · "
          f"engagement {bd.get('engagement', 0)}\n")

    roles = sc.get("page_roles") or {}
    if roles:
        print("Page roles: " + ", ".join(f"{k} {v}" for k, v in roles.items()) + "\n")

    findings = r.get("findings", []) or []
    if findings:
        print("| Sev | Type | Finding | Fix |")
        print("|-----|------|---------|-----|")
        for f in findings:
            fix = (f.get("suggested_action", {}) or {}).get("summary", "").replace("|", r"\|")
            title = f.get("title", "").replace("|", r"\|")
            print(f"| {f.get('severity', '')} | {f.get('finding_type', 'defect')} "
                  f"| {title} | {fix} |")
    else:
        print("No finding met the evidence bar in this audit.")

    skipped = sc.get("checks_skipped") or []
    if skipped:
        print(f"\n<details><summary>{len(skipped)} check(s) did not run, and why"
              "</summary>\n")
        for c in skipped:
            print(f"- **{c.get('check', '')}** — {c.get('reason', '')}")
        print("\n</details>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
