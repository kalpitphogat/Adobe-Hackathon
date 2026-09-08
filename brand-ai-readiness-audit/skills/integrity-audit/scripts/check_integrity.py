#!/usr/bin/env python3
"""integrity-audit: does the page try to manipulate the machine reading it?
Detects content aimed at crawlers/assistants but hidden from humans — visually-hidden
text (cloaking), prompt-injection / LLM-directive phrases (often in HTML comments or
hidden nodes), and invisible/zero-width Unicode used to smuggle text. These erode the
trust an assistant places in the page and are a citation/ranking risk.
Usage: check_integrity.py <cache_dir>"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "integrity-audit"

# LLM-directive / prompt-injection phrasing (case-insensitive). Kept specific to avoid
# firing on ordinary prose that merely mentions AI.
INJECTION = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions"
    r"|disregard\s+(?:the\s+)?(?:above|previous|earlier)"
    r"|as an ai language model"
    r"|you are (?:chatgpt|claude|gemini|an ai|a large language model)"
    r"|system\s*prompt\b"
    r"|prompt\s*injection"
    r"|(?:do not|don'?t) (?:mention|reveal|disclose) (?:this|the following|that)"
    r"|(?:instructions?|note|message) (?:to|for) (?:the )?(?:ai|assistant|llm|chatbot|model)"
    r"|<!--\s*(?:ai|llm|assistant|gpt)[:\s]",
    re.I)

# CSS/attribute patterns that hide an element's text from human view
HIDE_CSS = re.compile(
    r'style\s*=\s*["\'][^"\']*'
    r'(?:display\s*:\s*none'
    r'|visibility\s*:\s*hidden'
    r'|opacity\s*:\s*0(?:\.0+)?(?!\d)'
    r'|font-size\s*:\s*0'
    r'|text-indent\s*:\s*-\s*\d{3,}'
    r'|(?:left|top)\s*:\s*-\s*\d{4,})',
    re.I)

# Invisible / zero-width / bidi-control code points (built from ordinals so no invisible
# characters live in this source file): zero-width space/joiners, word-joiner, BOM, and
# the bidi override / isolate controls.
_ZW = (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF,
       0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
       0x2066, 0x2067, 0x2068, 0x2069)
ZERO_WIDTH = re.compile("[" + "".join(chr(c) for c in _ZW) + "]")


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = [p for p in meta["pages"] if p["status"] == 200]
    findings = []
    if not pages:
        return findings
    total = len(pages)

    injection_hits, hidden_pages, zw_pages = [], [], []
    for p in pages:
        html = A.read_page(cache_dir, p, "html") or ""
        text = A.read_page(cache_dir, p, "text") or ""

        m = INJECTION.search(html)
        if m:
            snippet = re.sub(r"\s+", " ", m.group(0)).strip()[:80]
            injection_hits.append((p["url"], snippet))

        n_hidden = len(HIDE_CSS.findall(html))
        if n_hidden >= 3:  # a few hidden nodes are normal (menus/modals); many is a smell
            hidden_pages.append((p["url"], n_hidden))

        zw = len(ZERO_WIDTH.findall(text))
        if zw >= 5:
            zw_pages.append((p["url"], zw))

    # 1. Prompt-injection / hidden LLM directives — highest severity
    if injection_hits:
        findings.append(A.finding(
            "Prompt-injection / hidden LLM instructions in page content",
            "critical",
            f"{len(injection_hits)} page(s) contain text that reads as an instruction to an AI "
            "assistant (often in HTML comments or hidden nodes), e.g. "
            + "; ".join(f'{u}: "{s}"' for u, s in injection_hits[:3]) + ".",
            "Remove any text that instructs, manipulates, or addresses an AI reader. Assistants "
            "increasingly detect and distrust (or refuse to cite) pages carrying injected "
            "directives — it is a reputation and safety risk, not an optimization.",
            "critical", "integrity", checked=total))

    # 2. Visually-hidden text (cloaking) — content shown to machines but not humans
    if hidden_pages:
        findings.append(A.finding(
            "Large amount of visually-hidden text (possible cloaking)",
            "medium",
            f"{len(hidden_pages)}/{total} pages hide many elements from view via CSS "
            "(display:none / visibility:hidden / off-screen / font-size:0), e.g. "
            + ", ".join(f"{u} ({n})" for u, n in hidden_pages[:3]) + ".",
            "Keep the content shown to machines identical to what humans see. Hidden keyword or "
            "boilerplate text reads as cloaking and is a trust/ranking risk; move genuinely "
            "optional UI (menus, modals) into components rather than large hidden text blocks.",
            "medium", "integrity", checked=total))

    # 3. Invisible / zero-width Unicode — a channel for smuggling hidden text
    if zw_pages:
        findings.append(A.finding(
            "Invisible / zero-width Unicode characters in content",
            "medium",
            f"{len(zw_pages)}/{total} pages contain runs of zero-width or bidi-control "
            "characters (U+200B/200C/200D/FEFF/202x), e.g. "
            + ", ".join(f"{u} ({n} chars)" for u, n in zw_pages[:3]) + ".",
            "Strip zero-width and bidirectional-control characters from page text. They are "
            "invisible to humans but carried into what a machine reads, and can hide or distort "
            "the extracted fact (or smuggle instructions).",
            "medium", "integrity", checked=total))

    return findings


if __name__ == "__main__":
    A.emit(SKILL, run(sys.argv[1]))
