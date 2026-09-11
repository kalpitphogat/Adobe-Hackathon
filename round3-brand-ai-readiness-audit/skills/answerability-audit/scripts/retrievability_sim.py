#!/usr/bin/env python3
"""Stage extract: would a retriever be able to lift a fact off this page and quote it?

WHAT THIS IS, AND WHAT IT IS NOT
--------------------------------
This is our operationalisation of the handout appendix subsection "How
assistants like ChatGPT use sources", which observes that the pages chosen as
sources "tend to be the ones a machine could easily reach, easily read, and
easily quote a clear fact from".

The handout says nothing about chunking. The chunking model here is standard
retrieval practice, not something the task asserted, and it is stated as our
own modelling choice rather than dressed up as a requirement.

CRITICAL CONSTRAINT ON THE FIX
------------------------------
Google Search Central states: "There's no requirement to break your content into
tiny pieces for AI to better understand it." So this check must NEVER recommend
chunking, fragmenting, or restructuring content into small blocks. It models how
a retriever might segment text in order to find where self-containment breaks;
the fix is always to make the prose self-contained, never to chop it up. Any
future edit that turns this into chunking advice contradicts primary guidance.
See references/chunking-model.md.

Method
------
1. Take the page as a no-JS crawler sees it (raw main text unless we rendered).
2. Segment into overlapping windows of about 300 tokens with 15% overlap.
3. Derive the page's claimed key facts from title, H1, hero copy and schema
   property values. Derived, never hardcoded, so this generalises to sites we
   have never seen.
4. Test whether each fact survives inside at least one SELF-CONTAINED window: a
   window that still makes sense lifted out, with no unresolved pronoun opener,
   no backward reference, and the entity named inside the window itself.
5. Report fact_coverage as N/M with the misses named and quoted.
"""

from __future__ import annotations

import re

from bundle import action, finding, threshold

CHECKS = [
    {"id": "extract.ans.fact_coverage_gap", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "high", "skill": "answerability-audit"},
    {"id": "extract.ans.chunk_not_self_contained", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "answerability-audit",
     "deduped_into": "extract.ans.fact_coverage_gap"},
]

PRONOUN_OPENER = re.compile(r"^\s*(it|this|that|they|these|those|he|she|there|such)\b", re.I)
# Interface furniture that appears as a heading on many templates. These are
# controls, not claims, and treating them as claims manufactured findings on
# every e-commerce page we audited.
CHROME_HEADING = re.compile(
    r"^\s*(your cart|cart|shopping bag|country\s*/\s*region|region|language|currency|"
    r"menu|navigation|search|newsletter|subscribe|follow us|share|filters?|sort by|"
    r"skip to|breadcrumb|pagination|cookie|consent|footer|header|related|you may also like|"
    r"recently viewed|quick view|close|back to top)\b",
    re.I,
)
BACKREF = re.compile(
    r"\b(as (mentioned|described|explained|noted|discussed) (above|earlier|previously)"
    r"|see above|the (above|aforementioned|former|latter)|as we saw)\b",
    re.I,
)
STOPWORDS = frozenset(
    "the a an and or of to for in on at is are was were be been being we our you your with by "
    "from that this it its their they them he she as more all can will has have had do does did "
    "not no so if than then there here what which who whom whose when where why how".split()
)


def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-]*", text or "")


def chunk(text: str, target: int = 300, overlap_ratio: float = 0.15) -> list[str]:
    """Segment into overlapping windows on sentence boundaries.

    Modelling only. This does NOT imply the page should be written in short
    blocks; see the constraint in the module docstring.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]
    if not sentences:
        return []
    windows: list[str] = []
    current: list[str] = []
    count = 0
    overlap_tokens = max(1, int(target * overlap_ratio))
    for sentence in sentences:
        n = len(tokens(sentence))
        if count + n > target and current:
            windows.append(" ".join(current))
            back: list[str] = []
            taken = 0
            for prev in reversed(current):
                back.insert(0, prev)
                taken += len(tokens(prev))
                if taken >= overlap_tokens:
                    break
            current = back
            count = taken
        current.append(sentence)
        count += n
    if current:
        windows.append(" ".join(current))
    return windows


def self_contained(window: str, entity: str | None) -> tuple[bool, str]:
    """Does this window still make sense lifted out of the page?"""
    stripped = (window or "").strip()
    if not stripped:
        return False, "empty"
    if PRONOUN_OPENER.match(stripped):
        return False, f"opens with the unresolved reference {stripped.split()[0]!r}"
    m = BACKREF.search(stripped)
    if m:
        return False, f"refers backwards to text outside itself via {m.group(0)!r}"
    if entity:
        # Match on a DISTINCTIVE token rather than the whole literal string. A
        # schema name like "Northwind Analytics Team" never appears verbatim in
        # prose that says "Northwind Analytics"; demanding the full string made
        # every window fail on a perfectly self-contained page.
        distinctive = [t.lower() for t in tokens(entity)
                       if t.lower() not in STOPWORDS and len(t) > 3]
        haystack = stripped.lower()
        if distinctive and not any(t in haystack for t in distinctive):
            return False, f"never names {entity!r} or any distinctive part of it inside the window"
    return True, "self-contained"


def _tidy_entity(value: str | None) -> str | None:
    """An entity is a NAME, not a headline.

    Live sites produced a 100-character duplicated hero string and a full
    article title as 'the entity'. Downstream checks then looked for a sentence
    naming that exact string, which no page could satisfy.
    """
    if not value:
        return None
    value = re.sub(r"\s+", " ", value).strip(" -|:\u2013\u2014")
    # Collapse an immediately repeated phrase, which is what a duplicated hero
    # heading looks like once the tags are stripped.
    half = len(value) // 2
    if half > 8 and value[:half].strip().lower() == value[half:].strip().lower():
        value = value[:half].strip()
    if len(value) > 60 or len(tokens(value)) > 8:
        return None
    return value or None


def derive_entity(b, page: dict) -> str | None:
    """The thing this page is about, from schema name, then H1, then title."""
    import json

    markup = page.get("markup") or {}
    try:
        blob = markup.get("jsonld") or []
        stack = list(blob) if isinstance(blob, list) else [blob]
        while stack:
            node = stack.pop(0)
            if isinstance(node, dict):
                for key in ("name", "legalName"):
                    value = node.get(key)
                    tidy = _tidy_entity(value) if isinstance(value, str) else None
                    if tidy:
                        return tidy
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
            elif isinstance(node, list):
                stack.extend(node)
    except (TypeError, ValueError):
        pass
    # A site-wide brand name beats a per-page headline. On live sites the H1
    # produced entities like a duplicated 100-character hero string and a full
    # article title, and downstream checks then demanded a sentence naming that
    # exact string, which no page could satisfy.
    brand = _tidy_entity(_site_brand(b))
    if brand:
        return brand
    h1s = (page.get("headings") or {}).get("h1") or []
    tidy = _tidy_entity(h1s[0]) if h1s else None
    if tidy:
        return tidy
    title = (page.get("title") or "").strip()
    for sep in (" — ", " – ", " | ", " - "):
        if sep in title:
            parts = [p for p in (title.split(sep)) if p.strip()]
            return _tidy_entity(parts[-1]) or _tidy_entity(parts[0])
    return _tidy_entity(title)


def _site_brand(b) -> str | None:
    """The brand this whole site belongs to, taken from the homepage title."""
    home = next(
        (p for p in b.html_pages() if p["url"].rstrip("/") == b.origin.rstrip("/")), None
    )
    if not home:
        return None
    title = (home.get("title") or "").strip()
    for sep in (" — ", " – ", " | ", " - "):
        if sep in title:
            parts = [p.strip() for p in title.split(sep) if p.strip()]
            if parts:
                return min(parts, key=len)
    return title or None


def derive_facts(b, page: dict) -> list[dict]:
    """The claims this page makes about itself, derived not hardcoded."""
    facts: list[dict] = []
    seen: set[str] = set()

    def add(source: str, claim: str) -> None:
        claim = re.sub(r"\s+", " ", claim or "").strip()
        key = claim.lower()
        if not claim or len(claim) < 8 or key in seen:
            return
        # A claim must be a statement, not a UI label. On a live storefront the
        # H2s included "Country/Region" and "Your cart is empty" - chrome from a
        # region selector and a cart drawer, not anything the page asserts.
        if CHROME_HEADING.search(claim):
            return
        content_words = [t for t in tokens(claim) if t.lower() not in STOPWORDS]
        if len(content_words) < 3:
            return
        seen.add(key)
        facts.append({"source": source, "claim": claim})

    title = page.get("title") or ""
    for sep in (" — ", " – ", " | ", " - "):
        if sep in title:
            for part in title.split(sep):
                add("title", part)
            break
    else:
        add("title", title)

    for h1 in ((page.get("headings") or {}).get("h1") or [])[:2]:
        add("h1", h1)
    for h2 in ((page.get("headings") or {}).get("h2") or [])[:4]:
        add("h2", h2)
    if page.get("meta_description"):
        add("meta description", page["meta_description"])

    # schema property values are the site's own machine-readable claims
    import json

    def walk(node) -> None:
        if isinstance(node, dict):
            for key in ("name", "headline", "description", "slogan"):
                v = node.get(key)
                if isinstance(v, str):
                    add(f"schema {key}", v)
            offers = node.get("offers")
            if isinstance(offers, dict):
                price, cur = offers.get("price"), offers.get("priceCurrency")
                if price:
                    add("schema offers.price", f"{price} {cur or ''}".strip())
            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk((page.get("markup") or {}).get("jsonld") or [])
    return facts[:12]


def fact_supported(fact: dict, windows: list[str], entity: str | None) -> tuple[bool, str]:
    """Does at least one SELF-CONTAINED window carry this fact?"""
    claim_tokens = {t.lower() for t in tokens(fact["claim"]) if t.lower() not in STOPWORDS}
    if not claim_tokens:
        return True, "no content tokens to test"
    best_reason = "no window contains the claim at all"
    for window in windows:
        window_tokens = {t.lower() for t in tokens(window)}
        overlap = len(claim_tokens & window_tokens) / len(claim_tokens)
        if overlap < 0.6:
            continue
        ok, why = self_contained(window, entity)
        if ok:
            return True, "carried by a self-contained window"
        best_reason = f"the only window carrying it {why}"
    return False, best_reason


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []
    target = threshold(profile, "chunk_target_tokens", 300)
    overlap = threshold(profile, "chunk_overlap_ratio", 0.15)

    for page in b.html_pages():
        page_type = b.page_type(page, profile)
        if page_type == "utility":
            continue
        text = page.get("main_text") or ""
        if page.get("rendered_available") and page.get("rendered_text"):
            text = page["rendered_text"]

        entity = derive_entity(b, page)
        facts = derive_facts(b, page)
        windows = chunk(text, target, overlap)

        if len(facts) < 2 or not windows:
            skipped.append({
                "check_id": "extract.ans.fact_coverage_gap",
                "reason": (
                    f"{page['url']}: only {len(facts)} derivable claim(s) and {len(windows)} "
                    f"window(s); too sparse to judge answerability without inventing a standard."
                ),
                "confidence_effect": "not assessed",
            })
            continue

        misses = []
        for fact in facts:
            ok, why = fact_supported(fact, windows, entity)
            if not ok:
                misses.append((fact, why))

        covered = len(facts) - len(misses)
        if misses:
            quoted = "; ".join(
                f'"{f["claim"][:90]}" (from {f["source"]}) - {why}' for f, why in misses[:4]
            )
            findings.append(finding(
                check_id="extract.ans.fact_coverage_gap",
                title=f"fact_coverage {covered}/{len(facts)}: {len(misses)} claim(s) cannot be quoted from this page",
                severity="high" if len(misses) >= len(facts) / 2 else "medium",
                confidence="likely", stage="extract",
                category="discoverability", scope="url",
                evidence=(
                    f"{page['url']}: the page makes {len(facts)} derivable claims about "
                    f"{entity!r}. Segmenting the {len(tokens(text))} words a no-JS reader sees into "
                    f"{len(windows)} overlapping windows of about {target} tokens, "
                    f"{covered} of {len(facts)} claims survive inside at least one window that "
                    f"still makes sense on its own. The misses: {quoted}."
                ),
                affected_urls=[page["url"]],
                action=action(
                    summary=(
                        "State each key claim in a sentence that names the subject and stands on "
                        "its own. Do NOT split the page into smaller blocks."
                    ),
                    effort="low",
                    mechanism=(
                        "A passage that is quoted away from its page loses whatever its pronouns "
                        "and back-references pointed at, so a claim that depends on them cannot be "
                        "reproduced as an answer."
                    ),
                    source=(
                        "Handout appendix, How assistants like ChatGPT use sources; "
                        "Aggarwal et al., GEO: Generative Engine Optimization, KDD 2024 "
                        "(arXiv:2311.09735)"
                    ),
                    patch=_rewrite_patch(entity, misses),
                    verification=(
                        "Copy any single paragraph out of the page and read it cold: does it still "
                        "name what it is about, without the paragraphs around it?"
                    ),
                ),
            ))

        # supporting check; the orchestrator dedupes it into the above
        failing = [(w, self_contained(w, entity)) for w in windows]
        bad = [(w, why) for w, (ok, why) in failing if not ok]
        if bad and len(bad) / len(windows) >= 0.2 and len(windows) >= 3:
            findings.append(finding(
                check_id="extract.ans.chunk_not_self_contained",
                title=f"{len(bad)} of {len(windows)} passages do not stand on their own",
                severity="medium", confidence="likely", stage="extract",
                category="discoverability", scope="url",
                evidence=(
                    f"{page['url']}: {len(bad)}/{len(windows)} windows ({len(bad)/len(windows):.0%}) "
                    f"fail the self-containment test. "
                    + "; ".join(f'"{w[:80]}" - {why}' for w, why in bad[:3])
                ),
                affected_urls=[page["url"]],
                action=action(
                    summary="Name the subject in each paragraph rather than relying on the one before it.",
                    effort="low",
                    mechanism=(
                        "An opening pronoun resolves to something outside the passage, so the "
                        "passage carries no recoverable subject once separated."
                    ),
                    source="references/chunking-model.md",
                    patch=(
                        f"<!-- was: {bad[0][0][:80]} -->\n"
                        f"<p>{entity or '__FILL_IN__:subject'} __FILL_IN__:restate_the_point_naming_the_subject</p>"
                    ),
                    verification="Read each paragraph in isolation; does it open by naming its subject?",
                ),
            ))

    return findings, skipped, []


def _rewrite_patch(entity, misses) -> str:
    lines = [
        "<!-- Make each claim self-contained IN PROSE. Do not split the page into",
        "     smaller blocks: Google Search Central states there is no requirement",
        "     to break content into tiny pieces for AI to understand it. -->",
        "",
    ]
    for fact, why in misses[:3]:
        lines.append(f"<!-- claim: {fact['claim'][:90]}  ({why}) -->")
        lines.append(
            f"<p>{entity or '__FILL_IN__:subject'} __FILL_IN__:state_this_claim_in_one_sentence_"
            f"that_names_the_subject.</p>"
        )
        lines.append("")
    return "\n".join(lines).rstrip()
