#!/usr/bin/env python3
"""Batch-run the audit against 10 sites and produce a combined summary."""
import json, os, subprocess, sys, time

SCRIPT = os.path.join("skills", "audit-orchestrator", "scripts", "run_audit.py")
OUT_DIR = "batch_reports"
os.makedirs(OUT_DIR, exist_ok=True)

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(sys.stdout, "buffer") else sys.stdout

SITES = [
    # ── Famous (high traffic, high engagement) ──
    ("google.com",      "https://www.google.com",       "famous"),
    ("github.com",      "https://github.com",           "famous"),
    ("wikipedia.org",   "https://en.wikipedia.org",     "famous"),
    ("bbc.com",         "https://www.bbc.com",          "famous"),
    ("stripe.com",      "https://stripe.com",           "famous"),
    # ── Niche (smaller, specialized) ──
    ("nomadlist.com",   "https://nomadlist.com",        "niche"),
    ("pudding.cool",    "https://pudding.cool",         "niche"),
    ("bear.blog",       "https://bear.blog",            "niche"),
    ("rawgraphs.io",    "https://rawgraphs.io",         "niche"),
    ("websitecarbon.com","https://www.websitecarbon.com","niche"),
]

results = []
for name, url, category in SITES:
    out_file = os.path.join(OUT_DIR, f"{name.replace('.', '_')}.json")
    print(f"\n{'='*60}")
    print(f"  Auditing: {name} ({category})")
    print(f"{'='*60}")
    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, SCRIPT, url, "--max-pages", "10", "--out", out_file],
            capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace"
        )
        elapsed = round(time.time() - t0, 1)
        if os.path.exists(out_file):
            with open(out_file, encoding="utf-8") as f:
                report = json.load(f)
            summary = report.get("summary", {})
            results.append({
                "site": name,
                "url": url,
                "category": category,
                "elapsed_s": elapsed,
                "pages_crawled": report.get("scope", {}).get("pages_crawled", 0),
                "total_findings": summary.get("total_findings", 0),
                "critical": summary.get("critical", 0),
                "high": summary.get("high", 0),
                "medium": summary.get("medium", 0),
                "low": summary.get("low", 0),
                "defects": summary.get("by_type", {}).get("defects", 0),
                "improvements": summary.get("by_type", {}).get("improvements", 0),
                "discoverability": summary.get("by_dimension", {}).get("discoverability", 0),
                "engagement": summary.get("by_dimension", {}).get("engagement", 0),
                "status": "ok",
            })
            print(f"  Done in {elapsed}s -- {summary.get('total_findings', '?')} findings "
                  f"({summary.get('critical', 0)}C {summary.get('high', 0)}H "
                  f"{summary.get('medium', 0)}M {summary.get('low', 0)}L)")
        else:
            results.append({"site": name, "url": url, "category": category,
                            "status": "no_report", "elapsed_s": elapsed,
                            "stderr": proc.stderr[-500:] if proc.stderr else ""})
            print(f"  No report produced in {elapsed}s")
            if proc.stderr:
                safe_stderr = proc.stderr[-200:].encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)
                print(f"    stderr: {safe_stderr}")
    except subprocess.TimeoutExpired:
        elapsed = round(time.time() - t0, 1)
        results.append({"site": name, "url": url, "category": category,
                        "status": "timeout", "elapsed_s": elapsed})
        print(f"  Timed out after {elapsed}s")
    except Exception as e:
        elapsed = round(time.time() - t0, 1)
        results.append({"site": name, "url": url, "category": category,
                        "status": f"error: {e}", "elapsed_s": elapsed})
        print(f"  Error: {e}")

# Write combined summary
summary_file = os.path.join(OUT_DIR, "_summary.json")
with open(summary_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print(f"  All done! {len([r for r in results if r['status'] == 'ok'])}/{len(SITES)} succeeded")
print(f"  Summary: {summary_file}")
print(f"{'='*60}")
