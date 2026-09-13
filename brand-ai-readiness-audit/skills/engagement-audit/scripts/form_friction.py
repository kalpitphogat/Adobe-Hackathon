#!/usr/bin/env python3
"""Stage act: how much does the form ask for before it gives anything back?"""

from __future__ import annotations

from bundle import action, finding, threshold, typed_threshold
from gating import Rule0b

CHECKS = [
    {"id": "act.form.field_count_excessive", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
    {"id": "act.form.high_friction_required_fields", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
    {"id": "act.form.unlabelled_inputs", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
]

# Page types where a long form is the point, not friction.
LONG_FORM_OK = {"utility"}


def _is_multistep(form: dict) -> bool:
    names = " ".join((f.get("name") or "").lower() for f in form.get("fields") or [])
    return "step" in names or any(
        (f.get("type") or "") == "hidden" and "step" in (f.get("name") or "").lower()
        for f in form.get("fields") or []
    )


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    gate = Rule0b(b)
    findings: list[dict] = []
    skipped: list[dict] = []
    friction_names = set(threshold(profile, "high_friction_fields", []) or [])

    for page in b.html_pages():
        page_type = b.page_type(page, profile)
        forms = page.get("forms") or []
        if not forms:
            continue
        if not gate.page_allowed("act.form.field_count_excessive", page):
            skipped.append(_skip("act.form.field_count_excessive", page))
            continue

        for form in forms:
            fields = form.get("fields") or []
            count = len(fields)
            if not count:
                continue

            # ------------------------------------------------- field count
            limit = typed_threshold(profile, "form_fields_max", page_type, 7) or 7
            if page_type in LONG_FORM_OK:
                skipped.append({
                    "check_id": "act.form.field_count_excessive",
                    "reason": (
                        f"{page['url']}: {count}-field form on a {page_type} page, where the fields "
                        f"are logistically necessary rather than friction."
                    ),
                    "confidence_effect": "suppressed by design",
                })
            elif _is_multistep(form):
                skipped.append({
                    "check_id": "act.form.field_count_excessive",
                    "reason": (
                        f"{page['url']}: the form appears to be multi-step, so total field count "
                        f"overstates what the visitor faces at once."
                    ),
                    "confidence_effect": "suppressed by design",
                })
            elif count > limit:
                listing = ", ".join(
                    f"{f['name'] or '(unnamed)'}:{f['type']}{'*' if f['required'] else ''}"
                    for f in fields
                )
                findings.append(finding(
                    check_id="act.form.field_count_excessive",
                    title=f"A {count}-field form stands between the visitor and the action",
                    severity="medium", confidence="confirmed", stage="act",
                    category="engagement", scope="url",
                    evidence=(
                        f"{page['url']} (page type {page_type}) posts to {form.get('action') or '(same page)'} "
                        f"with {count} visible fields against a threshold of {limit} for this site "
                        f"type. Fields, with * marking required: {listing}. Hidden and submit "
                        f"inputs were excluded from the count."
                    ),
                    affected_urls=[page["url"]],
                    action=action(
                        summary="Ask only for what is needed to deliver the next step; collect the rest later.",
                        effort="medium",
                        mechanism=(
                            "Every field is a separate decision and a separate chance to abandon; "
                            "fields that are not needed to fulfil the request cost completions "
                            "without returning anything."
                        ),
                        source="references/cro-frameworks.md",
                        patch=_minimal_form_patch(form, page_type),
                        verification=f"curl -s {page['url']} | grep -cE '<(input|select|textarea)'",
                    ),
                ))

            # --------------------------------------------- friction fields
            required_friction = [
                f for f in fields
                if f.get("required") and (f.get("name") or "").lower().replace("-", "_") in friction_names
            ]
            if required_friction and page_type not in ("utility",):
                names = ", ".join(f["name"] for f in required_friction)
                findings.append(finding(
                    check_id="act.form.high_friction_required_fields",
                    title=f"A top-of-funnel form requires {len(required_friction)} high-friction field(s)",
                    severity="medium", confidence="confirmed", stage="act",
                    category="engagement", scope="url",
                    evidence=(
                        f"{page['url']} (page type {page_type}) marks these as required: {names}. "
                        f"A visitor at this stage has not yet been given anything, so personal or "
                        f"organisational detail is being demanded before any value is delivered. "
                        f"On a checkout or application page these same fields would be necessary "
                        f"and this check does not fire there."
                    ),
                    affected_urls=[page["url"]],
                    action=action(
                        summary=f"Make {names} optional, or move them to a later step.",
                        effort="low",
                        mechanism=(
                            "Fields that feel invasive relative to what is being offered cause "
                            "abandonment at the field itself, not at submission."
                        ),
                        source="references/cro-frameworks.md",
                        patch="\n".join(
                            f'<input name="{f["name"]}" type="{f["type"]}">  <!-- required attribute removed -->'
                            for f in required_friction
                        ),
                        verification=f"curl -s {page['url']} | grep -E 'name=\"({'|'.join(f['name'] for f in required_friction)})\"'",
                    ),
                ))

            # ------------------------------------------------- labelling
            unlabelled = [f for f in fields if not f.get("labelled")]
            if not unlabelled:
                continue
            placeholder_only = [f for f in unlabelled if f.get("placeholder")]
            severity = "low" if len(placeholder_only) == len(unlabelled) else "medium"
            findings.append(finding(
                check_id="act.form.unlabelled_inputs",
                title=f"{len(unlabelled)} form field(s) have no programmatic label",
                severity=severity, confidence="confirmed", stage="act",
                category="engagement", scope="url",
                evidence=(
                    f"{page['url']}: {len(unlabelled)} of {count} fields have no <label>, "
                    f"aria-label or aria-labelledby: "
                    f"{', '.join(f['name'] or '(unnamed)' for f in unlabelled[:8])}. "
                    + (
                        f"All of them do carry a placeholder, which disappears on focus and is not "
                        f"exposed as a label, so this is reported at low severity."
                        if severity == "low"
                        else f"{len(unlabelled) - len(placeholder_only)} have neither a label nor a placeholder."
                    )
                ),
                affected_urls=[page["url"]],
                action=action(
                    summary="Give every field a visible, associated label.",
                    effort="low",
                    mechanism=(
                        "A placeholder vanishes as soon as the field is focused, so a visitor who "
                        "pauses mid-form loses the only description of what the field wanted."
                    ),
                    source="WCAG 2.2 Success Criterion 3.3.2 Labels or Instructions",
                    patch="\n".join(
                        f'<label for="{f["name"] or "field"}">{(f.get("placeholder") or "__FILL_IN__:label_text")}</label>\n'
                        f'<input id="{f["name"] or "field"}" name="{f["name"]}" type="{f["type"]}">'
                        for f in unlabelled[:4]
                    ),
                    verification=f"curl -s {page['url']} | grep -c '<label'",
                ),
            ))

    limitation = gate.limitation()
    return findings, skipped, ([limitation] if limitation else [])


def _minimal_form_patch(form: dict, page_type: str) -> str:
    fields = form.get("fields") or []
    keep = [f for f in fields if (f.get("type") in ("email",) or "email" in (f.get("name") or "").lower())]
    if not keep:
        keep = fields[:1]
    lines = [f'<form action="{form.get("action") or "__FILL_IN__:action"}" method="{form.get("method", "post")}">']
    for f in keep:
        name = f.get("name") or "email"
        lines.append(f'  <label for="{name}">__FILL_IN__:label_text</label>')
        lines.append(f'  <input id="{name}" name="{name}" type="{f.get("type", "text")}" required>')
    lines.append("  <button type=\"submit\">__FILL_IN__:verb_plus_object</button>")
    lines.append("</form>")
    lines.append("<!-- Collect the remaining detail after the visitor has received something. -->")
    return "\n".join(lines)


def _skip(check_id: str, page: dict) -> dict:
    return {
        "check_id": check_id,
        "reason": (
            f"{page['url']} serves an unhydrated shell with no rendered DOM, so visible content "
            f"was never observed. Suppressed entirely under gate Rule 0b."
        ),
        "confidence_effect": "suppressed entirely",
    }
