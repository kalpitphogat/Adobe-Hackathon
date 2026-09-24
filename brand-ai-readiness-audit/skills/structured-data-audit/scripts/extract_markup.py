#!/usr/bin/env python3
"""Stage extract: is any of this page machine-typed, and does it parse?

Shared helpers for the other two modules in this skill live here too, since
they all need the same flattened view of a page's structured data.
"""

from __future__ import annotations

import json
from pathlib import Path

from bundle import action, finding, threshold

REFERENCES = Path(__file__).resolve().parent.parent / "references"

CHECKS = [
    {"id": "extract.sd.absent_on_eligible_page", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "high", "skill": "structured-data-audit"},
    {"id": "extract.sd.invalid_syntax", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "high", "skill": "structured-data-audit"},
]


def spec() -> dict:
    return json.loads((REFERENCES / "schema-types.json").read_text(encoding="utf-8"))


def nodes(page: dict) -> list[dict]:
    """Flatten every structured-data node on a page, from any format."""
    out: list[dict] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            if "@type" in node or "@graph" in node:
                if "@type" in node:
                    out.append(node)
            for key, value in node.items():
                if key != "@type":
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    markup = page.get("markup") or {}
    walk(markup.get("jsonld") or [])
    for item in markup.get("microdata") or []:
        raw = (item.get("type") or "").rstrip("/").rsplit("/", 1)[-1]
        if raw:
            flat = {"@type": raw}
            for k, v in (item.get("properties") or {}).items():
                flat[k] = v[0] if isinstance(v, list) and len(v) == 1 else v
            out.append(flat)
    for item in markup.get("rdfa") or []:
        raw = (item.get("type") or "").rstrip("/").rsplit("/", 1)[-1]
        if raw:
            out.append({"@type": raw})
    return out


def types_of(page: dict) -> set[str]:
    found: set[str] = set()
    for node in nodes(page):
        t = node.get("@type")
        if isinstance(t, str):
            found.add(t.split("/")[-1].lower())
        elif isinstance(t, list):
            found.update(str(x).split("/")[-1].lower() for x in t)
    return found


def get_path(node: dict, dotted: str):
    """Resolve 'offers.price' through nested dicts and single-element lists."""
    current = node
    for part in dotted.split("."):
        if isinstance(current, list):
            current = current[0] if current else None
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    if isinstance(current, list):
        current = current[0] if current else None
    return current


def eligible(b, page, profile) -> tuple[bool, str]:
    """Should this page carry structured data at all?"""
    page_type = b.page_type(page, profile)
    conf = spec()
    if page_type in (conf.get("ineligible_page_types", {}).get("types") or []):
        return False, f"page type {page_type} is not expected to carry structured data"
    words = page.get("main_wordcount") or page.get("wordcount") or 0
    floor = threshold(profile, "structured_data_min_words", 200)
    if words < floor:
        return False, f"only {words} words of main content, below the {floor}-word floor"
    return True, ""


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []

    # -------------------------------------------------------- parse errors
    for page in b.html_pages():
        errors = ((page.get("markup") or {}).get("parse_errors")) or []
        if not errors:
            continue
        findings.append(finding(
            check_id="extract.sd.invalid_syntax",
            title=f"{len(errors)} JSON-LD block(s) on this page do not parse",
            severity="high", confidence="confirmed", stage="extract",
            category="discoverability", scope="url",
            evidence=(
                f"{page['url']}: "
                + "; ".join(
                    f"line {e.get('line')}: {e.get('error')} - near {e.get('excerpt', '')[:90]!r}"
                    for e in errors[:3]
                )
                + ". A block that does not parse is discarded entirely, so every property inside "
                  "it is lost even though the markup is present in the page."
            ),
            affected_urls=[page["url"]],
            action=action(
                summary="Fix the JSON syntax so the block parses.",
                effort="low",
                mechanism=(
                    "Structured data consumers parse the whole script block or none of it; one "
                    "syntax error discards every property in that block."
                ),
                source="JSON-LD 1.1, W3C Recommendation",
                patch=(
                    '<script type="application/ld+json">\n'
                    "{\n"
                    '  "@context": "https://schema.org",\n'
                    '  "@type": "__FILL_IN__:type",\n'
                    '  "name": "__FILL_IN__:name"\n'
                    "}\n"
                    "</script>\n"
                    "<!-- Validate with a JSON parser before shipping; trailing commas and\n"
                    "     unquoted keys are the two most common causes. -->"
                ),
                verification=(
                    f"curl -s {page['url']} | python -c \"import sys,re,json;"
                    f"[json.loads(m) for m in re.findall(r'<script type=.application/ld\\+json.>(.*?)</script>',"
                    f"sys.stdin.read(),re.S)]\" && echo OK"
                ),
            ),
        ))

    # ------------------------------------------------------------- absent
    missing = []
    for page in b.html_pages():
        ok, why = eligible(b, page, profile)
        if not ok:
            skipped.append({
                "check_id": "extract.sd.absent_on_eligible_page",
                "reason": f"{page['url']}: {why}.",
                "confidence_effect": "suppressed by design",
            })
            continue
        if types_of(page):
            continue
        missing.append(page)

    if missing:
        by_type: dict[str, list[str]] = {}
        for page in missing:
            by_type.setdefault(b.page_type(page, profile), []).append(page["url"])
        eligible_count = sum(
            1 for p in b.html_pages() if eligible(b, p, profile)[0]
        )
        findings.append(finding(
            check_id="extract.sd.absent_on_eligible_page",
            title=f"{len(missing)} of {eligible_count} eligible page(s) carry no structured data at all",
            severity="high", confidence="confirmed", stage="extract",
            category="discoverability", scope="url",
            evidence=(
                f"No JSON-LD, microdata or RDFa found on: "
                + "; ".join(f"{t} ({len(urls)}): {', '.join(urls[:3])}" for t, urls in sorted(by_type.items()))
                + f". Utility pages and pages under the "
                  f"{threshold(profile, 'structured_data_min_words', 200)}-word floor were excluded "
                  f"from the eligible set and are not counted here."
            ),
            affected_urls=[p["url"] for p in missing],
            action=action(
                summary="Add JSON-LD declaring what each page is about.",
                effort="medium",
                mechanism=(
                    "Structured data states a fact in a typed form, so a consumer can extract it "
                    "without having to infer it from prose it may parse differently."
                ),
                source="schema.org; Google Search Central, Structured data general guidelines",
                patch=_starter_patch(b, missing[0], profile),
                verification=(
                    f"curl -s {missing[0]['url']} | grep -c 'application/ld+json'  # expect at least 1"
                ),
            ),
        ))

    return findings, skipped, []


def _starter_patch(b, page: dict, profile) -> str:
    """A JSON-LD block built from values observed on the page. Never invented."""
    conf = spec()
    page_type = b.page_type(page, profile)
    entry = conf["page_types"].get(page_type) or conf["page_types"]["other"]
    schema_type = entry["expected"][0]
    title = page.get("title") or "__FILL_IN__:name"
    desc = page.get("meta_description") or "__FILL_IN__:description"
    body = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": title,
        "description": desc,
        "url": page["url"],
    }
    for prop in entry.get("required", []):
        if "." in prop:
            head, tail = prop.split(".", 1)
            body.setdefault(head, {"@type": "Offer"})
            if isinstance(body[head], dict):
                body[head][tail] = f"__FILL_IN__:{prop.replace('.', '_')}"
        elif prop not in body:
            body[prop] = f"__FILL_IN__:{prop}"
    return (
        '<script type="application/ld+json">\n'
        + json.dumps(body, indent=2)
        + "\n</script>"
    )
