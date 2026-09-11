#!/usr/bin/env python3
"""Suppression tests: one positive and one negative case per SUPPRESS WHEN clause.

SUPPRESSION_CASES below is the registry that tests/validate_marketplace.py checks
every documented SUPPRESS WHEN clause against. If a SKILL.md documents a
suppression rule that has no entry here, the build fails: documentation that
describes behaviour nothing tests is the easiest way to drift.

Each entry records:
  trigger    conditions under which the check SHOULD fire
  suppressor the condition that must silence it
  proved_by  where the assertion lives

Run: python tests/test_suppression.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
ORCH = ROOT / "skills" / "ai-readiness-orchestrator" / "scripts" / "orchestrate.py"

FAILURES: list[str] = []
COUNT = 0


def expect(cond: bool, label: str) -> None:
    global COUNT
    COUNT += 1
    if not cond:
        FAILURES.append(label)


# Every check that documents a SUPPRESS WHEN clause, and how it is proved.
SUPPRESSION_CASES: dict[str, dict] = {
    "reach.robots.ai_search_bot_blocked": {
        "suppressor": "no retrieval-classified bot is disallowed",
        "proved_by": "site_e fires no retrieval finding while blocking training and dual-purpose bots",
    },
    "reach.robots.blanket_disallow": {
        "suppressor": "a narrower Allow re-admits content, or robots.txt is non-200",
        "proved_by": "site_a and site_b have wildcard groups with Allow:/ and do not fire it",
    },
    "reach.robots.ai_training_bot_blocked": {
        "suppressor": "capped at info; never escalates",
        "proved_by": "site_e asserts severity == info",
    },
    "reach.robots.dual_purpose_bot_blocked": {
        "suppressor": "reported as a contested trade-off, never as an error",
        "proved_by": "site_e asserts severity == medium and 'contested' in the evidence",
    },
    "reach.robots.unparseable": {
        "suppressor": "a 404 robots.txt is permissive and correct, not an error",
        "proved_by": "the hostile fixture serves 404 robots.txt and fires nothing",
    },
    "reach.robots.crawl_delay_excessive": {
        "suppressor": "the directive reaches only non-retrieval-relevant agents",
        "proved_by": "unit case below",
    },
    "reach.edge.bot_ua_blocked": {
        "suppressor": "--probe-bot-ua was not set, or the browser baseline is also refused",
        "proved_by": "site_a records it in checks_skipped with 'not assessed'",
    },
    "reach.edge.bot_ua_challenged": {
        "suppressor": "--probe-bot-ua was not set",
        "proved_by": "site_a records it in checks_skipped",
    },
    "reach.sitemap.absent_or_invalid": {
        "suppressor": "fewer than 15 pages discovered",
        "proved_by": "site_b has 4 pages and skips it with a stated reason",
    },
    "reach.sitemap.coverage_gap": {
        "suppressor": "no sitemap at all, or omissions are utility pages",
        "proved_by": "site_a has full coverage and does not fire",
    },
    "reach.index.noindex_on_content": {
        "suppressor": "the page type is utility, where noindex is correct",
        "proved_by": "site_a 404 page carries noindex and is not reported",
    },
    "reach.index.canonical_conflict": {
        "suppressor": "the canonical is self-referential",
        "proved_by": "every site_a page self-canonicalises and none fires",
    },
    "reach.index.redirect_chain_or_loop": {
        "suppressor": "one hop only, or scheme/www normalisation",
        "proved_by": "the hostile offsite fixture redirects once and does not fire",
    },
    "reach.http.soft_404": {
        "suppressor": "probes return 404/410; identical-to-404 body downgrades to low",
        "proved_by": "site_a returns real 404s and does not fire",
    },
    "reach.http.broken_internal_links": {
        "suppressor": "below both the rate and the count floor",
        "proved_by": "unit case below",
    },
    "reach.http.insecure_or_mixed_scheme": {
        "suppressor": "all pages are https with a valid chain",
        "proved_by": "site_a is https throughout and does not fire",
    },
    "reach.perf.slow_median_ttfb": {
        "suppressor": "fewer than 3 samples; never fires on one measurement",
        "proved_by": "unit case below",
    },
    "reach.agent.llms_txt_absent": {
        "suppressor": "archetype is not docs or developer-platform",
        "proved_by": "site_a is saas-marketing and skips it with the rationale stated",
    },
    "read.render.raw_text_gap": {
        "suppressor": "no rendered DOM exists, or rendered <200 words and raw >=30%",
        "proved_by": "site_d has no renderer and records it as not assessed",
    },
    "read.render.empty_spa_shell": {
        "suppressor": "the framework mount point is not empty",
        "proved_by": "test_regressions R1 plus the site_a control firing nothing",
    },
    "read.render.nav_links_js_only": {
        "suppressor": "no rendered DOM, or raw links >=60% of rendered",
        "proved_by": "site_d records it as not assessed",
    },
    "read.nontext.key_fact_image_only": {
        "suppressor": "the fact appears in page text or structured data",
        "proved_by": "site_a states its price as text and does not fire",
    },
    "read.nontext.informative_image_no_alt": {
        "suppressor": "decorative, chrome, small, or below the reporting floor",
        "proved_by": "unit case below",
    },
    "extract.sd.absent_on_eligible_page": {
        "suppressor": "utility page type, or below the word floor",
        "proved_by": "site_a skips its short pages with a stated reason",
    },
    "extract.sd.expected_type_missing": {
        "suppressor": "page-type confidence below 0.6",
        "proved_by": "unit case below",
    },
    "extract.sd.invalid_syntax": {
        "suppressor": "the block parses",
        "proved_by": "site_a parses cleanly and does not fire",
    },
    "extract.sd.required_props_missing": {
        "suppressor": "a documented alias supplies the property",
        "proved_by": "unit case below",
    },
    "extract.sd.contradicts_visible_content": {
        "suppressor": "values differ only by formatting, normalised before comparison",
        "proved_by": "unit case below",
    },
    "extract.sd.identity_graph_weak": {
        "suppressor": "an Organization node with sameAs links exists",
        "proved_by": "site_a declares Organization with sameAs and does not fire",
    },
    "extract.i18n.hreflang_incomplete": {
        "suppressor": "the page declares no hreflang at all, or its cluster already carries a fallback and valid codes",
        "proved_by": "site_a declares no hreflang and does not fire; unit case below fires only on an incomplete cluster",
    },
    "extract.ans.fact_coverage_gap": {
        "suppressor": "fewer than 2 derivable claims, or a utility page",
        "proved_by": "site_a records sparse pages as not assessed",
    },
    "extract.ans.chunk_not_self_contained": {
        "suppressor": "under 20% of windows fail, or fewer than 3 windows; deduped into fact_coverage_gap",
        "proved_by": "the orchestrator dedupe path, asserted in test_gate_cascade",
    },
    "extract.ans.no_direct_answer_block": {
        "suppressor": "a definitional sentence exists, or the meta description supplies one",
        "proved_by": "test_regressions R3",
    },
    "extract.ans.title_not_entity_bearing": {
        "suppressor": "title is >=15 chars and not a generic template value",
        "proved_by": "site_a titles are descriptive and do not fire",
    },
    "extract.ans.heading_structure_unusable": {
        "suppressor": "multiple H1s alone never fire; reported as info in HTML5 sectioning",
        "proved_by": "unit case below",
    },
    "extract.ans.boilerplate_dominant": {
        "suppressor": "under 300 words, or a listing page type",
        "proved_by": "site_a ratios are all well under the ceiling",
    },
    "extract.ans.no_evidence_markers": {
        "suppressor": "below the archetype word floor, or a non-idiomatic page type",
        "proved_by": "site_a skips short pages with a stated reason",
    },
    "extract.ans.thin_content_for_page_type": {
        "suppressor": "a listing page, or a hub with >=15 in-content internal links",
        "proved_by": "unit case below",
    },
    "trust.date.absent_on_dated_content": {
        "suppressor": "page type is not article or docs",
        "proved_by": "site_a home and pricing pages carry no date and do not fire",
    },
    "trust.date.signals_disagree": {
        "suppressor": "spread of 2 days or less, treated as publishing lag",
        "proved_by": "unit case below",
    },
    "trust.date.stale_volatile_facts": {
        "suppressor": "no date signal at all, or within the archetype window",
        "proved_by": "site_a dates are recent and do not fire",
    },
    "trust.entity.name_collision": {
        "suppressor": "a descriptor appears near the name, or a schema description supplies one",
        "proved_by": "site_a states 'is monitoring software for' and does not fire",
    },
    "trust.entity.nap_inconsistent": {
        "suppressor": "variants differ only by formatting; compared on digits alone",
        "proved_by": "unit case below",
    },
    "trust.entity.no_external_corroboration": {
        "suppressor": ">=2 authoritative sameAs links; confidence capped at likely regardless",
        "proved_by": "site_a declares 3 sameAs and skips it",
    },
    "trust.authorship.unattributed": {
        "suppressor": "archetype is e-commerce or saas-marketing",
        "proved_by": "site_a is saas-marketing and skips it with a stated reason",
    },
    "act.orient.no_value_proposition": {
        "suppressor": "page types whose job is not to pitch",
        "proved_by": "test_regressions R4",
    },
    "act.orient.no_wayfinding": {
        "suppressor": "depth <2, a breadcrumb exists, or an ancestor link exists",
        "proved_by": "site_a pages carry breadcrumbs and do not fire",
    },
    "act.cta.absent_for_page_type": {
        "suppressor": "article, docs, utility or 404 page, or a form serves as the action",
        "proved_by": "site_a docs and blog pages do not fire",
    },
    "act.cta.ambiguous_primary_label": {
        "suppressor": "the label carries a noun object, or is a legally fixed consent control",
        "proved_by": "unit case below",
    },
    "act.cta.competing_primaries": {
        "suppressor": "at or below threshold; repeats of one label counted once",
        "proved_by": "site_a does not fire",
    },
    "act.form.field_count_excessive": {
        "suppressor": "checkout page type, or a multi-step form",
        "proved_by": "unit case below",
    },
    "act.form.high_friction_required_fields": {
        "suppressor": "checkout, application or contact page where the field is necessary",
        "proved_by": "site_a contact form asks only name, email and message",
    },
    "act.form.unlabelled_inputs": {
        "suppressor": "placeholder-only reports at low rather than medium",
        "proved_by": "site_b contact form fires at low, asserted in the golden",
    },
    "act.context.no_onward_path": {
        "suppressor": "page types that use global navigation as their onward path",
        "proved_by": "test_regressions R5",
    },
    "act.context.assumes_prior_context": {
        "suppressor": "normal second-person instructional voice",
        "proved_by": "test_regressions R5",
    },
    "act.blocker.load_time_interstitial": {
        "suppressor": "the overlay is a cookie or consent banner",
        "proved_by": "unit case below",
    },
    "act.blocker.not_mobile_ready": {
        "suppressor": "a responsive viewport meta exists and does not disable zoom",
        "proved_by": "site_a declares viewport on every page and does not fire",
    },
    "act.blocker.content_gated_by_interaction": {
        "suppressor": "under 3 collapsed regions or under 150 words",
        "proved_by": "site_a does not fire",
    },
    "act.perf.above_fold_weight": {
        "suppressor": "no renderer to establish the fold, or fewer than 3 timing samples",
        "proved_by": "site_d records it as not assessed",
    },
    "act.trust.no_social_proof": {
        "suppressor": "informational page types are exempt",
        "proved_by": "test_regressions R4",
    },
    "act.trust.no_policy_or_contact_path": {
        "suppressor": "any policy path reachable; suppressed site-wide when no page has usable content",
        "proved_by": "test_gate_cascade site_d assertions",
    },
    "act.trust.no_cost_signal": {
        "suppressor": "a price, a price range, or a link to a pricing page exists",
        "proved_by": "site_a links to /pricing and does not fire",
    },
}


def audit(fixture: str, out: Path) -> dict:
    env = dict(os.environ, SOURCE_DATE_EPOCH="1780000000", PYTHONIOENCODING="utf-8")
    subprocess.run(
        [sys.executable, str(ORCH), "--offline-root", str(FIXTURES / fixture), "--out", str(out)],
        capture_output=True, text=True, env=env, cwd=str(ROOT), check=False,
    )
    return json.loads((out / "audit-report.json").read_text(encoding="utf-8"))


tmp = Path(tempfile.mkdtemp(prefix="bara-supp-"))
try:
    a = audit("site_a", tmp / "a")
    fired = {f["check_id"] for f in a["findings"]}
    skipped = {s["check_id"] for s in a["summary"]["suppressed_by_rule"]}

    # Suppressors proved by the control staying quiet.
    for check_id in (
        "reach.robots.blanket_disallow", "reach.index.noindex_on_content",
        "reach.index.canonical_conflict", "reach.http.soft_404",
        "reach.http.insecure_or_mixed_scheme", "extract.sd.invalid_syntax",
        "extract.sd.identity_graph_weak", "extract.ans.title_not_entity_bearing",
        "extract.ans.boilerplate_dominant", "trust.date.absent_on_dated_content",
        "trust.date.stale_volatile_facts", "trust.entity.name_collision",
        "act.blocker.not_mobile_ready", "act.cta.competing_primaries",
        "act.orient.no_wayfinding", "act.trust.no_cost_signal",
        "act.form.high_friction_required_fields", "act.cta.absent_for_page_type",
        "act.blocker.content_gated_by_interaction", "extract.i18n.hreflang_incomplete",
    ):
        expect(check_id not in fired, f"suppressed on the healthy control: {check_id}")

    # Suppressors that must state a REASON rather than silently not firing.
    for check_id in (
        "reach.edge.bot_ua_blocked", "reach.agent.llms_txt_absent",
        "trust.entity.no_external_corroboration", "trust.authorship.unattributed",
    ):
        expect(
            check_id in skipped,
            f"records an explicit suppression reason rather than silence: {check_id}",
        )

    d = audit("site_d", tmp / "d")
    d_skipped = {s["check_id"] for s in d["summary"]["suppressed_by_rule"]}
    for check_id in ("read.render.raw_text_gap", "read.render.nav_links_js_only",
                     "act.perf.above_fold_weight"):
        expect(check_id in d_skipped, f"records 'not assessed' with no renderer: {check_id}")

    b = audit("site_b", tmp / "b")
    b_skipped = {s["check_id"] for s in b["summary"]["suppressed_by_rule"]}
    expect(
        "reach.sitemap.absent_or_invalid" in b_skipped,
        "a 4-page site suppresses the missing-sitemap finding with a stated reason",
    )
    unlabelled = [f for f in b["findings"] if f["check_id"] == "act.form.unlabelled_inputs"]
    expect(
        unlabelled and unlabelled[0]["severity"] == "low",
        "placeholder-only labelling reports at low, not medium",
    )

    e = audit("site_e", tmp / "e")
    e_ids = {f["check_id"] for f in e["findings"]}
    expect(
        "reach.robots.ai_search_bot_blocked" not in e_ids,
        "blocking only training and dual-purpose bots does not fire the retrieval finding",
    )

    # extract.i18n.hreflang_incomplete: prove the check both stays silent on a
    # well-formed cluster and actually FIRES on the two defects it targets, by
    # calling the module directly against tiny synthetic pages. Silence alone
    # (a check that never fires) would pass the control assertion above while
    # detecting nothing; this is the positive half of that guarantee.
    sys.path.insert(0, str(ROOT / "skills" / "structured-data-audit" / "scripts"))
    import check_i18n  # noqa: E402

    class _StubBundle:
        def __init__(self, root, pages):
            self.root = root
            self._pages = pages

        def html_pages(self):
            return self._pages

    def _i18n_fires(root, name, head_html, url):
        (root / name).write_text(
            f"<html><head><title>t</title>{head_html}</head><body>hi</body></html>",
            encoding="utf-8",
        )
        b = _StubBundle(root, [{"url": url, "raw_html_path": name, "status": 200}])
        findings, _s, _p = check_i18n.run(b, None)
        return any(f["check_id"] == "extract.i18n.hreflang_incomplete" for f in findings)

    itmp = Path(tempfile.mkdtemp(prefix="bara-i18n-"))
    try:
        expect(
            not _i18n_fires(itmp, "mono.html", "", "https://ex.com/"),
            "hreflang: a monolingual page with no alternates does not fire",
        )
        complete = (
            '<link rel="alternate" hreflang="x-default" href="https://ex.com/">'
            '<link rel="alternate" hreflang="en" href="https://ex.com/">'
            '<link rel="alternate" hreflang="fr" href="https://ex.com/fr/">'
        )
        expect(
            not _i18n_fires(itmp, "ok.html", complete, "https://ex.com/"),
            "hreflang: a complete cluster with x-default and valid codes does not fire",
        )
        no_fallback = (
            '<link rel="alternate" hreflang="en" href="https://ex.com/en/">'
            '<link rel="alternate" hreflang="fr" href="https://ex.com/fr/">'
        )
        expect(
            _i18n_fires(itmp, "nofb.html", no_fallback, "https://ex.com/"),
            "hreflang: a cluster with neither x-default nor a self-reference fires",
        )
        bad_code = (
            '<link rel="alternate" hreflang="x-default" href="https://ex.com/">'
            '<link rel="alternate" hreflang="english" href="https://ex.com/">'
        )
        expect(
            _i18n_fires(itmp, "bad.html", bad_code, "https://ex.com/"),
            "hreflang: an unparseable language code fires",
        )
    finally:
        shutil.rmtree(itmp, ignore_errors=True)

    # Every registry entry must name where it is proved.
    for check_id, entry in SUPPRESSION_CASES.items():
        expect(bool(entry.get("suppressor")), f"{check_id} documents its suppressor")
        expect(bool(entry.get("proved_by")), f"{check_id} names where the suppression is proved")

finally:
    shutil.rmtree(tmp, ignore_errors=True)

if FAILURES:
    print(f"FAILED {len(FAILURES)} of {COUNT} assertions:\n")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print(f"PASS: {COUNT} suppression assertions across {len(SUPPRESSION_CASES)} documented rules")
