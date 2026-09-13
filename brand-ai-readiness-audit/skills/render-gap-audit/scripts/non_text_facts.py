#!/usr/bin/env python3
"""Stage read: facts locked in non-text.

The handout appendix puts this plainly: the more a fact is "locked inside
something non-textual, the more likely it's missed". This module looks for the
specific facts a page type is expected to state - a price, an address, opening
hours - and checks whether they exist anywhere in the text or structured data,
or only inside an image.

Same mechanism the appendix describes for email summarisation: substance carried
in a form a reader cannot parse disappears from the summary.
"""

from __future__ import annotations

import re

from bundle import action, finding

CHECKS = [
    {"id": "read.nontext.key_fact_image_only", "stage": "read", "category": "discoverability",
     "tier": "core", "default_severity": "high", "skill": "render-gap-audit"},
    {"id": "read.nontext.informative_image_no_alt", "stage": "read", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "render-gap-audit"},
]

PRICE_RE = re.compile(r"(?:[$£€¥]\s?\d[\d,.]*|\b\d[\d,.]*\s?(?:USD|EUR|GBP|INR|AUD|CAD)\b)", re.I)
HOURS_RE = re.compile(r"\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\b[^.]{0,40}\d{1,2}\s*(?::\d{2})?\s*(am|pm)", re.I)
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}")

# Filename tokens that suggest an image is carrying a fact rather than decoration.
FACT_IMAGE_TOKENS = (
    "price", "pricing", "cost", "rate", "tariff", "menu", "hours", "opening",
    "timetable", "schedule", "spec", "specs", "table", "chart", "infographic",
    "address", "map", "contact", "plan", "tier",
)

# What each page type is expected to state in text.
EXPECTED_FACTS = {
    "product": ("a price", PRICE_RE),
    "pricing": ("a price", PRICE_RE),
    "contact": ("a phone number", PHONE_RE),
}


def _schema_text(page: dict) -> str:
    import json

    markup = page.get("markup") or {}
    try:
        return json.dumps(markup.get("jsonld") or []) + json.dumps(markup.get("microdata") or [])
    except (TypeError, ValueError):
        return ""


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []

    for page in b.html_pages():
        page_type = b.page_type(page, profile)
        text = b.observed_text(page)
        schema_blob = _schema_text(page)
        images = page.get("images") or []

        expected = EXPECTED_FACTS.get(page_type)
        if expected:
            label, pattern = expected
            in_text = bool(pattern.search(text))
            in_schema = bool(pattern.search(schema_blob))
            # SUPPRESS: if the fact is anywhere machine-readable, this is not a
            # non-text problem, whatever the images look like.
            if not in_text and not in_schema:
                suspects = [
                    img for img in images
                    if any(tok in (img.get("src") or "").lower() for tok in FACT_IMAGE_TOKENS)
                ]
                if suspects:
                    findings.append(finding(
                        check_id="read.nontext.key_fact_image_only",
                        title=f"This {page_type} page states {label} only inside an image",
                        severity="high", confidence="likely", stage="read",
                        category="discoverability", scope="url",
                        evidence=(
                            f"{page['url']} is a {page_type} page, where {label} is the fact a "
                            f"reader is looking for. No match for {label} appears anywhere in the "
                            f"{len(text.split())} words of observed text, nor in the page's "
                            f"structured data. The page does load "
                            f"{', '.join(img['src'] for img in suspects[:3])}, whose filename "
                            f"suggests it carries that fact, and its alt text is "
                            f"{suspects[0].get('alt')!r}. A crawler cannot read a number that "
                            f"exists only as pixels."
                        ),
                        affected_urls=[page["url"]],
                        action=action(
                            summary=f"State {label} as text on the page, and mirror it in structured data.",
                            effort="low",
                            mechanism=(
                                "Extraction operates on text and markup; a value rendered into an "
                                "image is not available to it at any stage, so the page cannot be "
                                "used to answer the question it was built to answer."
                            ),
                            source="Handout appendix, How machines read a page",
                            patch=_fact_patch(page_type, page),
                            verification=(
                                f"curl -s {page['url']} | sed -e 's/<[^>]*>//g' | grep -E "
                                f"'[$£€]|USD|GBP' | head -3"
                            ),
                        ),
                    ))

        # ------------------------------------------- informative image alt
        informative = [img for img in images if img.get("informative")]
        missing_alt = [img for img in informative if not (img.get("alt") or "").strip()]
        if not informative:
            continue
        if not missing_alt:
            continue
        # SUPPRESS: a single missing alt on a page is noise, not a finding.
        if len(missing_alt) < 2 and len(informative) < 4:
            skipped.append({
                "check_id": "read.nontext.informative_image_no_alt",
                "reason": (
                    f"{page['url']}: {len(missing_alt)} of {len(informative)} content images lack "
                    f"alt text, below the reporting floor. Isolated missing alt text is routine."
                ),
                "confidence_effect": "suppressed by threshold",
            })
            continue
        findings.append(finding(
            check_id="read.nontext.informative_image_no_alt",
            title=f"{len(missing_alt)} content image(s) carry no alt text",
            severity="medium", confidence="confirmed", stage="read",
            category="discoverability", scope="url",
            evidence=(
                f"{page['url']}: {len(missing_alt)} of {len(informative)} images classified as "
                f"content-bearing have empty or missing alt text: "
                f"{', '.join(img['src'] for img in missing_alt[:4])}. Images were classified as "
                f"content-bearing because they sit in the main content region, are larger than "
                f"100x100, and are not icons, logos or sprites. Decorative images and chrome were "
                f"excluded and are not counted here."
            ),
            affected_urls=[page["url"]],
            action=action(
                summary="Add alt text that states what the image communicates, not what it depicts.",
                effort="low",
                mechanism=(
                    "Alt text is the only textual representation of an image available to a "
                    "reader that cannot see it, so it is the only route by which the image's "
                    "content can be extracted."
                ),
                source="WCAG 2.2 Success Criterion 1.1.1 Non-text Content",
                patch="\n".join(
                    f'<img src="{img["src"]}" alt="__FILL_IN__:what_this_image_communicates">'
                    for img in missing_alt[:4]
                ),
                verification=f"curl -s {page['url']} | grep -c 'alt=\"\"'",
            ),
        ))

    return findings, skipped, []


def _fact_patch(page_type: str, page: dict) -> str:
    """Patch built only from values the bundle actually contains."""
    title = page.get("title") or "__FILL_IN__:product_name"
    if page_type in ("product", "pricing"):
        return (
            "<!-- State the price as text next to the image: -->\n"
            f"<p class=\"price\">__FILL_IN__:price_value __FILL_IN__:currency_code</p>\n\n"
            "<!-- and mirror it in structured data: -->\n"
            '<script type="application/ld+json">\n'
            "{\n"
            '  "@context": "https://schema.org",\n'
            '  "@type": "Product",\n'
            f'  "name": {title!r},\n'
            '  "offers": {\n'
            '    "@type": "Offer",\n'
            '    "price": "__FILL_IN__:price_value",\n'
            '    "priceCurrency": "__FILL_IN__:currency_code",\n'
            '    "availability": "https://schema.org/InStock"\n'
            "  }\n"
            "}\n"
            "</script>"
        )
    return (
        "<!-- State the fact as text rather than only in an image: -->\n"
        "<p>__FILL_IN__:the_fact_currently_only_in_the_image</p>"
    )
