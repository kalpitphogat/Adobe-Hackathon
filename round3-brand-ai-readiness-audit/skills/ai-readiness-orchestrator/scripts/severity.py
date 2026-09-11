#!/usr/bin/env python3
"""Severity, confidence, effort and ICE scoring.

ICE is Impact x Confidence x Ease, reported as the mean of the three on a 0-10
scale. Two deliberate choices:

  * Confidence is NOT a second judgement call. It is a deterministic map from
    the finding's own confidence enum - confirmed 9, likely 6, hypothesis 3 -
    so the same finding always scores the same, and so that confidence is not
    counted twice (once as a first-class field used by the gate cascade, and
    again as a free-floating estimate here).

  * Impact derives from post-gate severity, so a finding capped by the cascade
    also drops down the ranking. That is the point: a defect that is moot until
    something upstream is fixed should not outrank the thing blocking it.
"""

from __future__ import annotations

SEVERITY_ORDER = ["info", "low", "medium", "high", "critical"]
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITY_ORDER)}

CONFIDENCE_ORDER = ["hypothesis", "likely", "confirmed"]
CONFIDENCE_RANK = {c: i for i, c in enumerate(CONFIDENCE_ORDER)}

# Deterministic, documented, single source. See references/ice-model.md.
CONFIDENCE_TO_ICE = {"confirmed": 9.0, "likely": 6.0, "hypothesis": 3.0}
SEVERITY_TO_IMPACT = {"critical": 10.0, "high": 8.0, "medium": 5.0, "low": 3.0, "info": 1.0}
EFFORT_TO_EASE = {"low": 9.0, "medium": 5.0, "high": 2.0}

PRIORITY_FROM_SEVERITY = {
    "critical": "critical", "high": "high", "medium": "medium", "low": "low", "info": "low",
}


def cap_severity(current: str, ceiling: str) -> str:
    """Lower to the ceiling. Never raises: capping only ever reduces."""
    if SEVERITY_RANK.get(current, 0) > SEVERITY_RANK.get(ceiling, 0):
        return ceiling
    return current


def downgrade_confidence(current: str, steps: int = 1) -> str:
    idx = CONFIDENCE_RANK.get(current, 1)
    return CONFIDENCE_ORDER[max(0, idx - steps)]


def ice(severity: str, confidence: str, effort: str) -> tuple[float, dict]:
    impact = SEVERITY_TO_IMPACT.get(severity, 5.0)
    conf = CONFIDENCE_TO_ICE.get(confidence, 6.0)
    ease = EFFORT_TO_EASE.get(effort, 5.0)
    score = round((impact + conf + ease) / 3.0, 1)
    return score, {"impact": impact, "confidence": conf, "ease": ease}


def score_finding(finding: dict) -> dict:
    """Attach priority, ICE and its components. Mutates and returns the finding."""
    action = finding.setdefault("suggested_action", {})
    effort = action.get("effort") or "medium"
    action["effort"] = effort
    action["priority"] = PRIORITY_FROM_SEVERITY.get(finding["severity"], "medium")
    score, components = ice(finding["severity"], finding.get("confidence", "likely"), effort)
    action["ice"] = score
    action["ice_components"] = components
    return finding


def sort_key(finding: dict):
    """Severity desc, then ICE desc, then stage order, then check_id.

    Ends on check_id so the ordering is total and therefore deterministic: two
    findings that tie on every other axis still have one stable order.
    """
    stage_order = {"reach": 0, "read": 1, "extract": 2, "trust": 3, "act": 4}
    return (
        -SEVERITY_RANK.get(finding["severity"], 0),
        -(finding.get("suggested_action", {}).get("ice") or 0),
        stage_order.get(finding.get("stage", "act"), 9),
        finding.get("check_id", ""),
        (finding.get("affected_urls") or [""])[0],
    )
