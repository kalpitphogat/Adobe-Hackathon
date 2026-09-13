#!/usr/bin/env python3
"""Classify site archetype and per-page type, then select the threshold profile.

This is where generalisation to unseen sites lives. No audit check hardcodes a
number; each asks this profile for its thresholds. Classification is from
observed signals - URL shape, structured-data types, form and CTA presence,
content length distribution - never from a list of known sites, because the
audit is graded on sites it has never seen.

Every classification carries a confidence. A low-confidence archetype makes
downstream checks lower their own confidence rather than pretend.

CLI contract: see ai-readiness-orchestrator/references/skill-cli-contract.md
  --bundle <dir>   required, an evidence bundle
  stdout           exactly one JSON object
  exit 0 ran, 3 precondition unmet, 1 internal error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path

SCHEMA_VERSION = "1.0"
REFERENCES = Path(__file__).resolve().parent.parent / "references"

PAGE_TYPES = (
    "home", "product", "category", "article", "docs", "pricing",
    "contact", "about", "utility", "other",
)

ARCHETYPES = (
    "docs", "developer-platform", "saas-marketing", "e-commerce",
    "publisher", "local-business", "other",
)

# Schema.org @types that identify a page type with high confidence, because the
# site itself declared them.
SCHEMA_TYPE_HINTS = {
    "product": "product", "offer": "product", "itemlist": "category",
    "article": "article", "newsarticle": "article", "blogposting": "article",
    "techarticle": "docs", "apireference": "docs", "howto": "docs",
    "contactpage": "contact", "aboutpage": "about", "faqpage": "other",
    "collectionpage": "category", "webpage": None, "organization": None,
    "localbusiness": None, "store": None, "restaurant": None,
}

URL_RULES = (
    (r"^/?$", "home", 0.95),
    (r"/(contact|contact-us|get-in-touch)/?$", "contact", 0.9),
    (r"/(about|about-us|team|company|our-story|who-we-are)(/|$)", "about", 0.85),
    (r"/(pricing|plans|price|subscribe)/?$", "pricing", 0.9),
    (r"/(docs|documentation|guide|guides|reference|api|manual|handbook)(/|$)", "docs", 0.85),
    (r"/(blog|news|article|post|insights|stories)/[^/]+/?$", "article", 0.85),
    (r"/(blog|news|insights|stories|resources)/?$", "category", 0.8),
    # /collections/<slug> is a CATEGORY on every major storefront platform.
    # Treating it as a product page applied product thresholds to listing pages.
    (r"/(collections|category|categories|catalogue|catalog|range|shop-all)/[^/]+/?$", "category", 0.85),
    (r"/(product|products|item|p)/[^/]+/?$", "product", 0.85),
    (r"/(product|products|shop|store|collections|category|catalogue|catalog)/?$", "category", 0.8),
    (r"/(login|signin|sign-in|register|signup|cart|checkout|account|search|404)(/|$)", "utility", 0.9),
    (r"/(privacy|terms|legal|cookies?|imprint|gdpr|accessibility)(/|$)", "utility", 0.85),
)

ARCHETYPE_SIGNALS = {
    "e-commerce": [
        ("schema_product", 3.0), ("has_price", 2.0), ("cart_path", 2.5),
        ("many_product_urls", 2.0), ("add_to_cart_text", 2.0),
    ],
    "docs": [
        ("docs_path_share", 3.0), ("schema_techarticle", 2.0),
        ("code_blocks", 1.5), ("long_pages", 1.0),
    ],
    "developer-platform": [
        ("docs_path_share", 1.5), ("api_path", 2.5), ("code_blocks", 2.0),
        ("github_link", 1.5), ("schema_techarticle", 1.0),
    ],
    "publisher": [
        ("schema_article", 2.5), ("many_article_urls", 2.5), ("bylines", 2.0),
        ("dated_pages", 1.5),
    ],
    "local-business": [
        ("schema_localbusiness", 3.5), ("opening_hours", 2.5),
        ("postal_address", 1.0), ("phone_number", 0.5), ("small_site", 0.5),
    ],
    "saas-marketing": [
        ("pricing_page", 2.0), ("trial_cta", 2.0), ("schema_softwareapp", 2.0),
        ("feature_pages", 1.0), ("no_cart", 0.5),
    ],
}

PRICE_RE = re.compile(r"(?:[$£€¥]\s?\d[\d,.]*|\b\d[\d,.]*\s?(?:USD|EUR|GBP|INR)\b)", re.I)
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}")
POSTAL_RE = re.compile(r"\b\d{4,6}\b|\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b")
HOURS_RE = re.compile(r"\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\b[^.]{0,30}\d{1,2}[:.]?\d{0,2}\s*(am|pm|-)", re.I)
BYLINE_RE = re.compile(r"\bby\s+[A-Z][a-z]+\s+[A-Z][a-z]+", re.M)
TRIAL_RE = re.compile(
    r"\b(free trial|start (a |an )?(\d+[- ]day )?(free )?trial|book a demo|request a demo|"
    r"get started free|try it free|start free)\b",
    re.I,
)
CART_RE = re.compile(r"\b(add to (cart|basket|bag)|buy now|checkout)\b", re.I)


def load_bundle(bundle: Path) -> tuple[dict, list[dict]]:
    meta = json.loads((bundle / "meta.json").read_text(encoding="utf-8"))
    pages = [
        json.loads(line)
        for line in (bundle / "pages.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return meta, pages


def schema_types(page: dict) -> set[str]:
    """Every @type declared on a page, lowercased, from JSON-LD and microdata."""
    out: set[str] = set()

    def walk(node) -> None:
        if isinstance(node, dict):
            t = node.get("@type")
            if isinstance(t, str):
                out.add(t.lower())
            elif isinstance(t, list):
                out.update(str(x).lower() for x in t)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    markup = page.get("markup") or {}
    walk(markup.get("jsonld") or [])
    for item in markup.get("microdata") or []:
        raw = (item.get("type") or "").rstrip("/").rsplit("/", 1)[-1]
        if raw:
            out.add(raw.lower())
    return out


def classify_page(page: dict) -> tuple[str, float, list[str]]:
    """Type one page.

    Order matters, and the obvious order is wrong. Schema normally beats URL
    shape because the site declared it - but a handful of path names are
    unambiguous statements of intent that outrank a generic schema type. A SaaS
    site that marks up its /pricing page as schema.org/Product with an Offer is
    doing something correct and idiomatic; typing that page as a product page
    would then apply e-commerce thresholds to a pricing page and mis-fire the
    cost-signal and thin-content checks.

    So: unambiguous path names first, then schema, then softer path rules.
    """
    url = page.get("url", "")
    path = urllib.parse.urlsplit(url).path or "/"
    signals: list[str] = []
    types = schema_types(page)

    for pattern, label, confidence in URL_RULES:
        if confidence >= 0.9 and re.search(pattern, path, re.I):
            hinted = next((SCHEMA_TYPE_HINTS.get(t) for t in sorted(types) if SCHEMA_TYPE_HINTS.get(t)), None)
            signals.append(f"URL path matches {pattern}, an unambiguous {label} path")
            if hinted and hinted != label:
                signals.append(
                    f"schema @type implies {hinted}, but the explicit {label} path wins; "
                    f"marking up a {label} page with that type is idiomatic, not a defect"
                )
            return label, confidence, signals

    for t in sorted(types):
        hinted = SCHEMA_TYPE_HINTS.get(t)
        if hinted:
            signals.append(f"schema @type {t} implies {hinted}")
            return hinted, 0.92, signals

    for pattern, label, confidence in URL_RULES:
        if re.search(pattern, path, re.I):
            signals.append(f"URL path matches {pattern} implying {label}")
            return label, confidence, signals

    words = page.get("wordcount") or 0
    forms = page.get("forms") or []
    if page.get("status") != 200:
        return "utility", 0.5, [f"status {page.get('status')}"]
    if words >= 400 and page.get("dates", {}).get("schema_published"):
        signals.append("long page with a publication date")
        return "article", 0.65, signals
    if words >= 500:
        signals.append(f"{words} words with no type-specific signal")
        return "article", 0.5, signals
    if forms and sum(f.get("field_count", 0) for f in forms) >= 3:
        signals.append("form-dominant page with no other signal")
        return "contact", 0.45, signals
    signals.append("no decisive signal")
    return "other", 0.35, signals


def archetype_evidence(pages: list[dict]) -> dict[str, bool]:
    """Boolean site-level signals feeding archetype scoring."""
    total = max(1, len(pages))
    all_types: set[str] = set()
    for page in pages:
        all_types |= schema_types(page)

    text_all = " ".join((p.get("main_text") or "")[:4000] for p in pages)
    paths = [urllib.parse.urlsplit(p.get("url", "")).path.lower() for p in pages]
    page_types = [p.get("_page_type") for p in pages]

    def share(label: str) -> float:
        return sum(1 for t in page_types if t == label) / total

    external = {link for p in pages for link in (p.get("links", {}) or {}).get("external", [])}

    return {
        "schema_product": bool({"product", "offer"} & all_types),
        "schema_article": bool({"article", "newsarticle", "blogposting"} & all_types),
        "schema_techarticle": bool({"techarticle", "apireference", "howto"} & all_types),
        "schema_localbusiness": bool(
            {"localbusiness", "store", "restaurant", "dentist", "medicalclinic"} & all_types
        ),
        "schema_softwareapp": bool({"softwareapplication", "saas"} & all_types),
        "has_price": bool(PRICE_RE.search(text_all)),
        "cart_path": any("/cart" in p or "/checkout" in p or "/basket" in p for p in paths),
        "no_cart": not any("/cart" in p or "/checkout" in p for p in paths),
        "add_to_cart_text": bool(CART_RE.search(text_all)),
        "many_product_urls": share("product") >= 0.25,
        "many_article_urls": share("article") >= 0.35,
        "docs_path_share": sum(1 for p in paths if "/doc" in p or "/guide" in p or "/reference" in p) / total >= 0.25,
        "api_path": any("/api" in p for p in paths),
        "code_blocks": "INFORMATION_SCHEMA" in text_all or "npm install" in text_all or "pip install" in text_all,
        "github_link": any("github.com" in e for e in external),
        "long_pages": sum(1 for p in pages if (p.get("main_wordcount") or 0) > 400) / total >= 0.4,
        "bylines": bool(BYLINE_RE.search(text_all)),
        "dated_pages": sum(1 for p in pages if (p.get("dates") or {}).get("schema_published")) / total >= 0.3,
        "postal_address": bool(POSTAL_RE.search(text_all)),
        "phone_number": bool(PHONE_RE.search(text_all)),
        "opening_hours": bool(HOURS_RE.search(text_all)),
        "small_site": len(pages) <= 8,
        "pricing_page": any(t == "pricing" for t in page_types),
        "trial_cta": bool(TRIAL_RE.search(text_all)),
        "feature_pages": any("/feature" in p or "/solution" in p or "/platform" in p for p in paths),
    }


def classify_archetype(pages: list[dict]) -> tuple[str, float, list[str]]:
    if not pages:
        return "other", 0.0, ["no pages were collected"]

    evidence = archetype_evidence(pages)
    scores: dict[str, float] = {}
    fired: dict[str, list[str]] = {}
    for archetype, signals in ARCHETYPE_SIGNALS.items():
        total = 0.0
        hits = []
        for name, weight in signals:
            if evidence.get(name):
                total += weight
                hits.append(f"{name} (+{weight})")
        scores[archetype] = total
        fired[archetype] = hits

    # Some archetypes have a necessary condition, not just a score. Marking a
    # SaaS pricing plan up as schema.org/Product with an Offer is idiomatic, so
    # product schema plus a price is NOT sufficient evidence of a shop. Without
    # this gate a docs-and-pricing SaaS site classifies as e-commerce and then
    # gets e-commerce thresholds applied to every page.
    REQUIREMENTS = {
        # A shop needs a way to buy. Product schema plus a price is how SaaS
        # sites mark up a pricing plan.
        "e-commerce": ("cart_path", "add_to_cart_text", "many_product_urls"),
        # A local business is identified by opening hours or LocalBusiness
        # schema. A postal address and phone number in the footer are universal
        # and identify nothing.
        "local-business": ("schema_localbusiness", "opening_hours"),
        # A publisher publishes at volume. One blog post with a byline is a
        # company blog, which nearly every site has.
        "publisher": ("many_article_urls",),
        # Documentation has to be a substantial share of the site, not one page.
        "docs": ("docs_path_share", "schema_techarticle"),
    }
    for archetype, needed in REQUIREMENTS.items():
        if archetype in scores and not any(evidence.get(n) for n in needed):
            scores[archetype] = 0.0
            fired[archetype] = [
                f"disqualified: none of {list(needed)} observed, which are necessary for {archetype}"
            ]

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    best, best_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0

    if best_score < 3.0:
        return "other", 0.3, [f"no archetype scored above 3.0 (best was {best} at {best_score})"]

    # Confidence is the margin over the runner-up, so a site that looks equally
    # like two archetypes is reported as uncertain rather than arbitrarily typed.
    margin = (best_score - runner_up) / best_score
    confidence = round(min(0.95, 0.55 + margin * 0.45), 2)
    return best, confidence, fired[best]


def merge_thresholds(profiles: dict, archetype: str) -> dict:
    """Archetype overrides layered onto the defaults, one level deep."""
    merged = json.loads(json.dumps(profiles["default"]))
    override = profiles.get("archetypes", {}).get(archetype, {})
    for key, value in override.items():
        if key.startswith("_"):
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged


def build_profile(bundle: Path) -> dict:
    meta, pages = load_bundle(bundle)
    profiles = json.loads((REFERENCES / "threshold-profiles.json").read_text(encoding="utf-8"))

    page_out = {}
    for page in pages:
        page_type, confidence, signals = classify_page(page)
        page["_page_type"] = page_type
        page_out[page["url"]] = {
            "page_type": page_type,
            "confidence": confidence,
            "signals": signals,
        }

    archetype, arch_confidence, arch_signals = classify_archetype(pages)
    thresholds = merge_thresholds(profiles, archetype)

    notes = []
    if archetype == "other":
        notes.append(
            "Archetype could not be determined from observed signals. Default thresholds "
            "apply and every archetype-dependent check lowers its confidence one notch."
        )
    if not pages:
        notes.append("No pages were collected, so no page-level classification exists.")

    return {
        "skill": "site-profile-classifier",
        "schema_version": SCHEMA_VERSION,
        "site": meta.get("resolved_origin", ""),
        "archetype": archetype,
        "archetype_confidence": arch_confidence,
        "archetype_signals": sorted(arch_signals),
        "archetype_scores": {},
        "pages": dict(sorted(page_out.items())),
        "page_type_counts": {
            t: sum(1 for v in page_out.values() if v["page_type"] == t)
            for t in PAGE_TYPES
            if any(v["page_type"] == t for v in page_out.values())
        },
        "thresholds": thresholds,
        "notes": notes,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="profile.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--bundle", required=True, help="evidence bundle directory")
    args = parser.parse_args(argv)

    bundle = Path(args.bundle)
    if not (bundle / "meta.json").exists() or not (bundle / "pages.jsonl").exists():
        print(f"error: {bundle} is not an evidence bundle", file=sys.stderr)
        return 3
    try:
        print(json.dumps(build_profile(bundle), indent=2, sort_keys=True))
    except Exception as exc:  # noqa: BLE001
        print(f"internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
