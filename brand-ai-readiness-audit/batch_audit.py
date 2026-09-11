#!/usr/bin/env python3
"""Run the audit across a fixed list of live sites and summarise the results.

  python batch_audit.py                # the 10-site benchmark (5 well-known, 5 niche)
  python batch_audit.py --stress       # the generalisation set (9 differing purposes)
  python batch_audit.py --all          # both

Nothing here influences the audit: the runner only invokes the entrypoint and reads
whatever report it wrote. One site failing never stops the batch, and a site that fails
is recorded as a failure rather than dropped, so a run can never be mistaken for a
cleaner result than it was.

The category labels below exist ONLY for reading the results table. They are never
passed to the audit and no audit logic is aware of them.
"""
import argparse
import io
import json
import os
import subprocess
import sys
import time

SCRIPT = os.path.join("skills", "audit-orchestrator", "scripts", "run_audit.py")

# The fixed benchmark: exactly 5 well-known, exactly 5 niche. Kept identical across
# runs so before/after comparisons are meaningful.
BENCHMARK = [
    ("google.com",       "https://www.google.com",        "well-known"),
    ("github.com",       "https://github.com",            "well-known"),
    ("wikipedia.org",    "https://en.wikipedia.org",      "well-known"),
    ("bbc.com",          "https://www.bbc.com",           "well-known"),
    ("stripe.com",       "https://stripe.com",            "well-known"),
    ("nomadlist.com",    "https://nomadlist.com",         "niche"),
    ("pudding.cool",     "https://pudding.cool",          "niche"),
    ("bear.blog",        "https://bear.blog",             "niche"),
    ("rawgraphs.io",     "https://rawgraphs.io",          "niche"),
    ("websitecarbon.com", "https://www.websitecarbon.com", "niche"),
]

# The generalisation set: one site per distinct site PURPOSE, to check the audit does
# not assume a marketing-site template.
STRESS = [
    ("duckduckgo.com",   "https://duckduckgo.com",        "search engine"),
    ("developer.mozilla.org", "https://developer.mozilla.org", "documentation"),
    ("reuters.com",      "https://www.reuters.com",       "news/editorial"),
    ("etsy.com",         "https://www.etsy.com",          "ecommerce"),
    ("excalidraw.com",   "https://excalidraw.com",        "web application"),
    ("danluu.com",       "https://danluu.com",            "personal blog"),
    ("simonwillison.net", "https://simonwillison.net",    "portfolio/blog"),
    ("mit.edu",          "https://www.mit.edu",           "educational institution"),
    ("eff.org",          "https://www.eff.org",           "nonprofit/information"),
]


def row_from_report(report):
    sc = report.get("scope", {}) or {}
    su = report.get("summary", {}) or {}
    return {
        "status": report.get("status", "ok"),
        "pages_crawled": sc.get("pages_crawled", 0),
        "html_pages": sc.get("html_pages_analyzed", 0),
        "non_html": sc.get("non_html_resources", 0),
        "resource_kinds": sc.get("resource_kinds", {}),
        "page_roles": sc.get("page_roles", {}),
        "checks_skipped": len(sc.get("checks_skipped", [])),
        "findings_merged": len(sc.get("findings_merged", [])),
        "total_findings": su.get("total_findings", 0),
        "critical": su.get("critical", 0),
        "high": su.get("high", 0),
        "medium": su.get("medium", 0),
        "low": su.get("low", 0),
        "defects": (su.get("by_type", {}) or {}).get("defects", 0),
        "improvements": (su.get("by_type", {}) or {}).get("improvements", 0),
        "discoverability": (su.get("by_dimension", {}) or {}).get("discoverability", 0),
        "engagement": (su.get("by_dimension", {}) or {}).get("engagement", 0),
        "failure": report.get("failure"),
    }


def run_batch(sites, out_dir, max_pages, render):
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for name, url, category in sites:
        out_file = os.path.join(out_dir, f"{name.replace('.', '_')}.json")
        print(f"\n{'=' * 64}\n  Auditing {name} ({category})\n{'=' * 64}")
        t0 = time.time()
        row = {"site": name, "url": url, "category": category}
        cmd = [sys.executable, SCRIPT, url, "--max-pages", str(max_pages), "--out", out_file]
        if render:
            cmd.append("--render")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=420,
                                  encoding="utf-8", errors="replace")
            row["elapsed_s"] = round(time.time() - t0, 1)
            if os.path.exists(out_file):
                with open(out_file, encoding="utf-8") as f:
                    row.update(row_from_report(json.load(f)))
                if row["status"] == "failed":
                    print(f"  FAILED in {row['elapsed_s']}s -- "
                          f"{(row.get('failure') or {}).get('reason')}")
                else:
                    print(f"  {row['status']} in {row['elapsed_s']}s -- "
                          f"{row['total_findings']} findings "
                          f"({row['critical']}C {row['high']}H {row['medium']}M "
                          f"{row['low']}L; {row['defects']} defects / "
                          f"{row['improvements']} improvements) over "
                          f"{row['html_pages']} HTML pages of {row['pages_crawled']} resources")
            else:
                row.update({"status": "no_report",
                            "stderr": (proc.stderr or "")[-400:]})
                print(f"  No report written in {row['elapsed_s']}s")
        except subprocess.TimeoutExpired:
            row.update({"status": "timeout", "elapsed_s": round(time.time() - t0, 1)})
            print(f"  Timed out after {row['elapsed_s']}s")
        except Exception as e:  # noqa: BLE001 - one site must never stop the batch
            row.update({"status": f"runner_error: {e}", "elapsed_s": round(time.time() - t0, 1)})
            print(f"  Runner error: {e}")
        results.append(row)

    summary_file = os.path.join(out_dir, "_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    ok = sum(1 for r in results if r.get("status") in ("ok", "partial"))
    print(f"\n{'=' * 64}\n  {ok}/{len(sites)} produced a report -> {summary_file}\n{'=' * 64}")
    return results


def main():
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--stress", action="store_true", help="run the generalisation set")
    ap.add_argument("--all", action="store_true", help="run both sets")
    ap.add_argument("--max-pages", type=int, default=10)
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()

    if args.all or not args.stress:
        run_batch(BENCHMARK, "batch_reports", args.max_pages, args.render)
    if args.all or args.stress:
        run_batch(STRESS, "stress_reports", args.max_pages, args.render)
    return 0


if __name__ == "__main__":
    sys.exit(main())
