#!/usr/bin/env python3
"""Stage extract: is the markup the RIGHT type, and does it carry usable properties?"""

from __future__ import annotations

from bundle import action, finding
from extract_markup import eligible, get_path, nodes, spec, types_of

CHECKS = [
    {"id": "extract.sd.expected_type_missing", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "high", "skill": "structured-data-audit"},
    {"id": "extract.sd.required_props_missing", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "structured-data-audit"},
]


def _satisfied(node: dict, prop: str, aliases: dict) -> bool:
    if get_path(node, prop) not in (None, "", []):
        return True
    for alt in aliases.get(prop, []):
        if get_path(node, alt) not in (None, "", []):
            return True
    return False


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    conf = spec()
    aliases = conf.get("property_aliases", {})
    findings: list[dict] = []
    skipped: list[dict] = []

    wrong_type: list[tuple[dict, set, list]] = []
    prop_gaps: list[tuple[dict, str, list]] = []

    for page in b.html_pages():
        ok, why = eligible(b, page, profile)
        if not ok:
            continue
        present = types_of(page)
        if not present:
            continue  # already reported as absent
        page_type = b.page_type(page, profile)
        entry = conf["page_types"].get(page_type)
        if not entry:
            continue

        expected = {t.lower() for t in entry["expected"]}
        accepted = expected | {t.lower() for t in entry.get("accept_also", [])}

        confidence_pt = b.page_type_confidence(page, profile)
        if not (present & accepted):
            # SUPPRESS: if we are not sure what kind of page this is, we are not
            # sure what type it should declare either.
            if confidence_pt and confidence_pt < 0.6:
                skipped.append({
                    "check_id": "extract.sd.expected_type_missing",
                    "reason": (
                        f"{page['url']}: classified as {page_type} with only "
                        f"{confidence_pt:.2f} confidence, too low to assert which schema type it "
                        f"should declare."
                    ),
                    "confidence_effect": "suppressed by low classifier confidence",
                })
                continue
            wrong_type.append((page, present, entry["expected"]))
            continue

        # required properties, checked on the node that matches the expected type
        matching = [
            n for n in nodes(page)
            if str(n.get("@type", "")).split("/")[-1].lower() in accepted
        ]
        if not matching:
            continue
        node = matching[0]
        missing = [p for p in entry.get("required", []) if not _satisfied(node, p, aliases)]
        if missing:
            prop_gaps.append((page, str(node.get("@type")), missing))

    if wrong_type:
        findings.append(finding(
            check_id="extract.sd.expected_type_missing",
            title=f"{len(wrong_type)} page(s) declare structured data of the wrong kind",
            severity="high", confidence="confirmed", stage="extract",
            category="discoverability", scope="url",
            evidence="; ".join(
                f"{p['url']} is a {b.page_type(p, profile)} page declaring "
                f"{sorted(present) or ['nothing']} but none of {exp}"
                for p, present, exp in wrong_type[:5]
            ),
            affected_urls=[p["url"] for p, _, _ in wrong_type],
            action=action(
                summary="Declare the type that matches what the page is about.",
                effort="medium",
                mechanism=(
                    "A consumer selects markup by type; a product page typed only as WebPage "
                    "carries no price, no availability and nothing a shopping question can use."
                ),
                source="schema.org type hierarchy",
                patch=(
                    '<script type="application/ld+json">\n'
                    "{\n"
                    '  "@context": "https://schema.org",\n'
                    f'  "@type": "{wrong_type[0][2][0]}",\n'
                    f'  "name": {(wrong_type[0][0].get("title") or "__FILL_IN__:name")!r},\n'
                    f'  "url": "{wrong_type[0][0]["url"]}"\n'
                    "}\n"
                    "</script>"
                ),
                verification=(
                    f"curl -s {wrong_type[0][0]['url']} | grep -o '\"@type\"[^,}}]*'"
                ),
            ),
        ))

    if prop_gaps:
        findings.append(finding(
            check_id="extract.sd.required_props_missing",
            title=f"{len(prop_gaps)} page(s) declare a type but omit the properties that make it useful",
            severity="medium", confidence="confirmed", stage="extract",
            category="discoverability", scope="url",
            evidence="; ".join(
                f"{p['url']} declares {t} but has no {', '.join(missing)}"
                for p, t, missing in prop_gaps[:5]
            )
            + ". Properties are counted as present if any documented alias supplies them.",
            affected_urls=[p["url"] for p, _, _ in prop_gaps],
            action=action(
                summary="Populate the missing properties from the values already on the page.",
                effort="low",
                mechanism=(
                    "The type tells a consumer what kind of thing this is; the properties are the "
                    "answer itself, so a typed node with no properties answers nothing."
                ),
                source="references/required-props.md",
                patch=_prop_patch(prop_gaps[0]),
                verification=(
                    f"curl -s {prop_gaps[0][0]['url']} | grep -o "
                    f"'\"{prop_gaps[0][2][0].split('.')[-1]}\"[^,}}]*'"
                ),
            ),
        ))

    return findings, skipped, []


def _prop_patch(gap) -> str:
    page, schema_type, missing = gap
    lines = [
        '<script type="application/ld+json">',
        "{",
        '  "@context": "https://schema.org",',
        f'  "@type": "{schema_type}",',
        f'  "name": {(page.get("title") or "__FILL_IN__:name")!r},',
    ]
    nested: dict[str, list[str]] = {}
    for prop in missing:
        if "." in prop:
            head, tail = prop.split(".", 1)
            nested.setdefault(head, []).append(tail)
        else:
            lines.append(f'  "{prop}": "__FILL_IN__:{prop}",')
    for head, tails in nested.items():
        lines.append(f'  "{head}": {{')
        lines.append('    "@type": "Offer",')
        for tail in tails:
            lines.append(f'    "{tail}": "__FILL_IN__:{head}_{tail}",')
        lines[-1] = lines[-1].rstrip(",")
        lines.append("  },")
    lines[-1] = lines[-1].rstrip(",")
    lines += ["}", "</script>"]
    return "\n".join(lines)
