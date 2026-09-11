#!/usr/bin/env python3
"""Classifier tests. Locks in the generalisation rules, including three
mis-classifications found during S3 that a list-of-known-sites approach would
never have surfaced.

Run: python tests/test_profile.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECT = ROOT / "skills" / "site-evidence-collector" / "scripts" / "collect.py"
PROFILE = ROOT / "skills" / "site-profile-classifier" / "scripts" / "profile.py"
sys.path.insert(0, str(PROFILE.parent))

import profile as prof  # noqa: E402

FAILURES: list[str] = []
COUNT = 0


def expect(cond: bool, label: str) -> None:
    global COUNT
    COUNT += 1
    if not cond:
        FAILURES.append(label)


def synth(pages: list[dict]) -> list[dict]:
    out = []
    for p in pages:
        base = {
            "url": p["url"], "status": 200, "wordcount": p.get("wordcount", 300),
            "main_wordcount": p.get("wordcount", 300), "main_text": p.get("text", ""),
            "markup": {"jsonld": p.get("jsonld", []), "microdata": []},
            "links": {"external": p.get("external", [])}, "forms": [], "dates": {},
        }
        out.append(base)
    return out


def archetype_of(pages: list[dict]) -> tuple[str, float]:
    rows = synth(pages)
    for r in rows:
        r["_page_type"], _, _ = prof.classify_page(r)
    a, c, _ = prof.classify_archetype(rows)
    return a, c


# ------------------------------------------- regression: SaaS is not a shop

saas = [
    {"url": "https://x.test/", "text": "Start a 14-day trial of our monitoring platform."},
    {"url": "https://x.test/pricing", "text": "49 USD per month",
     "jsonld": [{"@type": "Product", "name": "Team", "offers": {"@type": "Offer", "price": "49.00"}}]},
    {"url": "https://x.test/features", "text": "Feature overview"},
    {"url": "https://x.test/docs/start", "text": "npm install"},
]
a, c = archetype_of(saas)
expect(
    a != "e-commerce",
    f"a SaaS pricing page marked up as Product/Offer must not classify the site as e-commerce (got {a})",
)
expect(a == "saas-marketing", f"SaaS site classifies as saas-marketing (got {a})")

rows = synth(saas)
pricing = next(r for r in rows if r["url"].endswith("/pricing"))
ptype, pconf, psignals = prof.classify_page(pricing)
expect(ptype == "pricing", f"/pricing with Product schema types as pricing, not product (got {ptype})")
expect(
    any("idiomatic" in s for s in psignals),
    "the classifier explains why it overrode the schema hint rather than doing it silently",
)

# ---------------------------- regression: a footer address is not a business

footer_only = [
    {"url": "https://y.test/", "text": "We build software. 14 Fenchurch Avenue, London EC3M 5BN. +44 20 7946 0102."},
    {"url": "https://y.test/about", "text": "About us. 14 Fenchurch Avenue, London EC3M 5BN."},
    {"url": "https://y.test/pricing", "text": "Start a free trial. 99 USD per month."},
]
a, _ = archetype_of(footer_only)
expect(
    a != "local-business",
    f"a postal address and phone in the footer must not imply local-business (got {a})",
)

real_local = [
    {"url": "https://z.test/", "text": "Open Mon-Fri 9:00am to 6:00pm. 12 High Street.",
     "jsonld": [{"@type": "LocalBusiness", "name": "Z Dental"}]},
    {"url": "https://z.test/contact", "text": "Mon 9am-5pm. Call us."},
]
a, _ = archetype_of(real_local)
expect(a == "local-business", f"LocalBusiness schema plus opening hours does classify (got {a})")

# ------------------------- regression: one blog post is not a publisher

company_blog = [
    {"url": "https://w.test/", "text": "Our platform. Start a trial."},
    {"url": "https://w.test/pricing", "text": "29 USD per month"},
    {"url": "https://w.test/features", "text": "Features"},
    {"url": "https://w.test/blog/one", "text": "Written by Priya Raman",
     "jsonld": [{"@type": "Article", "headline": "One"}]},
]
a, _ = archetype_of(company_blog)
expect(a != "publisher", f"a single bylined blog post must not imply publisher (got {a})")

real_publisher = [
    {"url": f"https://n.test/news/{i}", "text": "By Jane Smith",
     "jsonld": [{"@type": "NewsArticle", "headline": str(i)}]}
    for i in range(6)
] + [{"url": "https://n.test/", "text": "Latest news"}]
a, _ = archetype_of(real_publisher)
expect(a == "publisher", f"a site that is mostly articles does classify as publisher (got {a})")

# ------------------------------------------------- honest uncertainty

vague = [
    {"url": "https://v.test/", "text": "Welcome to our website."},
    {"url": "https://v.test/services", "text": "We offer services."},
]
a, c = archetype_of(vague)
expect(a == "other", f"a site with no archetype signal is 'other', not a guess (got {a})")
expect(c <= 0.4, f"'other' carries low confidence so downstream checks downgrade (got {c})")

# --------------------------------------------------- thresholds merge

profiles = json.loads((PROFILE.parent.parent / "references" / "threshold-profiles.json").read_text(encoding="utf-8"))
merged = prof.merge_thresholds(profiles, "e-commerce")
expect(merged["thin_content_words"]["product"] == 80, "archetype override applies to a nested key")
expect(merged["thin_content_words"]["article"] == 300, "unoverridden nested keys fall through to default")
expect(merged["require_cost_signal"] is True, "archetype-only key is added")
expect("_why" not in merged, "documentation keys are not leaked into thresholds")
merged_default = prof.merge_thresholds(profiles, "nonexistent-archetype")
expect(merged_default == profiles["default"], "unknown archetype falls back to defaults cleanly")

# ------------------------------------------------- end to end on fixtures

tmp = Path(tempfile.mkdtemp(prefix="bara-s3-"))
try:
    env = dict(os.environ, SOURCE_DATE_EPOCH="1780000000")
    expected = {"site_a": "saas-marketing", "site_d": "saas-marketing"}
    for fixture, want in expected.items():
        out = tmp / fixture
        subprocess.run(
            [sys.executable, str(COLLECT), "--offline-root", str(ROOT / "tests" / "fixtures" / fixture), "--out", str(out)],
            capture_output=True, env=env, cwd=str(ROOT), check=True,
        )
        proc = subprocess.run(
            [sys.executable, str(PROFILE), "--bundle", str(out)],
            capture_output=True, text=True, env=env, cwd=str(ROOT),
        )
        expect(proc.returncode == 0, f"{fixture}: profile.py exits 0")
        data = json.loads(proc.stdout)
        expect(data["archetype"] == want, f"{fixture} archetype is {want} (got {data['archetype']})")
        expect(
            data["pages"] and all("page_type" in v and "confidence" in v for v in data["pages"].values()),
            f"{fixture}: every page carries a type and a confidence",
        )
        expect("thresholds" in data and data["thresholds"], f"{fixture}: a threshold profile was selected")

    # site_a specifics: the pricing page must not be a product page
    out = tmp / "site_a"
    data = json.loads(
        subprocess.run([sys.executable, str(PROFILE), "--bundle", str(out)],
                       capture_output=True, text=True, env=env, cwd=str(ROOT)).stdout
    )
    pricing_url = next(u for u in data["pages"] if u.endswith("/pricing"))
    expect(
        data["pages"][pricing_url]["page_type"] == "pricing",
        f"site_a /pricing types as pricing (got {data['pages'][pricing_url]['page_type']})",
    )

    # precondition handling
    proc = subprocess.run([sys.executable, str(PROFILE), "--bundle", str(tmp / "nope")],
                          capture_output=True, text=True, cwd=str(ROOT))
    expect(proc.returncode == 3, f"missing bundle is exit 3 per the CLI contract (got {proc.returncode})")
    expect(proc.stdout.strip() == "", "nothing is written to stdout on a precondition failure")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

if FAILURES:
    print(f"FAILED {len(FAILURES)} of {COUNT} assertions:\n")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print(f"PASS: {COUNT} classifier assertions")
