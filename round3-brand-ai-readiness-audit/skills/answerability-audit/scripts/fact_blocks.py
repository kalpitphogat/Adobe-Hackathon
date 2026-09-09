#!/usr/bin/env python3
"""Stage extract: is the page's answer findable in its structure?"""

from __future__ import annotations

import re

from bundle import action, finding, threshold, typed_threshold
from retrievability_sim import derive_entity, tokens

CHECKS = [
    {"id": "extract.ans.no_direct_answer_block", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "answerability-audit"},
    {"id": "extract.ans.title_not_entity_bearing", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "answerability-audit"},
    {"id": "extract.ans.heading_structure_unusable", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "low", "skill": "answerability-audit"},
    {"id": "extract.ans.boilerplate_dominant", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "answerability-audit"},
    {"id": "extract.ans.thin_content_for_page_type", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "answerability-audit"},
]

GENERIC_TITLES = re.compile(
    r"^\s*(home|homepage|index|untitled|welcome|page|new page|document|site|main)\s*$", re.I
)
# A definitional sentence does not need an article: "X is monitoring software for
# data teams" defines X just as well as "X is a monitoring tool". Requiring the
# article fired on four pages of the healthy control fixture.
DEFINITIONAL = re.compile(
    r"\b(is|are|provides|offers|helps|lets you|enables|delivers|means|specialises|specializes)\b",
    re.I,
)
# First-person self-description names the entity as surely as using its name.
# "We make analog tools for a distracted world" defines the subject; requiring
# the literal brand string rejected it.
FIRST_PERSON_DEF = re.compile(
    r"\bwe\s+(are|make|build|design|create|help|provide|offer|publish|sell|run|develop)\b", re.I
)

NO_DIRECT_ANSWER_TYPES = {"category", "utility", "contact"}
LISTING_TYPES = {"category", "utility"}


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []
    max_answer_words = threshold(profile, "direct_answer_max_words", 50)
    max_boiler = threshold(profile, "boilerplate_ratio_max", 0.7)

    for page in b.html_pages():
        page_type = b.page_type(page, profile)
        text = b.observed_text(page)
        headings = page.get("headings") or {}
        h1s = headings.get("h1") or []
        title = (page.get("title") or "").strip()
        entity = derive_entity(b, page)
        words = len(tokens(text))

        # ------------------------------------------------- thin content
        floor = typed_threshold(profile, "thin_content_words", page_type, 150) or 150
        internal_in_main = len((page.get("links") or {}).get("internal_in_main") or [])
        hub_min = threshold(profile, "internal_links_hub_min", 15)
        if page_type in LISTING_TYPES:
            pass
        elif internal_in_main >= hub_min:
            skipped.append({
                "check_id": "extract.ans.thin_content_for_page_type",
                "reason": (
                    f"{page['url']}: {words} words is below the {floor}-word floor, but the page "
                    f"carries {internal_in_main} in-content internal links, so it is a hub whose "
                    f"value is its links rather than its prose."
                ),
                "confidence_effect": "suppressed by design",
            })
        elif words < floor and words > 0:
            findings.append(finding(
                check_id="extract.ans.thin_content_for_page_type",
                title=f"A {page_type} page carries only {words} words",
                severity="medium", confidence="confirmed", stage="extract",
                category="discoverability", scope="url",
                evidence=(
                    f"{page['url']} has {words} words of main content against a floor of {floor} "
                    f"for a {page_type} page on a {(profile or {}).get('archetype', 'unknown')} "
                    f"site. Navigation, header and footer were excluded from the count. There is "
                    f"not enough here for a retrieval system to find an answer to anything "
                    f"specific."
                ),
                affected_urls=[page["url"]],
                action=action(
                    summary="Answer the questions a visitor arrives with, in specifics.",
                    effort="medium",
                    mechanism=(
                        "A page with little text offers few facts to extract, so it is rarely the "
                        "best available source for any question."
                    ),
                    source="references/geo-methods.md",
                    patch=(
                        f"<h2>__FILL_IN__:question_visitors_actually_ask</h2>\n"
                        f"<p>{entity or '__FILL_IN__:subject'} __FILL_IN__:specific_answer_with_a_number_or_name.</p>"
                    ),
                    verification=f"curl -s {page['url']} | sed -e 's/<[^>]*>//g' | wc -w",
                ),
            ))

        # ---------------------------------------------------- title
        if page_type == "utility":
            pass
        elif not title or GENERIC_TITLES.match(title) or len(title) < 15:
            findings.append(finding(
                check_id="extract.ans.title_not_entity_bearing",
                title=f"The page title is {title!r}, which does not say what the page is about",
                severity="medium", confidence="confirmed", stage="extract",
                category="discoverability", scope="url",
                evidence=(
                    f"{page['url']} has <title>{title}</title> ({len(title)} characters). "
                    + (
                        "It is empty." if not title
                        else "It is a generic template value." if GENERIC_TITLES.match(title)
                        else "It is too short to carry both the subject and a descriptor."
                    )
                    + f" The H1 says {(h1s[0] if h1s else '(no H1)')!r}. The title is the strongest "
                      f"single signal of what a page is about, and it is often the only text shown "
                      f"beside a citation."
                ),
                affected_urls=[page["url"]],
                action=action(
                    summary="Write a title that names the subject and what the page says about it.",
                    effort="low",
                    mechanism=(
                        "The title is used as the page's label wherever it is referenced, so a "
                        "generic title makes the page indistinguishable from every other page."
                    ),
                    source="references/geo-methods.md",
                    patch=(
                        f"<title>{h1s[0] if h1s else '__FILL_IN__:subject'} "
                        f"— __FILL_IN__:what_this_page_says_about_it</title>"
                    ),
                    verification=f"curl -s {page['url']} | grep -o '<title>[^<]*</title>'",
                ),
            ))

        # ------------------------------------------- direct answer block
        if page_type in NO_DIRECT_ANSWER_TYPES or words < 80:
            pass
        else:
            paragraphs = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text[:900]) if p.strip()]
            def _names_subject(p: str) -> bool:
                if FIRST_PERSON_DEF.search(p):
                    return True
                if not entity:
                    return True
                return entity.lower().split()[0] in p.lower()

            has_answer = any(
                DEFINITIONAL.search(p) and len(tokens(p)) <= max_answer_words and _names_subject(p)
                for p in paragraphs[:5]
            )
            schema_desc = (page.get("meta_description") or "")
            if has_answer:
                pass
            elif schema_desc and DEFINITIONAL.search(schema_desc):
                skipped.append({
                    "check_id": "extract.ans.no_direct_answer_block",
                    "reason": (
                        f"{page['url']}: no definitional sentence in the first screen, but the "
                        f"meta description supplies one, so the fact is machine-available."
                    ),
                    "confidence_effect": "suppressed by design",
                })
            else:
                quoted = " | ".join(f'"{p[:100]}"' for p in paragraphs[:3]) or "(no sentences)"
                findings.append(finding(
                    check_id="extract.ans.no_direct_answer_block",
                    title=f"Nothing near the top of the page states plainly what {entity or 'this'} is",
                    severity="medium", confidence="likely", stage="extract",
                    category="discoverability", scope="url",
                    evidence=(
                        f"{page['url']}: the first five sentences are {quoted}. None is a "
                        f"definitional statement of at most {max_answer_words} words that names "
                        f"{entity!r} and says what it is. A system answering \"what is "
                        f"{entity or 'this'}\" has nothing short and quotable to lift."
                    ),
                    affected_urls=[page["url"]],
                    action=action(
                        summary=f"Open with one sentence of the form \"{entity or 'X'} is a … that …\".",
                        effort="low",
                        mechanism=(
                            "A short definitional sentence is directly quotable as an answer; a "
                            "reader that has to synthesise one from scattered prose usually picks "
                            "a source that did the work."
                        ),
                        source="references/geo-methods.md",
                        patch=(
                            f"<p>{entity or '__FILL_IN__:subject'} is "
                            f"__FILL_IN__:category that __FILL_IN__:what_it_does_for_whom.</p>"
                        ),
                        verification=(
                            f"Read the first two sentences of {page['url']}: do they answer "
                            f"\"what is this?\" without further reading?"
                        ),
                    ),
                ))

        # -------------------------------------------- heading structure
        levels = [(int(tag[1]), h) for tag in ("h1", "h2", "h3", "h4", "h5", "h6")
                  for h in (headings.get(tag) or [])]
        problems = []
        if not h1s:
            problems.append("no H1")
        if words > 800 and not (headings.get("h2") or []):
            problems.append(f"{words} words with no H2 to divide it")
        present_levels = sorted({lvl for lvl, _ in levels})
        for a, c in zip(present_levels, present_levels[1:]):
            if c - a > 1:
                problems.append(f"heading levels skip from h{a} to h{c}")
                break
        if len(h1s) > 1:
            skipped.append({
                "check_id": "extract.ans.heading_structure_unusable",
                "reason": (
                    f"{page['url']} has {len(h1s)} H1 elements. Multiple H1s are valid in HTML5 "
                    f"sectioning contexts and are recorded as an observation, never an error."
                ),
                "confidence_effect": "reported as info, not a defect",
            })
        if problems and page_type != "utility":
            findings.append(finding(
                check_id="extract.ans.heading_structure_unusable",
                title="The heading outline does not divide this page usefully",
                severity="low", confidence="confirmed", stage="extract",
                category="discoverability", scope="url",
                evidence=(
                    f"{page['url']}: " + "; ".join(problems)
                    + ". Outline: "
                    + (", ".join(f"h{lvl}:{h[:40]!r}" for lvl, h in levels[:8]) or "(no headings)")
                    + ". Headings are where a reader decides which part of a page answers the "
                      "question, so an outline that does not divide the content leaves it to guess."
                ),
                affected_urls=[page["url"]],
                action=action(
                    summary="Give the page one H1 and H2 sections that name what each part answers.",
                    effort="low",
                    mechanism=(
                        "Headings mark the boundaries a reader uses to locate the relevant part of "
                        "a long page; without them the whole page is one undifferentiated block."
                    ),
                    source="references/chunking-model.md",
                    patch=(
                        f"<h1>{h1s[0] if h1s else '__FILL_IN__:page_subject'}</h1>\n"
                        "<h2>__FILL_IN__:question_this_section_answers</h2>"
                    ),
                    verification=f"curl -s {page['url']} | grep -oE '<h[1-3][^>]*>' | sort | uniq -c",
                ),
            ))

        # ------------------------------------------------- boilerplate
        ratio = page.get("boilerplate_ratio")
        if ratio is None or words < 300 or page_type in LISTING_TYPES:
            continue
        if ratio > max_boiler:
            findings.append(finding(
                check_id="extract.ans.boilerplate_dominant",
                title=f"Navigation and chrome are {ratio:.0%} of this page's text",
                severity="medium", confidence="likely", stage="extract",
                category="discoverability", scope="url",
                evidence=(
                    f"{page['url']}: main content is {page.get('main_wordcount')} words of "
                    f"{page.get('wordcount')} total, so {ratio:.0%} of the page's text is "
                    f"navigation, header and footer against a ceiling of {max_boiler:.0%}. "
                    f"Repeated chrome dilutes the page's actual subject."
                ),
                affected_urls=[page["url"]],
                action=action(
                    summary="Reduce repeated chrome, or wrap the real content in <main>.",
                    effort="medium",
                    mechanism=(
                        "A reader that cannot tell chrome from content treats both as the page's "
                        "subject, so the page appears to be about its own navigation."
                    ),
                    source="references/chunking-model.md",
                    patch="<main>\n  <!-- the page's actual content only -->\n</main>",
                    verification=f"curl -s {page['url']} | grep -c '<main'",
                ),
            ))

    return findings, skipped, []
