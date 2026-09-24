#!/usr/bin/env python3
"""Stage trust: is it clear WHICH thing this brand is?

The handout appendix puts the problem directly: "when several different things
share a name, a system can mix them up unless there's something that clearly
distinguishes one from the others."
"""

from __future__ import annotations

import re
from collections import Counter

from bundle import action, finding, threshold

CHECKS = [
    {"id": "trust.entity.name_collision", "stage": "trust", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "trust-freshness-audit"},
    {"id": "trust.entity.nap_inconsistent", "stage": "trust", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "trust-freshness-audit"},
    {"id": "trust.authorship.unattributed", "stage": "trust", "category": "discoverability",
     "tier": "core", "default_severity": "low", "skill": "trust-freshness-audit"},
]

# Common nouns and generic words that collide with countless other entities.
COLLIDING = frozenset(
    """apex atlas anchor arbor aurora beacon bridge canvas cedar circle clarity compass core
    delta domain drift echo ember flow forge fusion grove harbor harbour haven horizon impact
    ion keystone lattice ledger lens lift loop lumen matrix meridian mint north nova oak onyx
    orbit origin pace pattern peak pillar pivot pulse quest range relay ridge river scope shift
    signal slate solstice spark sphere spring stack summit surge tempo terra thread tide torch
    trail vantage vertex vista vault wave zenith""".split()
)

ADDRESS = re.compile(
    r"\d{1,5}[A-Za-z]?\s+[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,3}\s+"
    r"(Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr|Way|Boulevard|Blvd|Court|Ct|Place|Pl)\b",
    re.I,
)
# A phone number has punctuation or a country code. A bare run of digits is a
# file size, a build stamp or a checksum: on sqlite.org this matched 202607312245
# and reported it as a telephone number.
PHONE = re.compile(
    r"(?:\+\d{1,3}[\s.\-]\s?)?(?:\(\d{2,5}\)|\d{2,5})[\s.\-]\d{3,4}[\s.\-]\d{3,4}"
    r"|\+\d{7,15}\b"
)
AUTHOR_HINT = re.compile(r"\b(by [A-Z][a-z]+ [A-Z][a-z]+|author|written by|posted by)\b")

ATTRIBUTION_TYPES = {"article"}


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def brand_name(b, profile) -> str | None:
    home = next((p for p in b.html_pages() if p["url"].rstrip("/") == b.origin.rstrip("/")), None)
    if home:
        def walk(node):
            if isinstance(node, dict):
                t = str(node.get("@type", "")).lower()
                if t in ("organization", "localbusiness", "corporation", "store", "person"):
                    name = node.get("name")
                    if isinstance(name, str):
                        return name.strip()
                for v in node.values():
                    got = walk(v)
                    if got:
                        return got
            elif isinstance(node, list):
                for item in node:
                    got = walk(item)
                    if got:
                        return got
            return None

        got = walk((home.get("markup") or {}).get("jsonld") or [])
        if got:
            return got
        title = (home.get("title") or "").strip()
        for sep in (" — ", " – ", " | ", " - "):
            if sep in title:
                return title.split(sep)[0].strip()
        if title:
            return title
    host = b.site.split(".")[0]
    return host.replace("-", " ").title() if host else None


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []
    pages = b.html_pages()
    if not pages:
        return findings, skipped, []

    name = brand_name(b, profile)
    home = next((p for p in pages if p["url"].rstrip("/") == b.origin.rstrip("/")), None)

    # ---------------------------------------------------- name collision
    if name and home:
        words = [w.lower() for w in re.findall(r"[A-Za-z]+", name)]
        risky = [w for w in words if w in COLLIDING]
        single_generic = len(words) == 1 and (risky or len(name) < 6)
        if risky or single_generic:
            text = b.observed_text(home)
            descriptor = _descriptor_near(name, text)
            schema_desc = None
            for node_desc in re.findall(r'"description"\s*:\s*"([^"]{10,200})"', str((home.get("markup") or {}).get("jsonld") or [])):
                schema_desc = node_desc
                break
            if descriptor or schema_desc:
                skipped.append({
                    "check_id": "trust.entity.name_collision",
                    "reason": (
                        f"the brand name {name!r} contains a colliding term, but a disambiguating "
                        f"descriptor appears near it: "
                        f"{(descriptor or schema_desc)[:110]!r}."
                    ),
                    "confidence_effect": "suppressed by design",
                })
            else:
                findings.append(finding(
                    check_id="trust.entity.name_collision",
                    title=f"The name {name!r} is ambiguous and nothing on the homepage distinguishes it",
                    severity="medium", confidence="likely", stage="trust",
                    category="discoverability", scope="site",
                    evidence=(
                        f"The brand name {name!r} "
                        + (f"contains the common term(s) {', '.join(risky)}, which many unrelated "
                           f"organisations, products and places also use. "
                           if risky else "is a single short generic word. ")
                        + f"Within 10 words of the name on {home['url']} there is no descriptor "
                          f"saying what kind of thing it is, and no schema description supplies one. "
                          f"A system that encounters this name elsewhere has nothing to tie it back "
                          f"to this organisation."
                    ),
                    affected_urls=[home["url"]],
                    action=action(
                        summary="Put a category descriptor next to the name, and add sameAs links.",
                        effort="low",
                        mechanism=(
                            "A descriptor beside the name gives a disambiguating anchor, so "
                            "statements about this entity can be separated from statements about "
                            "others sharing the name."
                        ),
                        source="Handout appendix, Why agreement across the web matters",
                        patch=(
                            f"<p>{name} is a __FILL_IN__:category for __FILL_IN__:audience, "
                            f"based in __FILL_IN__:location.</p>\n"
                            f'<!-- and in the Organization node: -->\n'
                            f'"description": "__FILL_IN__:one_line_category_description",\n'
                            f'"sameAs": ["__FILL_IN__:wikidata_or_wikipedia_url", "__FILL_IN__:linkedin_url"]'
                        ),
                        verification=(
                            f"Search the exact name and see whether this organisation is the first "
                            f"unambiguous result; if not, the descriptor is doing no work yet."
                        ),
                    ),
                ))

    # ------------------------------------------------------------- NAP
    addresses = Counter()
    phones = Counter()
    sources: dict[str, str] = {}
    for page in pages:
        text = b.observed_text(page)
        for m in ADDRESS.findall(text):
            pass
        for m in ADDRESS.finditer(text):
            key = re.sub(r"\s+", " ", m.group(0)).strip().lower()
            addresses[key] += 1
            sources.setdefault(key, page["url"])
        for m in PHONE.finditer(text):
            digits = _digits(m.group(0))
            if 9 <= len(digits) <= 15:
                phones[digits] += 1
                sources.setdefault(digits, page["url"])

    nap_required = threshold(profile, "nap_consistency_required", False)
    variants = []
    if len(addresses) > 1:
        variants.append(("address", list(addresses)))
    if len(phones) > 1:
        variants.append(("phone", list(phones)))

    if variants and (nap_required or len(pages) >= 4):
        findings.append(finding(
            check_id="trust.entity.nap_inconsistent",
            title="The site states more than one address or phone number for itself",
            severity="medium", confidence="likely", stage="trust",
            category="discoverability", scope="site",
            evidence="; ".join(
                f"{kind}: "
                + ", ".join(f"{v!r} (first seen on {sources.get(v, 'unknown')})" for v in vals[:4])
                for kind, vals in variants
            )
            + ". Phone numbers were compared on digits only and addresses on collapsed whitespace, "
              "so formatting differences are not counted as variants.",
            affected_urls=[b.origin + "/"],
            action=action(
                summary="Publish one canonical address and phone number, and render every mention from it.",
                effort="low",
                mechanism=(
                    "Cross-source agreement is what makes a detail believable; a site that "
                    "disagrees with itself gives a checker no version to settle on."
                ),
                source="Handout appendix, Why agreement across the web matters",
                patch=(
                    '"address": {\n'
                    '  "@type": "PostalAddress",\n'
                    '  "streetAddress": "__FILL_IN__:canonical_street",\n'
                    '  "addressLocality": "__FILL_IN__:city",\n'
                    '  "postalCode": "__FILL_IN__:postcode"\n'
                    "},\n"
                    '"telephone": "__FILL_IN__:canonical_phone"'
                ),
                verification="Grep the rendered site for phone digits; expect exactly one distinct value.",
            ),
        ))
    elif variants:
        skipped.append({
            "check_id": "trust.entity.nap_inconsistent",
            "reason": (
                f"{len(variants)} kind(s) of contact detail vary, but only {len(pages)} pages were "
                f"crawled and this archetype does not require NAP consistency; too little evidence "
                f"to call it an inconsistency."
            ),
            "confidence_effect": "suppressed by threshold",
        })

    # ------------------------------------------------------- authorship
    archetype = (profile or {}).get("archetype", "other")
    if archetype in ("e-commerce", "saas-marketing"):
        skipped.append({
            "check_id": "trust.authorship.unattributed",
            "reason": (
                f"archetype is {archetype}, where corporate rather than personal authorship is "
                f"idiomatic and an unattributed page is not a defect."
            ),
            "confidence_effect": "suppressed by design",
        })
    else:
        unattributed = []
        for page in pages:
            if b.page_type(page, profile) not in ATTRIBUTION_TYPES:
                continue
            text = b.observed_text(page)
            blob = str((page.get("markup") or {}).get("jsonld") or [])
            if AUTHOR_HINT.search(text) or '"author"' in blob:
                continue
            unattributed.append(page)
        if unattributed:
            findings.append(finding(
                check_id="trust.authorship.unattributed",
                title=f"{len(unattributed)} article(s) name nobody as the author",
                severity="low", confidence="confirmed", stage="trust",
                category="discoverability", scope="url",
                evidence=(
                    f"No schema author property and no byline text on: "
                    f"{', '.join(p['url'] for p in unattributed[:4])}."
                ),
                affected_urls=[p["url"] for p in unattributed],
                action=action(
                    summary="Attribute each article to a named person or to the organisation.",
                    effort="low",
                    mechanism=(
                        "Attribution gives a claim an accountable source, which is one of the few "
                        "signals separating a considered piece from anonymous copy."
                    ),
                    source="schema.org/Article author",
                    patch='"author": { "@type": "Person", "name": "__FILL_IN__:author_name" }',
                    verification=f"curl -s {unattributed[0]['url']} | grep -o '\"author\"[^}}]*}}'",
                ),
            ))

    return findings, skipped, []


def _descriptor_near(name: str, text: str) -> str | None:
    if not name or not text:
        return None
    idx = text.lower().find(name.lower())
    if idx < 0:
        return None
    window = text[idx: idx + len(name) + 120]
    m = re.search(
        r"\b(is|are)\s+(a|an|the)\s+([a-z][a-z\- ]{4,50})", window, re.I
    )
    return m.group(0) if m else None
