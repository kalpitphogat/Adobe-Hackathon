#!/usr/bin/env python3
"""Stage trust: does the page try to manipulate the machine that reads it?

Reachable, readable and well-marked-up content can still be untrustworthy. Three
patterns address the machine rather than the human and are increasingly detected
and penalised by assistants: text phrased as an instruction to an AI reader
(prompt injection, often buried in HTML comments or hidden nodes), text hidden
from the visitor but left in the served HTML for a crawler to read (cloaking),
and invisible or bidi-control Unicode smuggled into the text a machine extracts.

Cloaking is judged by CONTENT, not by volume. Hiding text with CSS is completely
ordinary on the modern web — responsive navigation, screen-reader-only hints,
accordions, tab panels, modal dialogs and cookie banners all sit in the DOM while
hidden from view — so the mere presence, or even the count, of hidden elements is
not a defect. What we flag is hidden text whose WORDING has no honest reason to be
concealed from a human while shown to a machine: content that grants the reader
permission or authority, tells the assistant how to rank, cite or describe the
brand, instructs it to bypass its own rules, or stuffs keywords a visitor never
sees. Benign hidden UI text is read and dismissed, never reported.

These are trust findings: they do not stop a page being fetched or parsed, but
they change whether an assistant will repeat what it found. Detection is
deliberately conservative — narrow injection phrasing, a manipulation classifier
over the hidden text itself for cloaking, and a run-length threshold for invisible
characters — because a false accusation of manipulation is worse than a miss.
"""

from __future__ import annotations

import re

from bundle import action, finding

CHECKS = [
    {"id": "trust.integrity.prompt_injection", "stage": "trust", "category": "discoverability",
     "tier": "core", "default_severity": "critical", "skill": "trust-freshness-audit"},
    {"id": "trust.integrity.cloaked_text", "stage": "trust", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "trust-freshness-audit"},
    {"id": "trust.integrity.invisible_unicode", "stage": "trust", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "trust-freshness-audit"},
]

# Directive phrasing aimed at an AI reader. Narrow on purpose: ordinary prose that
# merely mentions AI ("we use AI to…") must not match; the trigger is an instruction.
INJECTION = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions"
    r"|disregard\s+(?:the\s+)?(?:above|previous|earlier)"
    r"|as an ai language model"
    r"|you are (?:chatgpt|claude|gemini|an ai|a large language model)"
    r"|system\s*prompt\b"
    r"|prompt\s*injection"
    r"|(?:reveal|repeat|print|output|ignore)\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions)"
    r"|(?:do not|don'?t) (?:mention|reveal|disclose) (?:this|the following|that)"
    r"|(?:instructions?|note|message) (?:to|for) (?:the )?(?:ai|assistant|llm|chatbot|model)"
    r"|<!--\s*(?:ai|llm|assistant|gpt)[:\s]"
    # LLM chat-template / instruction control tokens. These are machine-only
    # delimiters — they have no meaning in human copy, so matching one is
    # unambiguous evidence of text staged for a model rather than a reader.
    r"|<\|(?:im_start|im_end|im_sep|system|user|assistant|endoftext)\|>"
    r"|\[/?INST\]|<</?SYS>>|<\|eot_id\|>|<\|start_header_id\|>",
    re.I)

# An opening tag that hides its own subtree from a human: an inline style that
# removes it from view, or the boolean `hidden` attribute. We then read the text
# INSIDE that element and judge it by content, never by the fact that it is hidden.
_HIDE_STYLE = (
    r'display\s*:\s*none'
    r'|visibility\s*:\s*hidden'
    r'|opacity\s*:\s*0(?:\.0+)?(?!\d)'
    r'|font-size\s*:\s*0'
    r'|text-indent\s*:\s*-\s*\d{3,}'
    r'|(?:left|top)\s*:\s*-\s*\d{4,}'
)
HIDDEN_OPEN = re.compile(
    r"<([a-zA-Z][\w-]*)\b"
    r"(?:[^>]*\bstyle\s*=\s*[\"'][^\"']*(?:" + _HIDE_STYLE + r")[^\"']*[\"']"
    # the standalone boolean `hidden` attribute — a leading space rules out
    # aria-hidden / data-hidden, which do not hide content from a crawler.
    r"|[^>]*\shidden(?=[\s/>=])[^>]*)"
    r"[^>]*>",
    re.I)

# Wording a page has no honest reason to HIDE from a human while leaving it in the
# DOM for a machine. Benign hidden UI (menu labels, "Close", screen-reader hints,
# tab or accordion bodies) does not match; each branch is a deliberate attempt to
# steer, deceive, or claim authority over the machine that reads the page.
HIDDEN_ABUSE = re.compile(
    # granting the reader/agent permission or authority it does not have
    r"(?:you (?:now )?have|you are (?:hereby )?granted|i (?:hereby )?grant you|granting you)\s+"
    r"(?:full\s+|admin(?:istrator)?\s+|elevated\s+|special\s+|root\s+)?"
    r"(?:permission|access|authori[sz]ation|authority|privileges?|rights)"
    r"|you\s+(?:are|'re)\s+(?:hereby\s+)?(?:authori[sz]ed|permitted|allowed|cleared)\s+to"
    r"|(?:grant|give|provide)\s+(?:me|us|the\s+(?:ai|assistant|agent|model|system))\s+"
    r"(?:full\s+|admin(?:istrator)?\s+)?(?:permission|access|control)"
    # telling the assistant to bypass its own constraints
    r"|(?:ignore|bypass|override|disable|forget)\s+(?:your|the|all|any)\s+"
    r"(?:safety|guidelines?|rules?|restrictions?|filters?|instructions?|policy|policies)"
    # dictating how the assistant should rank, cite, or describe the brand
    r"|(?:always|you\s+must|be\s+sure\s+to|make\s+sure\s+to|remember\s+to)\s+"
    r"(?:recommend|promote|prefer|rank|cite|feature|endorse|mention|say)"
    r"|(?:rank|list|place|rate)\s+(?:this|us|our\s+(?:site|brand|product|company))\s+"
    r"(?:first|#?1|number\s*one|at\s+the\s+top|above|highest)"
    r"|do\s+not\s+(?:recommend|mention|cite|show|list|suggest)\s+(?:our\s+|any\s+|the\s+)?"
    r"(?:competitor|rival|alternativ)"
    # asserting unearned trust directly to the machine
    r"|(?:this\s+is|we\s+are|treat\s+(?:this|us)\s+as)\s+(?:the\s+)?"
    r"(?:official|verified|most\s+trusted|authoritative|#?1|number[\s-]one|best)\s+"
    r"(?:source|site|brand|answer|result|choice)",
    re.I)

# Zero-width / word-joiner / BOM / bidi override + isolate controls, from ordinals
# so no invisible character lives in this source file.
_ZW = (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF,
       0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069)
ZERO_WIDTH = re.compile("[" + "".join(chr(c) for c in _ZW) + "]")

ZW_MIN = 5           # a single stray zero-width char is noise; a run is deliberate
STUFF_MIN_CHARS = 200  # keyword stuffing is judged only on a substantial hidden block


def _strip_tags(fragment: str) -> str:
    """Plain text of an HTML fragment: drop comments and nested tags, collapse space."""
    fragment = re.sub(r"<!--.*?-->", " ", fragment, flags=re.S)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", fragment).strip()


def _hidden_texts(html: str) -> list[str]:
    """Text inside elements hidden from a human via CSS or the `hidden` attribute.

    The closing tag is matched non-nested (up to the first same-name close), which
    can under-capture a nested hidden container. That bias is deliberate: it risks
    a miss, never a false accusation on content the element did not actually hold.
    """
    out: list[str] = []
    for m in HIDDEN_OPEN.finditer(html):
        tag = m.group(1).lower()
        start = m.end()
        close = re.search(rf"</{re.escape(tag)}\s*>", html[start:], flags=re.I)
        end = start + close.start() if close else min(start + 4000, len(html))
        text = _strip_tags(html[start:end])
        if text:
            out.append(text)
    return out


def _keyword_stuffed(text: str) -> bool:
    """A long hidden block that is a dense keyword list, not prose a visitor reads."""
    if len(text) < STUFF_MIN_CHARS:
        return False
    words = text.split()
    if len(words) < 30:
        return False
    separators = text.count(",") + text.count("|") + text.count("•") + text.count("/")
    sentence_ends = len(re.findall(r"[.!?](?:\s|$)", text))
    # Many separators, almost no sentence structure = a keyword dump, not a paragraph.
    return separators >= 12 and sentence_ends <= 2 and separators / len(words) > 0.2


def _hidden_abuse(text: str) -> str | None:
    """Return the offending phrase if hidden text is manipulative, else None."""
    m = HIDDEN_ABUSE.search(text)
    if m:
        return re.sub(r"\s+", " ", m.group(0)).strip()[:120]
    if _keyword_stuffed(text):
        return "keyword-stuffed hidden block (" + str(len(text)) + " chars, dense keyword list)"
    return None


def _raw_html(b, page: dict) -> str:
    rel = page.get("raw_html_path")
    if not rel:
        return ""
    path = b.root / rel
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []

    pages = b.html_pages()
    if not pages:
        for cid in ("trust.integrity.prompt_injection", "trust.integrity.cloaked_text",
                    "trust.integrity.invisible_unicode"):
            skipped.append({
                "check_id": cid,
                "reason": "no page was fetched successfully, so page content could not be inspected.",
                "confidence_effect": "not assessed",
            })
        return findings, skipped, []

    injected: list[tuple[str, str]] = []
    cloaked: list[tuple[str, str]] = []
    invisible: list[tuple[str, int]] = []

    for page in pages:
        url = page["url"]
        html = _raw_html(b, page)
        if html:
            m = INJECTION.search(html)
            if m:
                injected.append((url, re.sub(r"\s+", " ", m.group(0)).strip()[:80]))
            # Cloaking is judged by CONTENT: read the text inside hidden elements
            # and flag only the first block whose wording is manipulative. Benign
            # hidden UI text is read and dismissed.
            for hidden in _hidden_texts(html):
                offending = _hidden_abuse(hidden)
                if offending:
                    cloaked.append((url, offending))
                    break
        text = b.observed_text(page) or page.get("text") or ""
        zw = len(ZERO_WIDTH.findall(text))
        if zw >= ZW_MIN:
            invisible.append((url, zw))

    if injected:
        urls = sorted({u for u, _ in injected})
        examples = "; ".join(f'{u}: "{s}"' for u, s in injected[:3])
        findings.append(finding(
            check_id="trust.integrity.prompt_injection",
            title=f"Text addressed to an AI reader (prompt injection) on {len(urls)} page(s)",
            severity="critical", confidence="confirmed", stage="trust",
            category="discoverability", scope="site" if len(urls) > 1 else "url",
            evidence=(
                f"{len(urls)} page(s) carry text phrased as an instruction to an AI assistant, "
                f"frequently inside HTML comments or hidden nodes where a human never sees it: "
                f"{examples}. Assistants increasingly detect injected directives and distrust or "
                f"refuse to cite pages that carry them, so this is a reputation and safety risk "
                f"rather than an optimisation."
            ),
            affected_urls=urls,
            action=action(
                summary="Remove all text that instructs, manipulates, or addresses an AI reader.",
                effort="low",
                mechanism=(
                    "Retrieval assistants run injected-instruction detectors over fetched pages; a "
                    "page that tries to steer the model is filtered out of answers rather than "
                    "rewarded, so the directive removes the page from citations instead of shaping them."
                ),
                source="references/integrity-checks.md",
                patch="Delete the matched comment/hidden node, e.g. <!-- ignore all previous instructions ... -->",
                verification="Re-crawl and confirm no comment or hidden element contains AI-directive phrasing.",
            ),
        ))

    if cloaked:
        urls = sorted({u for u, _ in cloaked})
        examples = "; ".join(f'{u}: "{s}"' for u, s in cloaked[:3])
        findings.append(finding(
            check_id="trust.integrity.cloaked_text",
            title=f"Manipulative text hidden from visitors but left for crawlers on {len(urls)} page(s)",
            severity="medium", confidence="likely", stage="trust",
            category="discoverability", scope="site" if len(urls) > 1 else "url",
            evidence=(
                "Text hidden from view via CSS (display:none / visibility:hidden / off-screen) "
                "while left in the served HTML a crawler reads carries wording that has no honest "
                "reason to be concealed — it grants permission or authority, tells an assistant how "
                "to rank or describe the brand, instructs it to bypass its rules, or stuffs keywords: "
                + examples
                + ". This is content aimed at the machine and hidden from the human; assistants treat "
                "such divergence as a spam and manipulation signal and suppress trust in the page. "
                "(Ordinary hidden UI — menus, screen-reader text, accordions, modals — is not reported; "
                "only the manipulative wording above is.)"
            ),
            affected_urls=urls,
            action=action(
                summary="Remove the hidden manipulative text; never show machines wording you hide from visitors.",
                effort="medium",
                mechanism=(
                    "Retrieval systems compare what a human sees with what the raw HTML says; hidden "
                    "directives, authority claims or keyword dumps are read as an attempt to game the "
                    "machine and suppress trust in — or filter out — the page, the opposite of the intent."
                ),
                source="references/integrity-checks.md",
                patch="Delete the hidden node carrying the flagged wording. If content is genuinely optional UI, it should read as normal UI text, not instructions to or claims aimed at an AI.",
                verification="Confirm no CSS-hidden or hidden-attribute element contains directive, permission, ranking, or keyword-stuffed text.",
            ),
        ))

    if invisible:
        urls = sorted({u for u, _ in invisible})
        findings.append(finding(
            check_id="trust.integrity.invisible_unicode",
            title=f"Invisible / zero-width Unicode in the content of {len(urls)} page(s)",
            severity="medium", confidence="confirmed", stage="trust",
            category="discoverability", scope="site" if len(urls) > 1 else "url",
            evidence=(
                "Runs of zero-width or bidirectional-control code points (U+200B/200C/200D/FEFF/202x) "
                "appear in the extracted text of: "
                + ", ".join(f"{u} ({n} chars)" for u, n in invisible[:3])
                + ". They are invisible to a human but ride into the text a machine reads, where they "
                "can split or reorder the extracted fact, or hide content a reviewer never sees."
            ),
            affected_urls=urls,
            action=action(
                summary="Strip zero-width and bidi-control characters from page text.",
                effort="low",
                mechanism=(
                    "Extractors read the raw code points; an invisible character inside a word breaks "
                    "tokenisation and string matching even though the page looks correct to a person."
                ),
                source="references/integrity-checks.md",
                patch="Normalise content to remove U+200B-200D, U+2060, U+FEFF and U+202A-202E / U+2066-2069.",
                verification="Scan served text for those code points; expect none in human-readable copy.",
            ),
        ))

    return findings, skipped, []
