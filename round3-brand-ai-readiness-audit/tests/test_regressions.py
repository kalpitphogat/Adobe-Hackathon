#!/usr/bin/env python3
"""Regression tests for every false positive found and fixed during S4.

Each of these was discovered by the healthy-control fixture producing a finding
it should not have. A corrected control count is NOT a regression test: a future
change can reintroduce the bug and the count still looks plausible. Each fix
below therefore has an assertion that fails specifically when that bug returns.

Run: python tests/test_regressions.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

FAILURES: list[str] = []
COUNT = 0


def expect(cond: bool, label: str) -> None:
    global COUNT
    COUNT += 1
    if not cond:
        FAILURES.append(label)


def load(skill: str, module: str):
    """Import one skill's module with only that skill's scripts on the path."""
    path = str(SKILLS / skill / "scripts")
    saved = list(sys.path)
    sys.path.insert(0, path)
    try:
        for name in list(sys.modules):
            mod = sys.modules[name]
            if getattr(mod, "__file__", None) and str(SKILLS) in str(mod.__file__):
                if name not in ("json", "re"):
                    del sys.modules[name]
        return __import__(module)
    finally:
        sys.path = [path] + [p for p in saved if p != path]


# =====================================================================
# R1. observed_text() must return MAIN content, never the whole body.
#
# The bug: for a rendered page it returned rendered_text, which is the entire
# body including navigation, header and footer. Every check that reasons about
# how a page OPENS then saw the nav menu as the first sentence. This corrupted
# no_direct_answer_block, fact_coverage_gap, no_value_proposition and
# assumes_prior_context simultaneously, which is why it gets the most coverage
# here.
# =====================================================================

bundle_mod = load("answerability-audit", "bundle")


class _FakeBundle(bundle_mod.Bundle):
    def __init__(self):  # noqa: D107 - deliberately skips file I/O
        self.meta = {}
        self.pages = []
        self.robots_text = ""
        self.sitemap = {}
        self.probes = {}


NAV = "Acme Home Pricing Docs Blog About Contact"
FOOTER = "Privacy Terms Copyright 2026 Acme Ltd"
MAIN = "Acme Analytics is monitoring software for data teams. It watches pipeline freshness."

rendered_page = {
    "url": "https://e.test/",
    "status": 200,
    "rendered_available": True,
    "rendered_text": f"{NAV} {MAIN} {FOOTER}",
    "rendered_main_text": MAIN,
    "main_text": MAIN,
    "text": f"{NAV} {MAIN} {FOOTER}",
}

fb = _FakeBundle()
got = fb.observed_text(rendered_page)
expect(got == MAIN, f"R1: observed_text returns main content on a rendered page (got {got[:60]!r})")
expect("Pricing Docs Blog" not in got, "R1: observed_text excludes the navigation menu")
expect("Privacy Terms Copyright" not in got, "R1: observed_text excludes the footer")
expect(
    not got.startswith("Acme Home"),
    "R1: the first sentence of a rendered page is its content, NOT its nav menu",
)

# falls back sensibly when the collector predates rendered_main_text
legacy = dict(rendered_page)
del legacy["rendered_main_text"]
expect(
    fb.observed_text(legacy) == f"{NAV} {MAIN} {FOOTER}",
    "R1: falls back to rendered_text when rendered_main_text is absent, rather than returning nothing",
)
unrendered = {"url": "https://e.test/x", "status": 200, "rendered_available": False,
              "main_text": MAIN, "text": f"{NAV} {MAIN}"}
expect(fb.observed_text(unrendered) == MAIN, "R1: an unrendered page still yields main content")

# every duplicated copy of the reader must carry the same fix
for skill in ("crawl-access-audit", "render-gap-audit", "structured-data-audit",
              "answerability-audit", "trust-freshness-audit", "engagement-audit"):
    src = (SKILLS / skill / "scripts" / "bundle.py").read_text(encoding="utf-8")
    expect(
        "rendered_main_text" in src,
        f"R1: {skill}'s copy of bundle.py carries the main-content fix (they are duplicated on purpose)",
    )

# =====================================================================
# R2. Entity matching must use a DISTINCTIVE TOKEN, not the literal string.
#
# The bug: a schema name like "Northwind Analytics Team" was required verbatim,
# so prose saying "Northwind Analytics" failed every window and the page scored
# 0/11 facts covered.
# =====================================================================

sim = load("answerability-audit", "retrievability_sim")

window = "Northwind Analytics costs 49 USD per month on the Team plan and is billed monthly."
ok, why = sim.self_contained(window, "Northwind Analytics Team")
expect(ok, f"R2: a superset schema name matches prose naming the entity (got {why})")

ok, why = sim.self_contained("Widgets are sold in packs of ten and ship within a day.", "Northwind Analytics")
expect(not ok, "R2: a window that genuinely never names the entity still fails")

ok, _ = sim.self_contained("It costs 49 USD per month and is billed monthly.", "Northwind Analytics")
expect(not ok, "R2: an unresolved pronoun opener still fails regardless of entity matching")

ok, _ = sim.self_contained(
    "As mentioned above, Northwind Analytics costs 49 USD per month.", "Northwind Analytics"
)
expect(not ok, "R2: a backward reference still fails regardless of entity matching")

# =====================================================================
# R3. A definitional sentence does not require an article.
#
# The bug: the regex demanded "is a" / "is the", so "X is monitoring software
# for data teams" - a perfectly good definition - did not count, and
# no_direct_answer_block fired on four control pages including the homepage.
# =====================================================================

fb_mod = load("answerability-audit", "fact_blocks")

for sentence in (
    "Northwind Analytics is monitoring software for data engineering teams.",
    "Northwind Analytics is a monitoring tool.",
    "Northwind Analytics provides pipeline monitoring.",
    "Northwind Analytics helps data teams find stale tables.",
    "Northwind Analytics enables freshness alerting.",
):
    expect(
        bool(fb_mod.DEFINITIONAL.search(sentence)),
        f"R3: recognised as definitional without requiring an article: {sentence!r}",
    )
expect(
    not fb_mod.DEFINITIONAL.search("Northwind Analytics, London, 2021."),
    "R3: a fragment with no verb is still not definitional",
)

# =====================================================================
# R4. Pages whose job is not to pitch must not demand a value proposition,
#     and informational pages must not demand social proof.
# =====================================================================

orient = load("engagement-audit", "orientation")
for page_type in ("about", "contact", "pricing", "article", "docs", "category", "utility"):
    expect(
        page_type in orient.NO_VALUE_PROP_TYPES,
        f"R4: a {page_type} page is exempt from the above-fold value-proposition check",
    )
for page_type in ("home", "product"):
    expect(
        page_type not in orient.NO_VALUE_PROP_TYPES,
        f"R4: a {page_type} page is still expected to state a value proposition",
    )

blockers = load("engagement-audit", "blockers")
for page_type in ("about", "contact"):
    expect(
        page_type not in blockers.CONVERSION_TYPES,
        f"R4: a {page_type} page is exempt from the social-proof check",
    )
for page_type in ("home", "product", "pricing"):
    expect(
        page_type in blockers.CONVERSION_TYPES,
        f"R4: a {page_type} page is still expected to carry social proof",
    )

# =====================================================================
# R5. Second-person instructional voice is not "assuming prior context".
#
# The bug: a bare "your plan" / "your account" matched, so documentation saying
# "up to your plan limit" was reported as assuming a session the visitor did not
# have. Only phrasings that presume a PRIOR SESSION may match.
# =====================================================================

ctx = load("engagement-audit", "context_retention")

for benign in (
    "Start with ten tables; you can add more at any time up to your plan limit.",
    "Enter your email address to continue.",
    "Connect your warehouse and choose the tables to monitor.",
    "Your data is never read by Northwind Analytics.",
):
    ok, why = ctx.self_contained(benign)
    expect(ok, f"R5: normal second-person instruction is not flagged: {benign[:48]!r} ({why})")

for genuine in (
    "Continue where you left off in the setup wizard.",
    "Welcome back to the dashboard.",
    "As we discussed earlier, the migration completes overnight.",
    "Review your selected plan before confirming.",
):
    ok, _ = ctx.self_contained(genuine)
    expect(not ok, f"R5: copy that presumes a prior session IS flagged: {genuine[:48]!r}")

expect(
    "article" in ctx.ONWARD_PATH_TYPES and "docs" in ctx.ONWARD_PATH_TYPES,
    "R5: onward-path applies where reading ends and a next step is needed",
)
for page_type in ("home", "pricing", "contact", "about"):
    expect(
        page_type not in ctx.ONWARD_PATH_TYPES,
        f"R5: a {page_type} page uses global navigation as its onward path and is exempt",
    )

# =====================================================================
# R6. act.orient.h1_cta_mismatch stays CUT.
#
# Cut on evidence during S4: it fired on 7 of 8 control pages, including the
# homepage where H1 "Pipeline monitoring for data engineering teams" and CTA
# "Start a 14-day trial" is a CORRECT pairing. A headline names a category and a
# call to action names an action, so zero token overlap is the expected case.
# =====================================================================

inventory = json.loads((ROOT / "tests" / "expected_inventory.json").read_text(encoding="utf-8"))
ids = {c["id"] for c in inventory["checks"]}
expect(
    "act.orient.h1_cta_mismatch" not in ids,
    "R6: the cut check has not been reintroduced into the inventory",
)
expect(
    any(c["id"] == "act.orient.h1_cta_mismatch" for c in inventory.get("cut_checks", [])),
    "R6: the cut is recorded with its reasoning, not silently deleted",
)
expect(
    not any(c["id"] == "act.orient.h1_cta_mismatch" for c in getattr(orient, "CHECKS", [])),
    "R6: orientation.py does not declare the cut check",
)

# =====================================================================
# R7. The portability check must not flag prose that merely names a sibling.
#
# Found when every duplicated bundle.py failed because its docstring explains
# WHY it is duplicated and names ai-readiness-orchestrator.
# =====================================================================

sys.path.insert(0, str(ROOT / "tests"))
import validate_marketplace as vm  # noqa: E402

res = vm.Results(strict=False)
vm.check_no_cross_skill_imports(res)
rows = {name: status for status, name, _ in res.rows}
expect(
    rows.get("portability.no_cross_skill_imports") == "PASS",
    "R7: docstrings naming a sibling skill do not trip the portability check",
)

# =====================================================================
# R8. Main-content extraction must find the content on a PRE-HTML5 layout.
#
# FN-2, found on a live static site: navigation built as a <table> rather than a
# <nav> is invisible to tag-based chrome detection, so the page's "first
# sentence" came out as its own menu. That corrupted no_direct_answer_block,
# fact_coverage_gap, no_value_proposition and assumes_prior_context at once.
#
# The only thing separating a menu from prose on such a page is LINK DENSITY.
# =====================================================================

dom_mod = load("site-evidence-collector", "dom")
legacy = (ROOT / "tests" / "fixtures" / "legacy_table_nav.html").read_text(encoding="utf-8")
doc = dom_mod.parse_html(legacy, "https://rockwell.test/")

expect(
    doc.main_text.strip().startswith("Rockwell Instrument Company"),
    f"R8: the page opens with its content, not its navigation "
    f"(got {doc.main_text[:60]!r})",
)
for nav_term in ("Transducers", "Distributors", "Site map", "Spare parts", "Returns"):
    expect(
        nav_term not in doc.main_text,
        f"R8: link-density scoring excludes the menu item {nav_term!r} from main content",
    )
expect(doc.main_wordcount >= 100, f"R8: the real prose survives (got {doc.main_wordcount} words)")
expect(
    doc.main_wordcount < doc.wordcount,
    "R8: main content is a strict subset of the body, so something was excluded",
)

# The guard: on a page that is genuinely a list of links, stripping link blocks
# must NOT empty the page out.
listing = """<html><body><div><h1>All guides</h1>
<ul><li><a href="/a">Guide A</a></li><li><a href="/b">Guide B</a></li>
<li><a href="/c">Guide C</a></li><li><a href="/d">Guide D</a></li></ul></div></body></html>"""
listing_doc = dom_mod.parse_html(listing, "https://e.test/guides")
expect(
    listing_doc.main_wordcount > 0,
    "R8: a genuine listing page is not emptied by link-block stripping",
)

if FAILURES:
    print(f"FAILED {len(FAILURES)} of {COUNT} assertions:\n")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print(f"PASS: {COUNT} false-positive regression assertions")
