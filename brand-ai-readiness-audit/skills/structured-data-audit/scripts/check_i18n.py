#!/usr/bin/env python3
"""Stage extract: are the page's language alternates (hreflang) internally complete?

This check only reasons about pages that ALREADY declare hreflang alternates. A
monolingual page with no hreflang is correct and is never a finding here — firing
on every English-only page would be the exact false positive the rest of this
marketplace is built to avoid. When alternates ARE declared, the two mistakes that
actually break multi-region discoverability are:

  * no self-referential and no x-default entry — search and assistant systems then
    cannot tell which of the declared variants is canonical for a locale;
  * a malformed language code — an alternate an engine cannot parse is ignored.

Both are read from the served HTML, which is where hreflang lives.
"""

from __future__ import annotations

import re

from bundle import action, finding

CHECKS = [
    {"id": "extract.i18n.hreflang_incomplete", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "structured-data-audit"},
]

_ALT = re.compile(r"<link\b[^>]*\brel\s*=\s*[\"']alternate[\"'][^>]*>", re.I)
_HREFLANG = re.compile(r"\bhreflang\s*=\s*[\"']([^\"']+)[\"']", re.I)
_HREF = re.compile(r"\bhref\s*=\s*[\"']([^\"']+)[\"']", re.I)
# A permissive BCP-47-ish shape: primary subtag + optional region/script subtags.
_LANG_OK = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")


def _raw_html(b, page: dict) -> str:
    rel = page.get("raw_html_path")
    if not rel:
        return ""
    try:
        return (b.root / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _norm(url: str) -> str:
    return (url or "").split("#")[0].split("?")[0].rstrip("/").lower()


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []

    incomplete: list[tuple[str, str]] = []
    for page in b.html_pages():
        html = _raw_html(b, page)
        if not html:
            continue
        alts = _ALT.findall(html)
        pairs = []
        for tag in alts:
            hl = _HREFLANG.search(tag)
            hf = _HREF.search(tag)
            if hl:
                pairs.append((hl.group(1).strip(), (hf.group(1).strip() if hf else "")))
        if not pairs:
            continue  # no hreflang declared: correct for a monolingual page, not a finding

        langs = [p[0] for p in pairs]
        has_xdefault = any(l.lower() == "x-default" for l in langs)
        this = _norm(page["url"])
        has_self = any(_norm(href) == this for _, href in pairs if href)
        bad_codes = sorted({l for l in langs if l.lower() != "x-default" and not _LANG_OK.match(l)})

        problems = []
        if not has_xdefault and not has_self:
            problems.append(
                "the set declares neither an x-default nor a self-referential alternate, so no "
                "variant is marked as the fallback/canonical for its locale"
            )
        if bad_codes:
            problems.append(f"invalid language code(s): {', '.join(bad_codes)}")
        if problems:
            incomplete.append((page["url"], "; ".join(problems)))

    if incomplete:
        urls = sorted({u for u, _ in incomplete})
        findings.append(finding(
            check_id="extract.i18n.hreflang_incomplete",
            title=f"hreflang alternates are incomplete on {len(urls)} page(s)",
            severity="medium", confidence="confirmed", stage="extract",
            category="discoverability", scope="site" if len(urls) > 1 else "url",
            evidence=(
                f"{len(urls)} page(s) declare hreflang alternates that are internally incomplete: "
                + "; ".join(f"{u} — {why}" for u, why in incomplete[:3])
                + ". Engines and assistants that resolve the right regional/language variant rely "
                "on a complete alternate set with an x-default (or a self-reference) and valid "
                "codes; an incomplete set means the wrong variant, or none, is surfaced per locale."
            ),
            affected_urls=urls,
            action=action(
                summary="Complete each hreflang cluster: add x-default and a self-referential alternate, and fix invalid codes.",
                effort="medium",
                mechanism=(
                    "hreflang is a reciprocal, self-contained map of a page's locale variants; if it "
                    "lacks a fallback or names an unparseable locale, the resolver cannot pick the "
                    "correct variant and may drop the page from a locale's results."
                ),
                source="Google Search Central: localized versions; RFC 5646 (BCP 47)",
                patch=(
                    '<link rel="alternate" hreflang="x-default" href="https://example.com/">\n'
                    '<link rel="alternate" hreflang="en" href="https://example.com/">\n'
                    '<link rel="alternate" hreflang="en-GB" href="https://example.com/en-gb/">'
                ),
                verification="Confirm every alternate cluster includes x-default (or a self-reference) and only valid BCP-47 codes.",
            ),
        ))

    return findings, skipped, []
