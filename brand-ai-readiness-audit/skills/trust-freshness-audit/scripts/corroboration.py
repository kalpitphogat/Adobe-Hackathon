#!/usr/bin/env python3
"""Stage trust: is there anything outside this site that agrees with it?

The handout appendix: "A claim that lives in only one spot is fragile; a claim
repeated consistently across lots of unrelated sources is far more likely to be
believed and repeated back."

CONFIDENCE CEILING
------------------
This check can never reach `confirmed`. Absence of corroboration cannot be
proven from one site: we can observe that a site declares no sameAs links and
cites no external sources, but we cannot observe that nobody else mentions it.
The finding says what we saw, not what exists, and its confidence is capped at
`likely`, dropping to `hypothesis` when the optional Wikidata lookup is
unavailable. Wikidata is OFF by default and never blocks a run.
"""

from __future__ import annotations

import re
import urllib.parse

from bundle import action, finding

CHECKS = [
    {"id": "trust.entity.no_external_corroboration", "stage": "trust", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "trust-freshness-audit",
     "confidence_ceiling": "likely"},
]

# Hosts that carry independent, checkable identity rather than self-published social presence.
AUTHORITATIVE = (
    "wikipedia.org", "wikidata.org", "crunchbase.com", "linkedin.com", "github.com",
    "companieshouse.gov.uk", "sec.gov", "opencorporates.com", "gov.uk", "europa.eu",
    "doi.org", "orcid.org", "scholar.google.com", "bloomberg.com", "reuters.com",
)


def sameas_links(page: dict) -> list[str]:
    out: list[str] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            raw = node.get("sameAs")
            if isinstance(raw, str):
                out.append(raw)
            elif isinstance(raw, list):
                out.extend(str(x) for x in raw)
            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk((page.get("markup") or {}).get("jsonld") or [])
    return out


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []

    pages = b.html_pages()
    home = next((p for p in pages if p["url"].rstrip("/") == b.origin.rstrip("/")), None)
    if not home:
        skipped.append({
            "check_id": "trust.entity.no_external_corroboration",
            "reason": "the homepage was not crawled, so site-level identity links could not be read.",
            "confidence_effect": "not assessed",
        })
        return findings, skipped, []

    same = [s for s in sameas_links(home) if s.startswith("http")]
    authoritative = [
        s for s in same
        if any(host in (urllib.parse.urlsplit(s).hostname or "") for host in AUTHORITATIVE)
    ]

    outbound = set()
    for page in pages:
        for link in (page.get("links") or {}).get("external", []):
            host = (urllib.parse.urlsplit(link).hostname or "").lower()
            if host and host not in b.site:
                outbound.add(host)

    # SUPPRESS: two or more resolving authoritative profiles is enough.
    if len(authoritative) >= 2:
        skipped.append({
            "check_id": "trust.entity.no_external_corroboration",
            "reason": (
                f"the homepage declares {len(authoritative)} sameAs link(s) to independent "
                f"profiles ({', '.join(authoritative[:3])}), which is sufficient corroboration "
                f"anchoring."
            ),
            "confidence_effect": "suppressed by design",
        })
        return findings, skipped, []

    wikidata_available = "wikidata" not in b.degraded_capabilities()
    confidence = "likely" if wikidata_available else "hypothesis"

    findings.append(finding(
        check_id="trust.entity.no_external_corroboration",
        title="Nothing connects this site to an independent record of the same entity",
        severity="medium", confidence=confidence, stage="trust",
        category="discoverability", scope="site",
        evidence=(
            f"{home['url']} declares {len(same)} sameAs link(s)"
            + (f" ({', '.join(same[:3])})" if same else "")
            + f", of which {len(authoritative)} point at an independent identity source such as "
              f"Wikipedia, Wikidata, Companies House, LinkedIn or GitHub. Across "
              f"{len(pages)} crawled pages the site links outward to {len(outbound)} distinct "
              f"external host(s). "
              f"This says what we observed ON THIS SITE. It is not evidence that no one else "
              f"mentions the brand, which cannot be established from the site alone, so this "
              f"finding is reported at {confidence} confidence and never as confirmed."
            + ("" if wikidata_available else " The optional Wikidata cross-check was unavailable, "
                                             "so confidence is reduced further to hypothesis.")
        ),
        affected_urls=[home["url"]],
        action=action(
            summary="Add sameAs links from your Organization node to profiles you already control.",
            effort="low",
            mechanism=(
                "sameAs states that this site and an independent record describe one entity, "
                "which lets a checker corroborate a claim here against a source elsewhere instead "
                "of taking it on trust."
            ),
            source="schema.org/sameAs; handout appendix, Why agreement across the web matters",
            patch=(
                '"sameAs": [\n'
                '  "__FILL_IN__:wikidata_or_wikipedia_url",\n'
                '  "__FILL_IN__:linkedin_company_url",\n'
                '  "__FILL_IN__:github_or_crunchbase_url"\n'
                "]\n"
                "<!-- Only list profiles that genuinely describe this same entity. -->"
            ),
            verification=f"curl -s {home['url']} | grep -o '\"sameAs\"[^]]*]'",
        ),
    ))

    return findings, skipped, []
