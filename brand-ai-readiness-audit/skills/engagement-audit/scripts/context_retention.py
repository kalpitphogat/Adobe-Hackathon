#!/usr/bin/env python3
"""Stage act: does the page work for someone who arrives with no prior context?

This module covers the handout appendix subsection "Personalization and prior
context", which observes that assistants tailor answers using context they
already hold about a person. The on-site analogue is a page that assumes state
the visitor does not have - a plan they have not selected, a conversation they
were not part of, a session they never started.

DELIBERATE DUPLICATION
----------------------
`self_contained` below is a second, standalone copy of the self-containment
predicate that answerability-audit uses in retrievability_sim.py. It is copied
rather than imported because no script in this marketplace may import from a
sibling skill folder: the handout requires every skill folder to independently
satisfy the agentskills.io spec, and a folder that cannot be lifted out and run
alone does not satisfy that. See
ai-readiness-orchestrator/references/skill-cli-contract.md, and
tests/validate_marketplace.py :: portability.no_cross_skill_imports which
enforces it.

The two copies answer the same question about different subjects: there, whether
a chunk makes sense lifted out of its page; here, whether a page makes sense
lifted out of a session.
"""

from __future__ import annotations

import re

from bundle import action, finding, threshold
from gating import Rule0b

CHECKS = [
    {"id": "act.context.no_onward_path", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
    {"id": "act.context.assumes_prior_context", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
]

# Page types where a dead end is the intended design.
# Only page types where the visitor finishes reading and needs a next step.
# A homepage or pricing page uses global navigation as its onward path, so
# counting in-content links there produced false positives on the control.
ONWARD_PATH_TYPES = {"article", "docs", "product", "other"}
TERMINAL_TYPES = {"utility"}

# Phrases that presume state a first-time visitor cannot have.
PRIOR_CONTEXT = [
    (re.compile(r"\byour (selected|chosen|current|existing) [a-z ]{2,20}\b", re.I), "a selection the visitor has not made"),
    (re.compile(r"\bas (we )?(discussed|mentioned|agreed|noted) (above|earlier|previously)?\b", re.I), "an earlier conversation"),
    (re.compile(r"\bcontinue where you left off\b", re.I), "a previous session"),
    (re.compile(r"\bwelcome back\b", re.I), "a previous visit"),
    # A bare "your plan" / "your account" was tried and REMOVED during S4.
    # Second-person instructional voice - "up to your plan limit" - is standard
    # in documentation and marketing copy, and matching it fired on the healthy
    # control fixture. Only phrasings that presume a PRIOR SESSION remain.
    (re.compile(r"\bas (mentioned|described|explained) above\b", re.I), "text earlier on the page"),
    (re.compile(r"\b(resume|return to) your\b", re.I), "an interrupted flow"),
    (re.compile(r"\bthe (above|aforementioned) [a-z]{3,20}\b", re.I), "an earlier reference"),
]

# "This page", "This guide", "This section" are SELF-referential: the referent
# is the document the reader already has. Only a bare demonstrative is unresolved.
SELF_REFERENTIAL = re.compile(
    r"^\s*(this|that|these|those)\s+"
    r"(page|document|guide|section|article|post|chapter|tutorial|reference|site|release|note)s?\b",
    re.I,
)
PRONOUN_OPENER = re.compile(r"^\s*(it|this|that|they|these|those|he|she|there)\b", re.I)


def self_contained(text: str, entity: str | None = None) -> tuple[bool, str]:
    """Does this passage make sense lifted out of its surrounding context?

    Standalone copy; see the module docstring for why it is not imported.

    A passage fails if it opens with an unresolved pronoun or a backward
    reference, or if it never names the entity it is about.
    """
    stripped = (text or "").strip()
    if not stripped:
        return False, "empty"
    if PRONOUN_OPENER.match(stripped) and not SELF_REFERENTIAL.match(stripped):
        return False, f"opens with the unresolved reference {stripped.split()[0]!r}"
    for pattern, what in PRIOR_CONTEXT:
        m = pattern.search(stripped)
        if m:
            return False, f"assumes {what} via {m.group(0)!r}"
    if entity and entity.lower() not in stripped.lower():
        return False, f"never names {entity!r}"
    return True, "self-contained"


def _brand(b) -> str | None:
    home = next((p for p in b.html_pages() if p["url"].rstrip("/") == b.origin.rstrip("/")), None)
    if not home:
        return None
    title = home.get("title") or ""
    for sep in (" — ", " – ", " | ", " - ", ": "):
        if sep in title:
            parts = [p.strip() for p in title.split(sep)]
            return min(parts, key=len) or None
    return title.strip() or None


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    gate = Rule0b(b)
    findings: list[dict] = []
    skipped: list[dict] = []
    min_onward = threshold(profile, "onward_links_min", 3)

    for page in b.html_pages():
        page_type = b.page_type(page, profile)
        text = b.observed_text(page)

        # --------------------------------------------------- onward path
        if page_type not in ONWARD_PATH_TYPES:
            pass
        elif not gate.page_allowed("act.context.no_onward_path", page):
            skipped.append(_skip("act.context.no_onward_path", page))
        else:
            in_main = (page.get("links") or {}).get("internal_in_main") or []
            if len(in_main) < min_onward and len(text.split()) >= 80:
                findings.append(finding(
                    check_id="act.context.no_onward_path",
                    title="The visitor reaches the end of this page with nowhere to go",
                    severity="medium", confidence="confirmed", stage="act",
                    category="engagement", scope="url",
                    evidence=(
                        f"{page['url']} (page type {page_type}, {len(text.split())} words of "
                        f"observed content) contains {len(in_main)} internal link(s) inside its "
                        f"main content, below the floor of {min_onward}. Navigation and footer "
                        f"links were excluded because they are the same on every page and are not "
                        f"this page's suggestion of what to read next. "
                        f"{'Links present: ' + ', '.join(in_main) if in_main else 'No in-content internal links at all.'}"
                    ),
                    affected_urls=[page["url"]],
                    action=action(
                        summary="Add two or three in-content links to the obvious next pages.",
                        effort="low",
                        mechanism=(
                            "A visitor who finishes the content and sees only global navigation has "
                            "to restart their own search; an in-content link continues the journey "
                            "they were already on."
                        ),
                        source="references/cro-frameworks.md",
                        patch=_onward_patch(b, page),
                        verification=f"Open {page['url']}, scroll to the end: is there a suggested next page?",
                    ),
                ))

        # ------------------------------------------- assumes prior context
        if not gate.page_allowed("act.context.assumes_prior_context", page):
            skipped.append(_skip("act.context.assumes_prior_context", page))
            continue

        offenders = []
        for block in _blocks(text):
            ok, why = self_contained(block)
            if ok:
                continue
            if "unresolved reference" in why and _resolvable_earlier(block, text):
                continue
            offenders.append((block, why))

        if not offenders:
            continue
        quoted = "; ".join(f'"{b_[:110]}" ({why})' for b_, why in offenders[:3])
        findings.append(finding(
            check_id="act.context.assumes_prior_context",
            title=f"{len(offenders)} passage(s) assume context a first-time visitor does not have",
            severity="medium", confidence="likely", stage="act",
            category="engagement", scope="url",
            evidence=(
                f"{page['url']}: {quoted}. Most visitors arrive on a deep page from search or a "
                f"shared link with no prior session, so copy written for someone mid-journey "
                f"reads as though they have missed something."
            ),
            affected_urls=[page["url"]],
            action=action(
                summary="Rewrite these passages so they stand on their own for a first-time reader.",
                effort="low",
                mechanism=(
                    "A reference to state the visitor does not hold cannot be resolved, so the "
                    "sentence carries no information and signals the page was not meant for them."
                ),
                source="Handout appendix, Personalization and prior context",
                patch="\n".join(
                    f"<!-- was: {b_[:90]} -->\n<p>__FILL_IN__:restate_without_assuming_prior_context</p>"
                    for b_, _ in offenders[:3]
                ),
                verification="Read each passage cold, as a stranger: does it depend on something you were never told?",
            ),
        ))

    limitation = gate.limitation()
    return findings, skipped, ([limitation] if limitation else [])


def _blocks(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if len(s.strip()) > 30]


def _resolvable_earlier(block: str, text: str) -> bool:
    """A pronoun opener is fine if a named subject appears shortly before it."""
    idx = text.find(block[:40])
    if idx <= 0:
        return False
    preceding = text[max(0, idx - 320):idx]
    return bool(re.search(r"[A-Z][a-z]{2,}", preceding))


def _onward_patch(b, page: dict) -> str:
    candidates = [
        p for p in b.html_pages()
        if p["url"] != page["url"] and p.get("title") and p.get("main_wordcount", 0) > 60
    ]
    candidates.sort(key=lambda p: p["url"])
    if not candidates:
        return '<p>Next: <a href="__FILL_IN__:next_page_url">__FILL_IN__:next_page_title</a></p>'
    lines = ["<nav aria-label=\"Next steps\">", "  <p>Next:</p>", "  <ul>"]
    for p in candidates[:3]:
        lines.append(f'    <li><a href="{p["url"]}">{p["title"]}</a></li>')
    lines += ["  </ul>", "</nav>"]
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
