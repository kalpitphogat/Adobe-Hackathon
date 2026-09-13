#!/usr/bin/env python3
"""Gate Rule 0b, enforced inside this skill as well as in the orchestrator.

Engagement is NOT causally downstream of reach: a visitor arriving from an ad or
an email does not care whether a crawler was let in, so a robots.txt block must
never touch an engagement finding.

Engagement IS evidentially downstream of read. If a page's served HTML is an
empty application shell and no rendered DOM was captured, we never observed what
the visitor sees. A check that reasons over visible content is then not
"probably wrong", it is UNEVIDENCED. Reporting it at reduced severity would
assert something we did not observe, so it is suppressed entirely instead.

Two scopes matter, and the second is the one that is easy to get wrong:

  per page   a visible-content check is suppressed on any page we did not
             observe.
  site wide  a SITE-SCOPED check such as no_policy_or_contact_path is normally
             exempt, because it can be evidenced from other pages. On a site
             where EVERY page is an unobserved shell there are no other pages,
             so it must be suppressed too. Without this guard it fires falsely
             on every all-SPA site.

The orchestrator repeats this enforcement as a safety net. Both layers exist on
purpose: a skill run standalone must be just as honest as one run under the
orchestrator.
"""

from __future__ import annotations

# The visible-content checks. Everything here reasons about what a visitor sees.
RULE_0B_SUPPRESSIBLE = frozenset({
    "act.orient.no_value_proposition",
    "act.orient.h1_cta_mismatch",
    "act.orient.no_wayfinding",
    "act.cta.absent_for_page_type",
    "act.cta.ambiguous_primary_label",
    "act.cta.competing_primaries",
    "act.form.field_count_excessive",
    "act.form.high_friction_required_fields",
    "act.form.unlabelled_inputs",
    "act.context.no_onward_path",
    "act.context.assumes_prior_context",
    "act.blocker.content_gated_by_interaction",
    "act.trust.no_social_proof",
    "act.trust.no_cost_signal",
})

# Exempt from the per-page rule because they read raw <head> or markup, which is
# valid whether or not the body hydrated.
RULE_0B_EXEMPT = frozenset({
    "act.blocker.not_mobile_ready",
    "act.blocker.load_time_interstitial",
    "act.perf.above_fold_weight",
    "act.trust.no_policy_or_contact_path",
})


class Rule0b:
    def __init__(self, bundle) -> None:
        self.bundle = bundle
        self.unobserved = [p for p in bundle.html_pages() if not bundle.page_observed(p)]
        self.observed = [p for p in bundle.html_pages() if bundle.page_observed(p)]
        self.site_has_content = bundle.has_usable_content()

    def page_allowed(self, check_id: str, page: dict) -> bool:
        if check_id not in RULE_0B_SUPPRESSIBLE:
            return True
        return self.bundle.page_observed(page)

    def site_allowed(self, check_id: str) -> bool:
        """Site-scoped checks need at least one observed page somewhere."""
        return self.site_has_content

    def limitation(self) -> dict | None:
        """ONE consolidated entry, never one per page."""
        if not self.unobserved:
            return None
        if not self.site_has_content:
            return {
                "scope": "site",
                "reason": (
                    f"Every one of the {len(self.unobserved)} crawled pages serves an unhydrated "
                    f"application shell, and no rendered DOM was captured for any of them, so the "
                    f"page a visitor actually sees was never observed. All engagement checks are "
                    f"suppressed site-wide rather than reported at reduced confidence, because "
                    f"there is no evidence to reduce. This includes the normally site-scoped "
                    f"act.trust.no_policy_or_contact_path, which would otherwise be evidenced from "
                    f"other pages: on this site there are no other pages either. Re-run with a "
                    f"renderer available to assess engagement."
                ),
                "checks_not_run": sorted(RULE_0B_SUPPRESSIBLE | {"act.trust.no_policy_or_contact_path"}),
                "confidence_effect": "suppressed entirely; not downgraded",
            }
        return {
            "scope": ", ".join(p["url"] for p in self.unobserved[:8]),
            "reason": (
                f"{len(self.unobserved)} of {len(self.bundle.html_pages())} pages serve an "
                f"unhydrated application shell with no rendered DOM captured, so visible content "
                f"was never observed on them. Visible-content engagement checks are suppressed on "
                f"those pages. Other pages were observed and were assessed normally."
            ),
            "checks_not_run": sorted(RULE_0B_SUPPRESSIBLE),
            "confidence_effect": "suppressed entirely on the named pages; not downgraded",
        }
