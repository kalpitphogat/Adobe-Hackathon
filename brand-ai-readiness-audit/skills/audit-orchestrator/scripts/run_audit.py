#!/usr/bin/env python3
"""
audit-orchestrator entrypoint: crawl once, run every sub-audit against the shared
cache, then compose one audit report.

  python run_audit.py <site> [--max-pages N] [--render] [--cache DIR]
                             [--out FILE] [--html FILE]

The orchestrator holds no checks of its own. It owns exactly nine jobs:
  1. understand the site (one polite, robots-respecting crawl)
  2. collect the shared evidence cache
  3. invoke the specialised audits
  4. normalise their envelopes
  5. deduplicate findings that share a root cause
  6. validate that each finding's evidence actually exists
  7. calibrate severity against the documented gates
  8. prioritise the recommendations
  9. emit the required report schema, plus explicit scope

It never invents facts, evidence or counts, and it emits no score: no scoring
formula is implemented, so none is reported.
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

SEV_ORDER = A.SEV_ORDER
TYPE_ORDER = {"defect": 0, "improvement": 1}

# (skill id, script relative to its skill folder)
SUB_AUDITS = [
    ("crawl-access-audit",            "scripts/check_access.py"),
    ("render-extraction-audit",       "scripts/render_diff.py"),
    ("structured-data-audit",         "scripts/check_structured_data.py"),
    ("freshness-corroboration-audit", "scripts/check_freshness.py"),
    ("answerability-audit",           "scripts/check_answerability.py"),
    ("integrity-audit",               "scripts/check_integrity.py"),
    ("engagement-audit",              "scripts/check_engagement.py"),
]

ENGAGEMENT_CATEGORIES = {"engagement"}

# Findings that describe the same root cause. The first entry of a group wins and
# absorbs the others, so one problem is reported once rather than once per skill.
DEDUP_GROUPS = [
    ("structured-data:entity-sameas", "corroboration:entity-sameas"),
]


def _utf8_stdout():
    import io
    try:
        return io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        return sys.stdout


def run_sub(skill_id, script_rel, cache_dir):
    """Run one sub-audit. A crash or timeout is reported, never fatal."""
    script = os.path.join(SKILLS, skill_id, script_rel)
    if not os.path.exists(script):
        return {"skill": skill_id, "findings": [], "error": f"script not found: {script_rel}"}
    try:
        out = subprocess.run(
            [sys.executable, script, cache_dir],
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace")   # sub-audits emit UTF-8 on every OS
    except subprocess.TimeoutExpired:
        return {"skill": skill_id, "findings": [], "error": "timed out after 120s"}
    except Exception as e:  # noqa: BLE001
        return {"skill": skill_id, "findings": [], "error": str(e)[:300]}
    if out.returncode != 0:
        return {"skill": skill_id, "findings": [],
                "error": (out.stderr or "").strip()[:500] or f"exit {out.returncode}"}
    try:
        return json.loads(out.stdout or '{"findings": []}')
    except Exception as e:  # noqa: BLE001 - malformed envelope must not corrupt the report
        return {"skill": skill_id, "findings": [],
                "error": f"unparseable envelope: {e}"}


def validate_evidence(f):
    """Reject a finding whose own evidence does not support reporting it.

    A finding must name what was observed and must not claim a scope it never
    inspected. This is the last line of defence against a check emitting a claim
    with nothing behind it.
    """
    obs = (f.get("evidence_detail", {}) or {}).get("observation", "") or f.get("evidence", "")
    if not obs.strip():
        return False, "no observation recorded"
    if f.get("checked") == 0:
        return False, "checked 0 items"
    if not f.get("title") or not f.get("suggested_action", {}).get("summary"):
        return False, "incomplete finding"
    if f.get("severity") not in A.SEVERITIES:
        return False, f"invalid severity {f.get('severity')!r}"
    return True, None


def deduplicate(findings):
    """Collapse findings that share a dedup key or a known root cause.

    Returns (kept, removed_records) so the report can say what was merged instead
    of silently dropping it.
    """
    absorbed_by = {}
    for group in DEDUP_GROUPS:
        winner = group[0]
        for loser in group[1:]:
            absorbed_by[loser] = winner
    present = {f.get("dedup_key") for f in findings}

    kept, removed, seen = [], [], set()
    for f in findings:
        key = f.get("dedup_key") or f["title"]
        winner = absorbed_by.get(key)
        if winner and winner in present:
            removed.append({"title": f["title"], "skill": f.get("skill"),
                            "merged_into": winner, "reason": "same root cause"})
            continue
        if key in seen:
            removed.append({"title": f["title"], "skill": f.get("skill"),
                            "merged_into": key, "reason": "duplicate finding key"})
            continue
        seen.add(key)
        kept.append(f)
    return kept, removed


def failure_report(site, host, reason, detail, scope_extra=None):
    """A machine-readable failure, never a hollow report that looks like a pass."""
    return {
        "site": host or site,
        "url": site,
        "audited_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "auditor": {"marketplace": "brand-ai-readiness-audit", "version": "2.0.0"},
        "status": "failed",
        "failure": {"reason": reason, "detail": detail},
        "scope": dict({"pages_crawled": 0, "html_pages_analyzed": 0,
                       "robots_respected": True}, **(scope_extra or {})),
        "summary": {"total_findings": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
        "findings": [],
    }


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
    out_stream = _utf8_stdout()

    def finish(report, code):
        text = json.dumps(report, ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(text)
        if args.html:
            try:
                import render_report
                with open(args.html, "w", encoding="utf-8") as fh:
                    fh.write(render_report.render(report))
                print(f"wrote HTML report -> {args.html}", file=sys.stderr)
            except Exception as e:  # noqa: BLE001 - HTML is a convenience, not the contract
                print(f"warning: HTML report not written: {e}", file=sys.stderr)
        print(text, file=out_stream)
        return code

    # ---- 1. crawl once -> shared cache ------------------------------------ #
    cmd = [sys.executable, os.path.join(HERE, "crawler.py"), site, cache_dir,
           "--max-pages", str(args.max_pages)]
    if args.render:
        cmd.append("--render")
    try:
        crawl = subprocess.run(cmd, timeout=300)
        crawl_rc = crawl.returncode
    except subprocess.TimeoutExpired:
        return finish(failure_report(site, "", "crawl_timeout",
                                     "The crawl exceeded its 300s budget."), 1)
    except Exception as e:  # noqa: BLE001
        return finish(failure_report(site, "", "crawl_error", str(e)[:300]), 1)

    meta_path = os.path.join(cache_dir, "meta.json")
    if crawl_rc != 0 or not os.path.exists(meta_path):
        return finish(failure_report(site, "", "crawl_failed",
                                     f"crawler exited {crawl_rc} without producing a cache"), 1)
    try:
        meta = A.load_meta(cache_dir)
    except Exception as e:  # noqa: BLE001
        return finish(failure_report(site, "", "cache_unreadable", str(e)[:300]), 1)

    pages = meta.get("pages", [])
    html_ps = A.html_pages(meta)
    non_html = A.non_html_resources(meta)
    crawl_status = meta.get("crawl_status", "ok")

    if crawl_status == "failed":
        blocked = [p["url"] for p in pages if p.get("robots_blocked")]
        errs = meta.get("fetch_errors", [])[:5]
        detail = (f"{len(pages)} URL(s) were queued; none returned a usable response. "
                  f"{len(blocked)} were disallowed by robots.txt and never requested. "
                  + (f"First errors: {errs}." if errs else ""))
        return finish(failure_report(site, meta.get("host", ""), "no_readable_content", detail,
                                     {"pages_crawled": len(pages),
                                      "robots_blocked_urls": len(blocked),
                                      "fetch_errors": errs}), 1)

    # ---- 2. fan out sub-audits -------------------------------------------- #
    all_findings, skill_errors, skipped_checks = [], [], []
    for skill_id, script_rel in SUB_AUDITS:
        res = run_sub(skill_id, script_rel, cache_dir)
        if res.get("error"):
            skill_errors.append({"skill": skill_id, "error": res["error"]})
            print(f"warning: sub-audit {skill_id} did not run cleanly: {res['error']}",
                  file=sys.stderr)
        for sc in res.get("skipped_checks", []):
            skipped_checks.append(dict(sc, skill=skill_id))
        for f in res.get("findings", []):
            if not isinstance(f, dict) or "title" not in f:
                continue
            f["skill"] = skill_id
            f["dimension"] = ("engagement" if f.get("category") in ENGAGEMENT_CATEGORIES
                              else "discoverability")
            all_findings.append(f)

    # ---- 3. cross-skill root-cause annotation ----------------------------- #
    thin_html_flagged = any(
        f.get("skill") == "render-extraction-audit" and "raw HTML" in f.get("title", "")
        for f in all_findings)
    if thin_html_flagged:
        for f in all_findings:
            if f.get("_thin_html_sensitive"):
                note = ("This page's raw HTML is sparse, so the measurement above may reflect "
                        "client-side rendering reported by render-extraction-audit rather than "
                        "a separate problem.")
                f["evidence"] += " " + note
                f.setdefault("evidence_detail", {})["interpretation"] = (
                    (f["evidence_detail"].get("interpretation", "") + " " + note).strip())

    # ---- 4. validate evidence --------------------------------------------- #
    validated, rejected = [], []
    for f in all_findings:
        ok, why = validate_evidence(f)
        (validated if ok else rejected).append(f if ok else {"title": f.get("title"),
                                                             "skill": f.get("skill"),
                                                             "reason": why})

    # ---- 5. deduplicate ---------------------------------------------------- #
    deduped, merged = deduplicate(validated)

    # When the crawl reached no HTML page at all, the only useful thing to report
    # is why. Optional recommendations about a site whose pages were never read
    # would pad a blocked crawl into something that reads like an audit.
    if not html_ps:
        dropped = [f for f in deduped if f.get("finding_type") == "improvement"]
        if dropped:
            deduped = [f for f in deduped if f.get("finding_type") != "improvement"]
            skipped_checks.append({
                "skill": "audit-orchestrator",
                "check": "proactive improvement recommendations",
                "reason": f"no HTML page was analysed in this crawl, so {len(dropped)} "
                          "optional recommendation(s) were withheld. What the crawl could "
                          "not reach is reported instead.",
            })

    # ---- 6. calibrate severity -------------------------------------------- #
    for f in deduped:
        A.calibrate(f)

    # ---- 7. prioritise + stable ids --------------------------------------- #
    deduped.sort(key=lambda f: (TYPE_ORDER.get(f.get("finding_type", "defect"), 9),
                                SEV_ORDER.get(f["severity"], 9),
                                f.get("skill", ""), f.get("title", "")))
    for i, f in enumerate(deduped, 1):
        f["id"] = f"F-{i:03d}"

    counts = {s: sum(1 for f in deduped if f["severity"] == s) for s in A.SEVERITIES}

    # ---- 8. emit ----------------------------------------------------------- #
    report = {
        "site": meta["host"],
        "url": site,
        "audited_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "auditor": {"marketplace": "brand-ai-readiness-audit", "version": "2.0.0"},
        "status": "ok" if crawl_status == "ok" and not skill_errors else "partial",
        "scope": {
            "requested_url": meta.get("requested_site", site),
            **({"site_moved_to": meta["site_moved_to"]} if meta.get("site_moved_to") else {}),
            "pages_crawled": meta.get("pages_crawled", 0),
            "html_pages_analyzed": len(html_ps),
            "non_html_resources": len(non_html),
            "resource_kinds": meta.get("resource_kinds", {}),
            "page_roles": meta.get("page_roles", {}),
            "max_pages_requested": meta.get("max_pages"),
            "sample_based": meta.get("pages_crawled", 0) >= meta.get("max_pages", 0),
            "crawl_status": crawl_status,
            "render_used": meta.get("render_available", False),
            "robots_respected": True,
            "robots_blocked_urls": sum(1 for p in pages if p.get("robots_blocked")),
            "fetch_errors": meta.get("fetch_errors", [])[:5],
            "skills_run": len(SUB_AUDITS) - len(skill_errors),
            "skills_errored": skill_errors,
            "checks_skipped": skipped_checks,
            "findings_merged": merged,
            "findings_rejected_for_weak_evidence": rejected,
            "note": ("All counts describe the sampled resources listed above, not the whole "
                     "site, unless a finding states otherwise."),
        },
        "summary": {
            "total_findings": len(deduped),
            "critical": counts["critical"],
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"],
            "by_dimension": {
                "discoverability": sum(1 for f in deduped if f["dimension"] == "discoverability"),
                "engagement": sum(1 for f in deduped if f["dimension"] == "engagement"),
            },
            "by_type": {
                "defects": sum(1 for f in deduped if f.get("finding_type", "defect") == "defect"),
                "improvements": sum(1 for f in deduped if f.get("finding_type") == "improvement"),
            },
        },
        "findings": [
            {
                "id": f["id"],
                "title": f["title"],
                "severity": f["severity"],
                "dimension": f["dimension"],
                "category": f.get("category", ""),
                "skill": f["skill"],
                "finding_type": f.get("finding_type", "defect"),
                "confidence": f.get("confidence", "high"),
                "evidence": f["evidence"],
                "evidence_detail": f.get("evidence_detail", {}),
                "suggested_action": f["suggested_action"],
                **({"mechanism": f["mechanism"]} if f.get("mechanism") else {}),
                **({"page_role": f["page_role"]} if f.get("page_role") else {}),
                **({"scope": f["scope"]} if f.get("scope") else {}),
                **({"checked": f["checked"],
                    "checked_unit": f.get("checked_unit", "sampled HTML pages")}
                   if "checked" in f else {}),
                **({"severity_capped_from": f["severity_capped_from"],
                    "severity_cap_reason": f["severity_cap_reason"]}
                   if "severity_capped_from" in f else {}),
            }
            for f in deduped
        ],
    }
    # A partial run is reported, not silently passed off as a complete audit.
    return finish(report, 1 if skill_errors else 0)


if __name__ == "__main__":
    sys.exit(main())
