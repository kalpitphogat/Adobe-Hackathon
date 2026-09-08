#!/usr/bin/env python3
"""
audit-orchestrator entrypoint: crawl once, run every sub-audit against the shared
cache, then compose one audit report against the fixed schema.

  python run_audit.py <site> [--max-pages N] [--render] [--cache DIR] [--out FILE]

Deterministic, read-only, offline-composable (no external service needed). Findings
are sorted by severity, given stable F-NNN ids, and counted by severity in summary.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))       # marketplace root
SKILLS = os.path.join(ROOT, "skills")
sys.path.insert(0, HERE)
import auditlib as A  # noqa: E402

SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# (skill id, script relative to its skill folder)
SUB_AUDITS = [
    ("crawl-access-audit",           "scripts/check_access.py"),
    ("render-extraction-audit",      "scripts/render_diff.py"),
    ("structured-data-audit",        "scripts/check_structured_data.py"),
    ("freshness-corroboration-audit","scripts/check_freshness.py"),
    ("answerability-audit",          "scripts/check_answerability.py"),
    ("integrity-audit",              "scripts/check_integrity.py"),
    ("engagement-audit",             "scripts/check_engagement.py"),
]


def run_sub(skill_id, script_rel, cache_dir):
    script = os.path.join(SKILLS, skill_id, script_rel)
    try:
        out = subprocess.run([sys.executable, script, cache_dir],
                             capture_output=True, text=True, timeout=120)
        if out.returncode != 0:
            return {"skill": skill_id, "findings": [], "error": out.stderr.strip()[:500]}
        return json.loads(out.stdout or '{"findings": []}')
    except Exception as e:  # noqa: BLE001
        return {"skill": skill_id, "findings": [], "error": str(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site")
    ap.add_argument("--max-pages", type=int, default=12)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--cache", default=None)
    ap.add_argument("--out", default=None, help="write the JSON report to this file")
    ap.add_argument("--html", default=None, help="also write a human-readable HTML report here")
    args = ap.parse_args()

    site = A.normalize_site(args.site)
    cache_dir = args.cache or tempfile.mkdtemp(prefix="audit_")

    # 1. crawl once -> shared cache
    crawler = os.path.join(HERE, "crawler.py")
    cmd = [sys.executable, crawler, site, cache_dir, "--max-pages", str(args.max_pages)]
    if args.render:
        cmd.append("--render")
    try:
        crawl = subprocess.run(cmd, timeout=240)
    except subprocess.TimeoutExpired:
        print(f"error: crawl of {site} timed out after 240s; no report produced.", file=sys.stderr)
        return 1
    meta_path = os.path.join(cache_dir, "meta.json")
    if crawl.returncode != 0 or not os.path.exists(meta_path):
        print(f"error: crawl failed (exit {crawl.returncode}); no cache produced, no report.",
              file=sys.stderr)
        return 1
    meta = A.load_meta(cache_dir)

    # A valid cache with nothing actually reachable (DNS/connection failure, all errors)
    # is not an auditable site — say so clearly instead of emitting a hollow report.
    if not any(p.get("status") for p in meta.get("pages", [])):
        print(f"error: {site} was unreachable — no page returned a response. No report produced.",
              file=sys.stderr)
        return 1

    # 2. fan out sub-audits, tag findings with their source skill
    all_findings = []
    skill_errors = []
    disc, eng = {"crawl-access", "render-extraction", "structured-data",
                 "freshness", "corroboration", "answerability"}, {"engagement"}
    for skill_id, script_rel in SUB_AUDITS:
        res = run_sub(skill_id, script_rel, cache_dir)
        if res.get("error"):
            skill_errors.append({"skill": skill_id, "error": res["error"]})
            print(f"warning: sub-audit {skill_id} did not run: {res['error']}", file=sys.stderr)
        for f in res.get("findings", []):
            f["skill"] = skill_id
            cat = f.get("category", "")
            f["dimension"] = "engagement" if cat in eng else "discoverability"
            all_findings.append(f)

    # 3. sort + stable ids
    all_findings.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 9), f.get("skill", "")))
    for i, f in enumerate(all_findings, 1):
        f["id"] = f"F-{i:03d}"
        f = f  # id first is nicer, but json order is not significant

    counts = {s: sum(1 for f in all_findings if f["severity"] == s)
              for s in ("critical", "high", "medium", "low")}

    report = {
        "site": meta["host"],
        "url": site,
        "audited_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "auditor": {"marketplace": "brand-ai-readiness-audit", "version": "1.0.0"},
        "scope": {
            "pages_crawled": meta["pages_crawled"],
            "render_used": meta["render_available"],
            "robots_respected": True,
            "skills_run": len(SUB_AUDITS) - len(skill_errors),
            "skills_errored": skill_errors,
        },
        "summary": {
            "total_findings": len(all_findings),
            "critical": counts["critical"],
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"],
            "by_dimension": {
                "discoverability": sum(1 for f in all_findings if f["dimension"] == "discoverability"),
                "engagement": sum(1 for f in all_findings if f["dimension"] == "engagement"),
            },
        },
        "findings": [
            {
                "id": f["id"],
                "title": f["title"],
                "severity": f["severity"],
                "dimension": f["dimension"],
                "skill": f["skill"],
                "evidence": f["evidence"],
                "suggested_action": f["suggested_action"],
                **({"checked": f["checked"]} if "checked" in f else {}),
            }
            for f in all_findings
        ],
    }

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    if args.html:
        import render_report
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(render_report.render(report))
        print(f"wrote HTML report -> {args.html}", file=sys.stderr)
    print(text)
    # Non-zero exit if any sub-audit failed to run, so callers/CI notice an incomplete report.
    return 1 if skill_errors else 0


if __name__ == "__main__":
    sys.exit(main())
