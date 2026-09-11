#!/usr/bin/env python3
"""Stage act: can a first-time visitor tell what this is and where they are?"""

from __future__ import annotations

import re

from bundle import action, finding

CHECKS = [
    {"id": "act.orient.no_value_proposition", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "high", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
    {"id": "act.orient.no_wayfinding", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
]

# Page types where an above-fold value proposition is not the idiom.
# Page types whose job is not to pitch: an About page describes the company,
# a Contact page gives contact details, an article delivers its content.
# A pricing page states cost, not audience; an About page describes the
# company; a Contact page gives contact details; an article delivers its
# content. The audience-and-outcome sentence is a homepage and product-page
# idiom, and testing for it elsewhere fired on the healthy control fixture.
NO_VALUE_PROP_TYPES = {"utility", "article", "docs", "category", "contact", "about", "pricing"}
NO_WAYFINDING_TYPES = {"home", "utility"}

STOPWORDS = frozenset(
    "the a an and or of to for in on at is are we our you your with by from that this it "
    "us be as more all can will has have new get make take just its their".split()
)

# A value proposition names an audience or an outcome. Pure welcome copy does not.
VAGUE_OPENERS = re.compile(
    r"^\s*(welcome|hello|hi there|about us|home|introducing us|our website)\b", re.I
)
AUDIENCE_HINT = re.compile(
    r"\b(for |helps? |help you|built for|built to|designed for|designed to|made for|made to|"
    r"used by|trusted by|lets you|let you|so you can|gives you|give you|we help|"
    r"is a |is an |is the |are a |are the |meet the|join the|"
    r"tools? (for|to)|software (for|to)|platform (for|to)|system for)\b",
    re.I,
)


def content_tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in STOPWORDS and len(w) > 2}


def first_sentences(text: str, limit_chars: int = 400) -> list[str]:
    head = (text or "")[:limit_chars]
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", head) if s.strip()]


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    from gating import Rule0b

    gate = Rule0b(b)
    findings: list[dict] = []
    skipped: list[dict] = []

    for page in b.html_pages():
        page_type = b.page_type(page, profile)
        text = b.observed_text(page)
        h1s = (page.get("headings") or {}).get("h1") or []

        # ------------------------------------------------ value proposition
        if page_type in NO_VALUE_PROP_TYPES:
            pass
        elif not gate.page_allowed("act.orient.no_value_proposition", page):
            skipped.append(_rule0b_skip("act.orient.no_value_proposition", page))
        else:
            head = text[:400]
            sentences = first_sentences(text)
            has_prop = bool(AUDIENCE_HINT.search(head)) and not VAGUE_OPENERS.match(head)
            if not has_prop and len(text.split()) >= 30:
                quoted = " | ".join(f'"{s[:110]}"' for s in sentences[:3]) or "(no sentences in the first screen)"
                findings.append(finding(
                    check_id="act.orient.no_value_proposition",
                    title="The first screen never says who this is for or what it does",
                    severity="high", confidence="likely", stage="act",
                    category="engagement", scope="url",
                    evidence=(
                        f"{page['url']} (page type {page_type}). H1 is "
                        f"{(h1s[0] if h1s else '(none)')!r}. The first 400 characters of observed "
                        f"content read: {quoted}. None of these names an audience or an outcome - "
                        f"no phrase of the form \"for <who>\", \"helps <who> <do what>\", or "
                        f"\"<product> is a <category>\" appears. A first-time visitor has to infer "
                        f"what this is."
                    ),
                    affected_urls=[page["url"]],
                    action=action(
                        summary="Open with one sentence naming the audience and the outcome.",
                        effort="low",
                        mechanism=(
                            "A visitor decides whether to stay from the first screen; without a "
                            "sentence that names them, they have to do the work of inferring "
                            "relevance, and most leave instead."
                        ),
                        source="references/cro-frameworks.md",
                        patch=(
                            f"<h1>{h1s[0] if h1s else '__FILL_IN__:what_this_page_is'}</h1>\n"
                            f"<p>__FILL_IN__:product_name is __FILL_IN__:category for "
                            f"__FILL_IN__:audience. It __FILL_IN__:primary_outcome.</p>"
                        ),
                        verification=(
                            f"Open {page['url']} and read only the first screen: can a stranger say "
                            f"who it is for and what it does?"
                        ),
                    ),
                ))

        # act.orient.h1_cta_mismatch was CUT during S4. See the note at the
        # bottom of this file: it could not earn a negative fixture.

        # ------------------------------------------------------ wayfinding
        depth = len([s for s in page["url"].split("://")[-1].split("/")[1:] if s])
        if depth < 2 or page_type in NO_WAYFINDING_TYPES:
            continue
        if not gate.page_allowed("act.orient.no_wayfinding", page):
            skipped.append(_rule0b_skip("act.orient.no_wayfinding", page))
            continue
        has_breadcrumb = _has_breadcrumb(page, text)
        ancestors = _ancestor_links(page)
        if has_breadcrumb or ancestors:
            continue
        findings.append(finding(
            check_id="act.orient.no_wayfinding",
            title="A deep page offers no path back to its parent section",
            severity="medium", confidence="likely", stage="act",
            category="engagement", scope="url",
            evidence=(
                f"{page['url']} sits {depth} levels deep. No BreadcrumbList structured data and no "
                f"breadcrumb navigation landmark was found, and none of its "
                f"{len((page.get('links') or {}).get('internal', []))} internal links point to an "
                f"ancestor path. A visitor arriving here from search or a shared link has no way "
                f"to see where they are or move up."
            ),
            affected_urls=[page["url"]],
            action=action(
                summary="Add a breadcrumb trail linking each ancestor section.",
                effort="low",
                mechanism=(
                    "Most visitors to a deep page arrive from outside, not from the homepage; "
                    "without an upward path the page is a dead end regardless of its content."
                ),
                source="references/cro-frameworks.md",
                patch=_breadcrumb_patch(page),
                verification=f"curl -s {page['url']} | grep -i 'breadcrumb'",
            ),
        ))

    limitation = gate.limitation()
    return findings, skipped, ([limitation] if limitation else [])


def _rule0b_skip(check_id: str, page: dict) -> dict:
    return {
        "check_id": check_id,
        "reason": (
            f"{page['url']} serves an unhydrated shell and no rendered DOM was captured, so the "
            f"visible content a visitor sees was never observed. Suppressed entirely under gate "
            f"Rule 0b rather than reported at reduced confidence."
        ),
        "confidence_effect": "suppressed entirely",
    }


CTA_TAGS_TEXT = re.compile(r"\b(sign up|get started|start|buy|order|book|request|download|subscribe|"
                           r"contact|try|demo|quote|apply|register|add to|checkout|submit|send|"
                           r"learn more|read more|continue|next|join)\b", re.I)


def ctas(page: dict) -> list[dict]:
    """Actionable elements ranked by prominence.

    Prominence heuristic, stated so it can be argued with: an anchor whose text
    reads as an action, in the main content, ranks above the same text in
    navigation or footer chrome, because chrome repeats on every page and is not
    this page's call to action.
    """
    out = []
    for anchor in page.get("anchors") or []:
        text = (anchor.get("text") or "").strip()
        if not text or len(text) > 60:
            continue
        if not CTA_TAGS_TEXT.search(text):
            continue
        out.append({
            "text": text,
            "href": anchor.get("href", ""),
            "in_main": bool(anchor.get("in_main")),
            "in_chrome": bool(anchor.get("in_chrome")),
            "kind": "anchor",
        })
    out.sort(key=lambda c: (not c["in_main"], c["in_chrome"], c["text"]))
    return out


def _ctas(page: dict) -> list[dict]:
    return ctas(page)


def _has_breadcrumb(page: dict, text: str) -> bool:
    import json

    markup = page.get("markup") or {}
    try:
        blob = json.dumps(markup.get("jsonld") or [])
    except (TypeError, ValueError):
        blob = ""
    if "BreadcrumbList" in blob:
        return True
    return bool(re.search(r"breadcrumb", json.dumps(page.get("headings") or {}), re.I))


def _ancestor_links(page: dict) -> list[str]:
    url = page["url"]
    parts = url.split("://", 1)[-1]
    host, _, path = parts.partition("/")
    segments = [s for s in path.split("/") if s]
    ancestors = set()
    scheme = url.split("://", 1)[0]
    for i in range(len(segments)):
        ancestors.add(f"{scheme}://{host}/" + "/".join(segments[:i]))
        ancestors.add(f"{scheme}://{host}/" + "/".join(segments[:i]) + "/")
    internal = set((page.get("links") or {}).get("internal", []))
    return sorted(internal & ancestors)


def _breadcrumb_patch(page: dict) -> str:
    url = page["url"]
    scheme, _, rest = url.partition("://")
    host, _, path = rest.partition("/")
    segments = [s for s in path.split("/") if s]
    items = []
    crumbs = [(f"{scheme}://{host}/", "Home")]
    acc = ""
    for seg in segments[:-1]:
        acc += "/" + seg
        crumbs.append((f"{scheme}://{host}{acc}", seg.replace("-", " ").title()))
    for i, (href, name) in enumerate(crumbs, start=1):
        items.append(
            '    {"@type": "ListItem", "position": %d, "name": "%s", "item": "%s"}' % (i, name, href)
        )
    nav = " &rsaquo; ".join(f'<a href="{href}">{name}</a>' for href, name in crumbs)
    return (
        f'<nav aria-label="Breadcrumb">{nav} &rsaquo; <span>__FILL_IN__:this_page_title</span></nav>\n\n'
        '<script type="application/ld+json">\n'
        '{\n  "@context": "https://schema.org",\n  "@type": "BreadcrumbList",\n  "itemListElement": [\n'
        + ",\n".join(items)
        + "\n  ]\n}\n</script>"
    )


# ---------------------------------------------------------------------------
# CUT CHECK: act.orient.h1_cta_mismatch
#
# Design: flag a page whose primary call to action shares no content word with
# its H1, on the theory that the action should continue the headline's promise.
#
# Why it was cut, on evidence, during S4: it fired on 7 of 8 pages of the
# healthy control fixture, including the homepage, where the pairing is
# CORRECT. H1 "Pipeline monitoring for data engineering teams" and CTA "Start a
# 14-day trial" share no token because a headline names a category and a call
# to action names an action. That is good copywriting, not a defect. Token
# overlap does not measure whether an action follows from a promise, and no
# threshold rescues it: the check has no negative fixture it can pass.
#
# Under the standing quality gate - no check ships without a positive fixture,
# a negative fixture, and both suppression assertions - this one does not ship.
# Recorded here rather than deleted silently so the reasoning survives.
# ---------------------------------------------------------------------------
