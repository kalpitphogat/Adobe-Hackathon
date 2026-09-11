#!/usr/bin/env python3
"""Stage trust: does the page try to manipulate the machine that reads it?

Reachable, readable and well-marked-up content can still be untrustworthy. Three
patterns address the machine rather than the human and are increasingly detected
and penalised by assistants: text phrased as an instruction to an AI reader
(prompt injection, often buried in HTML comments or hidden nodes), large amounts
of visually-hidden text (cloaking — shown to the crawler, not the visitor), and
invisible or bidi-control Unicode smuggled into the text a machine extracts.

These are trust findings: they do not stop a page being fetched or parsed, but
they change whether an assistant will repeat what it found. Detection is
deliberately conservative — narrow injection phrasing, a multi-element threshold
for cloaking, and a run-length threshold for invisible characters — because a
false accusation of manipulation is worse than a miss.
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

# Inline styles that remove an element's text from human view.
HIDE_CSS = re.compile(
    r'style\s*=\s*["\'][^"\']*'
    r'(?:display\s*:\s*none'
    r'|visibility\s*:\s*hidden'
    r'|opacity\s*:\s*0(?:\.0+)?(?!\d)'
    r'|font-size\s*:\s*0'
    r'|text-indent\s*:\s*-\s*\d{3,}'
    r'|(?:left|top)\s*:\s*-\s*\d{4,})',
    re.I)

# Zero-width / word-joiner / BOM / bidi override + isolate controls, from ordinals
# so no invisible character lives in this source file.
_ZW = (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF,
       0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069)
ZERO_WIDTH = re.compile("[" + "".join(chr(c) for c in _ZW) + "]")

HIDDEN_MIN = 3   # a lone display:none menu is normal; several is a smell
ZW_MIN = 5       # a single stray zero-width char is noise; a run is deliberate


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
    cloaked: list[tuple[str, int]] = []
    invisible: list[tuple[str, int]] = []

    for page in pages:
        url = page["url"]
        html = _raw_html(b, page)
        if html:
            m = INJECTION.search(html)
            if m:
                injected.append((url, re.sub(r"\s+", " ", m.group(0)).strip()[:80]))
            n_hidden = len(HIDE_CSS.findall(html))
            if n_hidden >= HIDDEN_MIN:
                cloaked.append((url, n_hidden))
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
        findings.append(finding(
            check_id="trust.integrity.cloaked_text",
            title=f"Large amount of visually-hidden text on {len(urls)} page(s) (possible cloaking)",
            severity="medium", confidence="likely", stage="trust",
            category="discoverability", scope="site" if len(urls) > 1 else "url",
            evidence=(
                "Several elements are hidden from view via CSS (display:none / visibility:hidden / "
                "off-screen / font-size:0) while remaining in the served HTML a crawler reads: "
                + ", ".join(f"{u} ({n} hidden elements)" for u, n in cloaked[:3])
                + ". Divergence between what a human sees and what a machine reads is a classic "
                "spam signal, and means a fact a machine extracts may not be verifiable on the page."
            ),
            affected_urls=urls,
            action=action(
                summary="Keep the content shown to machines identical to what humans see.",
                effort="medium",
                mechanism=(
                    "Search and retrieval systems compare rendered and raw content; hidden keyword "
                    "or boilerplate text is treated as cloaking and suppresses trust in the page."
                ),
                source="references/integrity-checks.md",
                patch="Remove hidden keyword/boilerplate blocks; render genuinely optional UI as components, not large hidden text.",
                verification="Diff the rendered text against the raw HTML text; they should carry the same facts.",
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
