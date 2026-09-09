#!/usr/bin/env python3
"""The gate cascade. See references/gate-rules.md for the full statement.

Short version, because the distinction is the whole design:

  reach -> read -> extract -> trust    are causally ordered for DISCOVERABILITY.
                                       An upstream failure makes downstream
                                       findings MOOT, so they are capped and
                                       tagged blocked_by, never deleted.

  act                                  is NOT causally downstream of reach. A
                                       visitor arriving from an ad does not care
                                       whether a crawler was let in.

  act IS evidentially downstream of read. If we never observed the page a
  visitor sees, engagement findings are UNEVIDENCED, so they are SUPPRESSED
  ENTIRELY rather than capped. Capping asserts a weaker claim; suppression
  asserts none, and none is what we have.
"""

from __future__ import annotations

from severity import SEVERITY_RANK, cap_severity, downgrade_confidence

STAGE_ORDER = ["reach", "read", "extract", "trust"]

# Findings that close a gate for the entire site rather than one URL.
SITE_SCOPE_CLOSERS = {
    "reach.robots.blanket_disallow",
    "reach.robots.ai_search_bot_blocked",
    "reach.edge.bot_ua_blocked",
}
URL_SCOPE_CLOSERS = {
    "reach.index.noindex_on_content",
    "read.render.raw_text_gap",
    "read.render.empty_spa_shell",
}

# Rule 1 exception: a check whose severity ceiling is low can never close a gate.
NEVER_CLOSES_GATE = {"reach.agent.llms_txt_absent"}

BLOCKED_SEVERITY_CEILING = "medium"


class GateState:
    def __init__(self) -> None:
        self.site_closed: dict[str, dict] = {}
        self.url_closed: dict[str, dict[str, dict]] = {}
        self.notes: list[str] = []

    def close_site(self, stage: str, finding: dict) -> None:
        if stage not in self.site_closed:
            self.site_closed[stage] = finding

    def close_url(self, stage: str, url: str, finding: dict) -> None:
        self.url_closed.setdefault(stage, {})
        self.url_closed[stage].setdefault(url, finding)

    def blocker_for(self, finding: dict) -> dict | None:
        """The earliest upstream finding that makes this one moot, or None.

        Rule 4: exactly one blocker is named, the most upstream one, because the
        report should point at a root cause rather than a chain.
        """
        stage = finding.get("stage")
        if stage not in STAGE_ORDER:
            return None
        my_index = STAGE_ORDER.index(stage)
        urls = set(finding.get("affected_urls") or [])
        for upstream in STAGE_ORDER[:my_index]:
            if upstream in self.site_closed:
                return self.site_closed[upstream]
            closed_urls = self.url_closed.get(upstream, {})
            if not closed_urls:
                continue
            if urls and urls <= set(closed_urls):
                return closed_urls[sorted(urls)[0]]
        return None


def build_gate_state(findings: list[dict]) -> GateState:
    """Rule 1: a gate closes on a critical, or on two or more highs in one stage."""
    state = GateState()
    by_stage_site: dict[str, list[dict]] = {}

    for finding in findings:
        stage = finding.get("stage")
        if stage not in STAGE_ORDER:
            continue
        check_id = finding.get("check_id", "")
        if check_id in NEVER_CLOSES_GATE:
            continue
        severity = finding.get("severity", "info")

        if check_id in SITE_SCOPE_CLOSERS and severity == "critical":
            state.close_site(stage, finding)
            continue
        if check_id in URL_SCOPE_CLOSERS and severity in ("critical", "high"):
            for url in finding.get("affected_urls") or []:
                state.close_url(stage, url, finding)
            continue
        if severity == "critical" and finding.get("scope") == "site":
            state.close_site(stage, finding)
            continue
        if severity == "high":
            by_stage_site.setdefault(stage, []).append(finding)

    # two or more highs at the same stage and scope also close it
    for stage, group in by_stage_site.items():
        site_scoped = [f for f in group if f.get("scope") == "site"]
        if len(site_scoped) >= 2:
            state.close_site(stage, sorted(site_scoped, key=lambda f: f["check_id"])[0])

    return state


def apply_cascade(findings: list[dict], id_of) -> tuple[list[dict], int]:
    """Cap blocked discoverability findings. Returns (findings, blocked_count).

    Rule 3: cap, never delete. The finding stays in the report because it is a
    real defect that will matter the moment the blocker is fixed; it is capped
    because right now it changes nothing.
    """
    state = build_gate_state(findings)
    blocked = 0

    for finding in findings:
        if finding.get("category") != "discoverability":
            continue  # Rule 0: gates never touch engagement
        blocker = state.blocker_for(finding)
        if blocker is None or blocker is finding:
            continue
        if id_of(blocker) == id_of(finding):
            continue

        original = finding["severity"]
        finding["severity"] = cap_severity(original, BLOCKED_SEVERITY_CEILING)
        finding["blocked_by"] = id_of(blocker)

        # Rule 3 nuance: only downgrade confidence when the evidence itself was
        # collected through the blocked path. Independently gathered evidence
        # keeps its confidence, because the block does not make it less true.
        if blocker.get("stage") == "read" and finding.get("stage") in ("extract", "trust"):
            finding["confidence"] = downgrade_confidence(finding.get("confidence", "likely"))
        blocked += 1

    return findings, blocked


def gate_summary(findings: list[dict], id_of) -> list[str]:
    """Human sentences describing what is blocking what."""
    by_blocker: dict[str, int] = {}
    for finding in findings:
        blocker = finding.get("blocked_by")
        if blocker:
            by_blocker[blocker] = by_blocker.get(blocker, 0) + 1
    out = []
    for blocker_id, count in sorted(by_blocker.items()):
        root = next((f for f in findings if id_of(f) == blocker_id), None)
        title = root["title"] if root else blocker_id
        out.append(
            f"{count} finding(s) are recorded but capped at {BLOCKED_SEVERITY_CEILING} because "
            f"{blocker_id} ({title}) blocks them. They become relevant the moment {blocker_id} is "
            f"fixed."
        )
    return out
