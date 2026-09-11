#!/usr/bin/env python3
"""Stage extract: does the markup agree with the page, and does the site have an identity?

Markup that contradicts the visible page is worse than no markup, because it
actively misinforms a consumer that trusts it. That is why the contradiction
check is high severity while merely-absent markup on a small page is suppressed
entirely.
"""

from __future__ import annotations

import re

from bundle import action, finding
from extract_markup import get_path, nodes, spec, types_of

CHECKS = [
    {"id": "extract.sd.contradicts_visible_content", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "high", "skill": "structured-data-audit"},
    {"id": "extract.sd.identity_graph_weak", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "structured-data-audit"},
]

IDENTITY_TYPES = {"organization", "localbusiness", "person", "corporation", "store", "ngo", "website"}
MONEY_RE = re.compile(r"[0-9][0-9,]*(?:\.[0-9]{1,2})?")


def _norm_money(value) -> str | None:
    if value is None:
        return None
    m = MONEY_RE.search(str(value).replace(" ", ""))
    if not m:
        return None
    raw = m.group(0).replace(",", "")
    try:
        return f"{float(raw):.2f}"
    except ValueError:
        return None


def _norm_text(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _norm_date(value) -> str | None:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(value or ""))
    return m.group(0) if m else None


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []
    conf = spec()

    # ------------------------------------------- schema vs visible content
    contradictions: list[tuple[str, str, str, str]] = []
    for page in b.html_pages():
        text = b.observed_text(page)
        if not text:
            continue
        for node in nodes(page):
            price = get_path(node, "offers.price")
            if price is not None:
                declared = _norm_money(price)
                on_page = {_norm_money(m) for m in re.findall(r"[$£€¥]\s?[\d,]+(?:\.\d{1,2})?", text)}
                on_page |= {
                    _norm_money(m) for m in re.findall(r"\b[\d,]+(?:\.\d{1,2})?\s?(?:USD|EUR|GBP|INR)\b", text)
                }
                on_page.discard(None)
                # SUPPRESS: only a real disagreement counts. If the page shows no
                # price at all we cannot compare, and formatting is normalised.
                if declared and on_page and declared not in on_page:
                    contradictions.append((
                        page["url"], "offers.price", declared,
                        f"page shows {', '.join(sorted(x for x in on_page if x)[:3])}",
                    ))

            published = get_path(node, "datePublished")
            visible = (page.get("dates") or {}).get("visible")
            if published and visible:
                a, c = _norm_date(published), _norm_date(visible)
                if a and c and a != c:
                    contradictions.append((page["url"], "datePublished", a, f"page shows {c}"))

    if contradictions:
        findings.append(finding(
            check_id="extract.sd.contradicts_visible_content",
            title=f"Structured data disagrees with the visible page on {len(contradictions)} value(s)",
            severity="high", confidence="confirmed", stage="extract",
            category="discoverability", scope="url",
            evidence="; ".join(
                f"{url}: schema {prop} = {declared}, but the {rest}"
                for url, prop, declared, rest in contradictions[:5]
            )
            + ". Values were normalised for currency symbol, thousands separator and date format "
              "before comparison, so this is a genuine disagreement rather than a formatting "
              "difference.",
            affected_urls=[c[0] for c in contradictions],
            action=action(
                summary="Generate the structured data from the same source as the rendered page.",
                effort="medium",
                mechanism=(
                    "A consumer that trusts the markup will state the wrong value; markup that "
                    "contradicts the page is worse than no markup, because it misinforms "
                    "confidently."
                ),
                source="Google Search Central, Structured data general guidelines",
                patch=(
                    "# Bind the markup to the same template variable that renders the page:\n"
                    '#   "price": "{{ product.price }}"   not a hardcoded literal\n'
                    "# so the two cannot drift apart."
                ),
                verification=(
                    f"curl -s {contradictions[0][0]} | grep -o '\"price\"[^,}}]*' "
                    f"# compare with the price shown on the page"
                ),
            ),
        ))

    # ------------------------------------------------ site identity graph
    home = next((p for p in b.html_pages() if p["url"].rstrip("/") == b.origin.rstrip("/")), None)
    if home is None:
        skipped.append({
            "check_id": "extract.sd.identity_graph_weak",
            "reason": "the homepage was not among the crawled pages, so site identity could not be assessed.",
            "confidence_effect": "not assessed",
        })
        return findings, skipped, []

    home_types = types_of(home)
    identity_nodes = [
        n for n in nodes(home)
        if str(n.get("@type", "")).split("/")[-1].lower() in IDENTITY_TYPES
    ]
    sameas: list[str] = []
    for node in identity_nodes:
        raw = node.get("sameAs")
        if isinstance(raw, str):
            sameas.append(raw)
        elif isinstance(raw, list):
            sameas.extend(str(x) for x in raw)

    dangling = _dangling_ids(home)

    problems = []
    if not identity_nodes:
        problems.append(
            f"the homepage declares {sorted(home_types) or 'no structured data'} and none of it is "
            f"an Organization, LocalBusiness or Person node, so nothing states who runs this site"
        )
    if identity_nodes and not sameas:
        problems.append(
            "the identity node declares no sameAs links, so there is nothing connecting this site "
            "to any independent profile that could corroborate it"
        )
    if dangling:
        problems.append(
            f"{len(dangling)} @id reference(s) point at nodes that do not exist in the page graph: "
            f"{', '.join(dangling[:3])}"
        )

    if problems:
        findings.append(finding(
            check_id="extract.sd.identity_graph_weak",
            title="The site does not clearly state who publishes it",
            severity="medium", confidence="confirmed", stage="extract",
            category="discoverability", scope="site",
            evidence=f"On {home['url']}: " + "; ".join(problems) + ".",
            affected_urls=[home["url"]],
            action=action(
                summary="Publish an Organization node on the homepage with sameAs links to your real profiles.",
                effort="low",
                mechanism=(
                    "A named, linked entity lets a consumer connect statements on this site to the "
                    "same entity elsewhere; without it the brand is an unlinked string that may "
                    "collide with other things sharing the name."
                ),
                source="schema.org/Organization; handout appendix, Why agreement across the web matters",
                patch=_identity_patch(b, home),
                verification=f"curl -s {home['url']} | grep -o '\"sameAs\"[^]]*]'",
            ),
        ))

    return findings, skipped, []


def _dangling_ids(page: dict) -> list[str]:
    defined: set[str] = set()
    referenced: set[str] = set()

    def walk(node, top=False) -> None:
        if isinstance(node, dict):
            if "@id" in node and len(node) == 1:
                referenced.add(str(node["@id"]))
            elif "@id" in node:
                defined.add(str(node["@id"]))
            for k, v in node.items():
                if k != "@id":
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk((page.get("markup") or {}).get("jsonld") or [])
    return sorted(referenced - defined)


def _identity_patch(b, home: dict) -> str:
    import json

    name = (home.get("title") or "").split("—")[0].split("|")[0].strip() or "__FILL_IN__:organisation_name"
    desc = home.get("meta_description") or "__FILL_IN__:one_line_description"
    body = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": f"{b.origin}/#organization",
        "name": name,
        "url": b.origin + "/",
        "description": desc,
        "sameAs": [
            "__FILL_IN__:your_wikipedia_or_wikidata_url",
            "__FILL_IN__:your_linkedin_url",
            "__FILL_IN__:your_primary_social_or_github_url",
        ],
    }
    return '<script type="application/ld+json">\n' + json.dumps(body, indent=2) + "\n</script>"
