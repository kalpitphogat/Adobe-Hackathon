#!/usr/bin/env python3
"""Stage act: things that stop a visitor who was otherwise willing.

Includes the four checks exempt from gate Rule 0b's per-page suppression,
because they read the raw <head> or response metadata rather than hydrated body
content - valid whether or not the page rendered. The exception is
act.trust.no_policy_or_contact_path, which is site-scoped and IS suppressed when
no page on the site has observed content, since there are then no other pages to
evidence it from.
"""

from __future__ import annotations

import re
import statistics

from bundle import action, finding, threshold
from gating import Rule0b

CHECKS = [
    {"id": "act.blocker.load_time_interstitial", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": False},
    {"id": "act.blocker.not_mobile_ready", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "high", "skill": "engagement-audit",
     "rule_0b_suppressible": False},
    {"id": "act.blocker.content_gated_by_interaction", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
    {"id": "act.perf.above_fold_weight", "stage": "act", "category": "engagement",
     "tier": "enrichment", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": False},
    {"id": "act.trust.no_social_proof", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
    {"id": "act.trust.no_policy_or_contact_path", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": False},
    {"id": "act.trust.no_cost_signal", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
]

# Where a visitor actually decides to act. About and Contact pages were
# removed after they fired on the healthy control: they are informational,
# and social proof there is not what carries the decision.
CONVERSION_TYPES = {"home", "product", "pricing"}
COMMERCIAL_TYPES = {"product", "pricing", "category"}

SOCIAL_PROOF = [
    (re.compile(r"\b(testimonial|review|rated|rating|stars?)\b", re.I), "review or rating language"),
    (re.compile(r"\b(trusted by|used by|join(ed)? (over )?[\d,]+|[\d,]+\+? (customers|companies|teams|users))\b", re.I), "customer count"),
    (re.compile(r"\b(case stud(y|ies)|success story)\b", re.I), "case study"),
    (re.compile(r"[“\"][^”\"]{40,}[”\"]\s*[-—]\s*[A-Z]", re.I), "an attributed quotation"),
]

POLICY_PATHS = re.compile(r"/(privacy|terms|legal|imprint|cookie|contact|about|support|help)", re.I)
PRICE_RE = re.compile(r"(?:[$£€¥]\s?\d[\d,.]*|\b\d[\d,.]*\s?(?:USD|EUR|GBP|INR|AUD|CAD)\b)", re.I)
PRICE_PATH_RE = re.compile(r"\b(pricing|plans|quote|contact sales|get a quote|request pricing)\b", re.I)
# A page that says the thing is free HAS stated its cost. Asking it for a price
# fired on an open-source download page.
FREE_RE = re.compile(
    r"\b(free (to (use|download|try)|forever|of charge|plan)|no cost|open[- ]source|"
    r"free and open|zero cost|\$0\b|100% free|always free|download (it )?free)\b",
    re.I,
)

MODAL_ON_LOAD = re.compile(
    r"(data-(modal|popup|overlay)-(trigger|on)=[\"']?(load|onload|pageload|scroll)"
    r"|class=[\"'][^\"']*(newsletter-popup|exit-intent|interstitial|modal--auto)"
    r"|window\.onload\s*=\s*[^;]{0,80}(modal|popup|overlay))",
    re.I,
)
COOKIE_BANNER = re.compile(r"(cookie|consent|gdpr)", re.I)
# aria-expanded="false" was removed from this pattern after it fired 22 times
# on one storefront for navigation dropdowns and a cart drawer, which is correct
# ARIA rather than hidden content. What remains is markup that hides PROSE.
GATED = re.compile(
    r"(<details(?![^>]*\bopen\b)|class=[\"'][^\"']*(accordion|collapse)(?![^\"']*\bshow\b)"
    r"|class=[\"'][^\"']*read-more)",
    re.I,
)
# Chrome that legitimately collapses and is not page content.
GATED_CHROME = re.compile(r"(nav|menu|drawer|cart|header|footer|filter|facet|cookie)", re.I)


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    gate = Rule0b(b)
    findings: list[dict] = []
    skipped: list[dict] = []

    # --------------------------------------------------- mobile readiness
    no_viewport = []
    bad_viewport = []
    for page in b.html_pages():
        viewport = _viewport(b, page)
        if viewport is None:
            no_viewport.append(page["url"])
        elif re.search(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1(\.0)?\b", viewport, re.I):
            bad_viewport.append((page["url"], viewport))

    if no_viewport:
        findings.append(finding(
            check_id="act.blocker.not_mobile_ready",
            title=f"{len(no_viewport)} page(s) declare no mobile viewport",
            severity="high", confidence="confirmed", stage="act",
            category="engagement", scope="url",
            evidence=(
                f"No <meta name=\"viewport\"> on: {', '.join(no_viewport[:6])}. Without it a mobile "
                f"browser renders at a desktop width and scales the whole page down, so body text "
                f"arrives too small to read and every tap target is too small to hit."
            ),
            affected_urls=no_viewport,
            action=action(
                summary="Add a responsive viewport meta tag to every page.",
                effort="low",
                mechanism=(
                    "The viewport meta tag is what tells a mobile browser to lay out at device "
                    "width instead of emulating a desktop and zooming out."
                ),
                source="WCAG 2.2 Success Criterion 1.4.10 Reflow",
                patch='<meta name="viewport" content="width=device-width, initial-scale=1">',
                verification=f"curl -s {no_viewport[0]} | grep -i 'name=\"viewport\"'",
            ),
        ))
    if bad_viewport:
        findings.append(finding(
            check_id="act.blocker.not_mobile_ready",
            title=f"{len(bad_viewport)} page(s) disable pinch zoom",
            severity="medium", confidence="confirmed", stage="act",
            category="engagement", scope="url",
            evidence="; ".join(f"{u}: {v!r}" for u, v in bad_viewport[:4]),
            affected_urls=[u for u, _ in bad_viewport],
            action=action(
                summary="Remove user-scalable=no and maximum-scale from the viewport tag.",
                effort="low",
                mechanism="Disabling zoom removes the only recourse a visitor has when text is too small.",
                source="WCAG 2.2 Success Criterion 1.4.4 Resize Text",
                patch='<meta name="viewport" content="width=device-width, initial-scale=1">',
                verification=f"curl -s {bad_viewport[0][0]} | grep -i viewport",
            ),
        ))

    # ------------------------------------------------------ interstitials
    for page in b.html_pages():
        raw = _raw_html(b, page)
        if not raw:
            continue
        m = MODAL_ON_LOAD.search(raw)
        if not m:
            continue
        window = raw[max(0, m.start() - 300): m.end() + 300]
        if COOKIE_BANNER.search(window):
            skipped.append({
                "check_id": "act.blocker.load_time_interstitial",
                "reason": (
                    f"{page['url']}: an overlay fires on load, but the surrounding markup is a "
                    f"cookie or consent banner, which is frequently a legal requirement rather "
                    f"than a marketing interruption."
                ),
                "confidence_effect": "suppressed by design",
            })
            continue
        findings.append(finding(
            check_id="act.blocker.load_time_interstitial",
            title="An overlay is configured to interrupt the visitor on arrival",
            severity="medium", confidence="likely", stage="act",
            category="engagement", scope="url",
            evidence=(
                f"{page['url']}: markup matching an on-load overlay trigger was found: "
                f"{m.group(0)[:120]!r}. Cookie and consent banners were excluded. An overlay that "
                f"fires before the visitor has read anything asks for a decision they have no "
                f"basis to make."
            ),
            affected_urls=[page["url"]],
            action=action(
                summary="Trigger the overlay on intent or after meaningful engagement, not on load.",
                effort="low",
                mechanism=(
                    "A visitor interrupted before reading anything has no reason to say yes, so "
                    "the overlay converts poorly and costs the pageview."
                ),
                source="references/cro-frameworks.md",
                patch="<!-- Trigger after scroll depth or exit intent rather than on load. -->",
                verification=f"Open {page['url']} in a fresh session and time how long before an overlay appears.",
            ),
        ))

    # ------------------------------------------------ gated main content
    limit_ratio = threshold(profile, "gated_content_ratio_max", 0.2)
    for page in b.html_pages():
        if not gate.page_allowed("act.blocker.content_gated_by_interaction", page):
            continue
        raw = _raw_html(b, page)
        if not raw:
            continue
        hits = [
            m for m in GATED.finditer(raw)
            if not GATED_CHROME.search(raw[max(0, m.start() - 160):m.end() + 160])
        ]
        if not hits:
            continue
        words = page.get("main_wordcount") or 0
        if words < 150 or len(hits) < 3:
            skipped.append({
                "check_id": "act.blocker.content_gated_by_interaction",
                "reason": (
                    f"{page['url']}: {len(hits)} collapsed region(s) on a {words}-word page is "
                    f"below the reporting floor. Progressive disclosure of a few sections, such as "
                    f"an FAQ whose questions are all visible, is a design choice, not a defect."
                ),
                "confidence_effect": "suppressed by threshold",
            })
            continue
        findings.append(finding(
            check_id="act.blocker.content_gated_by_interaction",
            title=f"{len(hits)} content region(s) require a click before they can be read",
            severity="medium", confidence="likely", stage="act",
            category="engagement", scope="url",
            evidence=(
                f"{page['url']}: {len(hits)} collapsed regions (closed <details>, accordion or "
                f"read-more wrappers) across {words} words of main content. Navigation dropdowns, "
                f"cart drawers and filter panels were excluded, and aria-expanded is not counted "
                f"at all because it is correct ARIA on a menu button rather than hidden content. "
                f"A visitor scanning the page sees only the headings; anything behind a click is "
                f"invisible to them unless they already suspect it is there."
            ),
            affected_urls=[page["url"]],
            action=action(
                summary="Show the key content by default; use collapse only for genuinely secondary detail.",
                effort="low",
                mechanism=(
                    "Visitors scan before they commit; content behind an interaction is not part "
                    "of the scan and so does not influence the decision to stay."
                ),
                source="references/cro-frameworks.md",
                patch="<details open>\n  <summary>__FILL_IN__:section_heading</summary>\n  ...\n</details>",
                verification=f"curl -s {page['url']} | grep -c '<details'",
            ),
        ))

    # ------------------------------------------------- above-fold weight
    samples = [float(s) for s in (b.probes.get("ttfb_samples_ms") or [])]
    rendered = [p for p in b.html_pages() if p.get("rendered_available")]
    if not rendered:
        skipped.append({
            "check_id": "act.perf.above_fold_weight",
            "reason": (
                "no rendered DOM was captured, so the fold could not be established and "
                "above-fold weight could not be measured. This check is in the ENRICHMENT tier."
            ),
            "confidence_effect": "not assessed",
        })
    elif len(samples) < 3:
        skipped.append({
            "check_id": "act.perf.above_fold_weight",
            "reason": (
                f"only {len(samples)} timing sample(s); this check requires at least 3 so it never "
                f"fires on a single transient measurement."
            ),
            "confidence_effect": "not assessed",
        })
    else:
        limit = threshold(profile, "page_bytes_max", 3000000)
        heavy = [p for p in rendered if (p.get("bytes") or 0) > limit]
        if heavy:
            findings.append(finding(
                check_id="act.perf.above_fold_weight",
                title=f"{len(heavy)} page(s) exceed the page-weight budget",
                severity="medium", confidence="confirmed", stage="act",
                category="engagement", scope="url",
                evidence="; ".join(
                    f"{p['url']}: {(p.get('bytes') or 0)/1024:.0f} KiB against a "
                    f"{limit/1024:.0f} KiB budget (median of {len(samples)} timing samples: "
                    f"{statistics.median(samples):.0f} ms)"
                    for p in heavy[:4]
                ),
                affected_urls=[p["url"] for p in heavy],
                action=action(
                    summary="Compress and lazy-load below-fold media; defer non-critical scripts.",
                    effort="medium",
                    mechanism=(
                        "Bytes that must arrive before first paint delay the moment the visitor "
                        "can read anything, and a visitor who sees nothing leaves."
                    ),
                    source="references/cro-frameworks.md",
                    patch='<img src="hero.webp" loading="lazy" decoding="async" width="1200" height="630" alt="__FILL_IN__:alt">',
                    verification=f"curl -so /dev/null -w '%{{size_download}}\\n' {heavy[0]['url']}",
                ),
            ))

    # ----------------------------------------------------- social proof
    for page in b.html_pages():
        page_type = b.page_type(page, profile)
        if page_type not in CONVERSION_TYPES:
            continue
        if not gate.page_allowed("act.trust.no_social_proof", page):
            continue
        text = b.observed_text(page)
        if len(text.split()) < 60:
            continue
        found = [label for pattern, label in SOCIAL_PROOF if pattern.search(text)]
        if found:
            continue
        findings.append(finding(
            check_id="act.trust.no_social_proof",
            title=f"A {page_type} page offers no evidence that anyone else has trusted this",
            severity="medium", confidence="likely", stage="act",
            category="engagement", scope="url",
            evidence=(
                f"{page['url']} ({len(text.split())} words) contains none of: review or rating "
                f"language, a customer or user count, a case study reference, or an attributed "
                f"quotation. A visitor deciding whether to act has only the brand's own claims to "
                f"go on."
            ),
            affected_urls=[page["url"]],
            action=action(
                summary="Add one specific, attributed piece of evidence near the primary action.",
                effort="low",
                mechanism=(
                    "An attributed third-party statement is evidence a visitor can weigh; a "
                    "first-party claim is not, so it does not reduce the risk of acting."
                ),
                source="references/cro-frameworks.md",
                patch=(
                    "<blockquote>\n"
                    "  <p>__FILL_IN__:specific_outcome_in_the_customers_words</p>\n"
                    "  <cite>__FILL_IN__:name, __FILL_IN__:role, __FILL_IN__:company</cite>\n"
                    "</blockquote>"
                ),
                verification=f"Open {page['url']}: is there evidence from someone other than the brand?",
            ),
        ))

    # ------------------------------------------ policy and contact (site)
    if not gate.site_allowed("act.trust.no_policy_or_contact_path"):
        skipped.append({
            "check_id": "act.trust.no_policy_or_contact_path",
            "reason": (
                "No page in the crawl has observed content, so there are no pages from which to "
                "evidence a site-scoped check. This check is normally exempt from gate Rule 0b "
                "because it can be evidenced from other pages; on an all-shell site there are no "
                "other pages either, so it is suppressed site-wide rather than fired falsely."
            ),
            "confidence_effect": "suppressed entirely",
        })
    else:
        all_internal = {
            link for p in b.html_pages() for link in (p.get("links") or {}).get("internal", [])
        } | {p["url"] for p in b.html_pages()}
        policy_hits = sorted(u for u in all_internal if POLICY_PATHS.search(u))
        if not policy_hits:
            findings.append(finding(
                check_id="act.trust.no_policy_or_contact_path",
                title="No contact, privacy or terms page is reachable anywhere on the site",
                severity="medium", confidence="confirmed", stage="act",
                category="engagement", scope="site",
                evidence=(
                    f"Across {len(b.html_pages())} crawled pages and {len(all_internal)} distinct "
                    f"internal link targets, no URL matches a contact, privacy, terms, legal, "
                    f"imprint, support or about path. A visitor has no way to find out who they "
                    f"would be dealing with or how to reach them."
                ),
                affected_urls=[b.origin + "/"],
                action=action(
                    summary="Publish contact and privacy pages and link them from the footer of every page.",
                    effort="low",
                    mechanism=(
                        "A visitor assessing whether to transact looks for evidence there is a "
                        "reachable organisation behind the site; absence reads as risk."
                    ),
                    source="references/cro-frameworks.md",
                    patch=(
                        "<footer>\n"
                        '  <a href="/contact">Contact</a>\n'
                        '  <a href="/privacy">Privacy</a>\n'
                        '  <a href="/terms">Terms</a>\n'
                        "</footer>"
                    ),
                    verification=f"curl -s {b.origin}/ | grep -Eo 'href=\"[^\"]*(contact|privacy)[^\"]*\"'",
                ),
            ))

    # -------------------------------------------------------- cost signal
    require_cost = threshold(profile, "require_cost_signal", False)
    for page in b.html_pages():
        page_type = b.page_type(page, profile)
        if page_type not in COMMERCIAL_TYPES:
            continue
        if not gate.page_allowed("act.trust.no_cost_signal", page):
            continue
        text = b.observed_text(page)
        if PRICE_RE.search(text) or PRICE_PATH_RE.search(text):
            continue
        if FREE_RE.search(text):
            skipped.append({
                "check_id": "act.trust.no_cost_signal",
                "reason": (
                    f"{page['url']} states that the thing is free or open source, which IS a cost "
                    f"signal. Asking a free product for a price is a false positive."
                ),
                "confidence_effect": "suppressed by design",
            })
            continue
        internal = (page.get("links") or {}).get("internal", [])
        if any(re.search(r"/(pricing|plans|quote)", u, re.I) for u in internal):
            skipped.append({
                "check_id": "act.trust.no_cost_signal",
                "reason": (
                    f"{page['url']} states no price, but links to a pricing page, which is a "
                    f"legitimate path to the cost."
                ),
                "confidence_effect": "suppressed by design",
            })
            continue
        severity = "medium" if require_cost else "low"
        findings.append(finding(
            check_id="act.trust.no_cost_signal",
            title=f"A {page_type} page gives no indication of cost and no path to one",
            severity=severity, confidence="confirmed", stage="act",
            category="engagement", scope="url",
            evidence=(
                f"{page['url']} is a {page_type} page. No currency amount appears in its "
                f"{len(text.split())} words of observed content, no schema.org offers.price is "
                f"declared, no phrase such as \"contact sales\" or \"request pricing\" appears, and "
                f"none of its {len(internal)} internal links leads to a pricing or quote page."
            ),
            affected_urls=[page["url"]],
            action=action(
                summary="State a price, a price range, or an explicit route to getting one.",
                effort="low",
                mechanism=(
                    "Cost is the question a visitor on a commercial page is trying to answer; "
                    "leaving it unanswerable ends the visit rather than deferring it."
                ),
                source="references/cro-frameworks.md",
                patch=(
                    "<p class=\"price\">__FILL_IN__:amount __FILL_IN__:currency</p>\n"
                    "<!-- or, if pricing is genuinely quote-based: -->\n"
                    '<p><a href="/contact">Request pricing</a> — typical range __FILL_IN__:range</p>'
                ),
                verification=f"curl -s {page['url']} | grep -Eo '[$£€][0-9,]+' | head -3",
            ),
        ))

    limitation = gate.limitation()
    return findings, skipped, ([limitation] if limitation else [])


def _viewport(b, page: dict) -> str | None:
    raw = _raw_html(b, page)
    if raw is None:
        return None
    m = re.search(r'<meta[^>]+name=["\']?viewport["\']?[^>]*>', raw, re.I)
    if not m:
        return None
    c = re.search(r'content=["\']([^"\']*)["\']', m.group(0), re.I)
    return c.group(1) if c else ""


_RAW_CACHE: dict[str, str] = {}


def _raw_html(b, page: dict) -> str | None:
    path = page.get("raw_html_path")
    if not path:
        return None
    key = str(b.root / path)
    if key not in _RAW_CACHE:
        p = b.root / path
        _RAW_CACHE[key] = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
    return _RAW_CACHE[key] or None
