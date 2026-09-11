#!/usr/bin/env python3
"""integrity-audit: does the page try to manipulate the machine reading it?

Trust and safety on the discoverability side. Three distinct things are detected,
and the skill is deliberately reluctant about the middle one:

  1. Text that addresses or instructs an AI reader (prompt injection).
  2. Substantial text hidden from human view that is NOT ordinary UI. Menus,
     dialogs, tab panels, carousels, skip links and screen-reader-only text are
     legitimate and are excluded; the presence of display:none is never on its
     own treated as cloaking.
  3. Invisible and bidirectional-control Unicode in the extracted text.

Usage: check_integrity.py <cache_dir>
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "integrity-audit"

# LLM-directive / prompt-injection phrasing. Kept specific so ordinary prose that
# merely mentions AI does not match.
INJECTION = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions"
    r"|disregard\s+(?:the\s+)?(?:above|previous|earlier)\s+(?:instructions?|prompt|text)"
    r"|as an ai language model"
    r"|you are (?:chatgpt|claude|gemini|an ai assistant|a large language model)"
    r"|(?:do not|don'?t) (?:mention|reveal|disclose) (?:this|the following|that)"
    r"|(?:instructions?|note|message) (?:to|for) (?:the )?(?:ai|assistant|llm|chatbot|model)\b"
    r"|<!--\s*(?:ai|llm|assistant|gpt)[:\s]",
    re.I)

# Elements whose contents are presented AS quoted or code-formatted material
# rather than asserted by the page. An article that quotes an AI-directed note,
# or shows one in a code block, is writing about the technique, not using it, and
# must not be reported as carrying an injected directive.
_QUOTED_TAGS = ("code", "pre", "blockquote", "samp", "kbd")
QUOTED_CONTEXT = re.compile(
    "|".join(r"<{t}[^>]*>.*?</{t}[^>]*>".format(t=t) for t in _QUOTED_TAGS),
    re.IGNORECASE | re.DOTALL)

# Invisible / zero-width / bidi-control code points, built from ordinals so no
# invisible characters live in this source file.
_ZW = (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF,
       0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
       0x2066, 0x2067, 0x2068, 0x2069)
ZERO_WIDTH = re.compile("[" + "".join(chr(c) for c in _ZW) + "]")

# A hidden block only draws attention when it holds a meaningful amount of text
# AND is large relative to what the page actually shows. The ratio gate does most
# of the work: a small hidden template string on a large page is suppressed by it,
# while a page whose invisible text rivals its visible text is flagged at any size.
HIDDEN_ABS_CHARS = 150
HIDDEN_RATIO = 0.25
# ...or an outright large block of invisible non-UI prose, whatever the page size.
HIDDEN_ABS_ALONE = 2000
# Several separate hidden non-UI blocks on one page is a pattern rather than an
# accident, so a repeated structure lowers the volume needed to notice it.
HIDDEN_BLOCK_COUNT = 3
HIDDEN_ABS_REPEATED = 100
# Below this the ratio is arithmetic noise rather than a measurement.
MIN_VISIBLE_FOR_RATIO = 120
# Roles whose visible text is minimal by design and whose hidden UI state is
# inherent. Excluded from this check rather than mis-measured by it.
HIDDEN_EXEMPT_ROLES = {"authentication", "utility"}


def interactive_screen(p):
    """A login form or tool panel: little prose, several controls, and hidden
    error/state containers as a matter of course. The hidden-to-visible ratio
    carries no signal on such a page, whatever role confidence it was given."""
    if A.role_of(p) in HIDDEN_EXEMPT_ROLES:
        return True
    if p.get("n_password_inputs", 0) > 0:
        return True
    controls = (p.get("n_inputs", 0) + p.get("n_buttons", 0) + p.get("n_selects", 0))
    return controls >= 3 and p.get("text_len", 0) < 600


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = A.html_pages(meta)
    findings, skips = [], []

    non_html = A.non_html_resources(meta)
    if non_html:
        skips.append(A.skipped(
            "integrity checks on non-HTML resources",
            f"{len(non_html)} crawled resource(s) are not HTML documents; hidden-element and "
            "page-text checks do not apply to them."))
    if not pages:
        skips.append(A.skipped("all integrity checks",
                               "no HTML page was retrieved in this crawl"))
        return findings, skips

    total = len(pages)
    injection_hits, hidden_pages, zw_pages = [], [], []
    ui_hidden_total = 0
    quoted_only = []

    hidden_exempt = 0
    for p in pages:
        html = A.read_page(cache_dir, p, "html") or ""
        text = A.read_page(cache_dir, p, "text") or ""

        # Search with quoted and code-formatted regions removed, so only text the
        # page asserts in its own voice can raise this finding.
        asserted = QUOTED_CONTEXT.sub(" ", html)
        m = INJECTION.search(asserted)
        if m:
            injection_hits.append((p["url"], re.sub(r"\s+", " ", m.group(0)).strip()[:90]))
        elif INJECTION.search(html):
            quoted_only.append(p["url"])

        hidden = p.get("hidden_text_len", 0)
        ui_hidden_total += p.get("hidden_ui_text_len", 0)
        visible = max(p.get("text_len", 0), 1)
        blocks = p.get("n_hidden_blocks", 0)
        if hidden and interactive_screen(p):
            hidden_exempt += 1
            continue
        ratio_ok = (visible >= MIN_VISIBLE_FOR_RATIO and hidden / visible >= HIDDEN_RATIO)
        substantial = hidden >= HIDDEN_ABS_CHARS and ratio_ok
        repeated = blocks >= HIDDEN_BLOCK_COUNT and hidden >= HIDDEN_ABS_REPEATED and ratio_ok
        if substantial or repeated or hidden >= HIDDEN_ABS_ALONE:
            hidden_pages.append((p["url"], hidden, visible, blocks))

        zw = len(ZERO_WIDTH.findall(text))
        if zw >= 5:
            zw_pages.append((p["url"], zw))

    # ---- 1. prompt injection ------------------------------------------------ #
    if injection_hits:
        findings.append(A.finding(
            "Page markup contains text addressed to an AI reader",
            "critical",
            f"{len(injection_hits)}/{total} sampled pages contain a phrase that reads as an "
            "instruction directed at an AI system: "
            + "; ".join(f'{u}: "{s}"' for u, s in injection_hits[:3]) + ".",
            "Text of this form is treated as an attempt to influence a machine reader rather "
            "than to inform a human one, and is a recognised reason for a consumer to distrust "
            "or decline to cite a page.",
            "Remove the matched text from these pages. If it is quoted content about prompt "
            "injection rather than an instruction, move it inside a code block or escape it so "
            "it does not read as a directive.",
            "critical", "integrity", checked=total, confidence="high", material=True,
            mechanism="trust", dedup_key="integrity:prompt-injection"))

    if quoted_only:
        skips.append(A.skipped(
            "AI-directive text in quoted or code-formatted content",
            f"{len(quoted_only)} sampled page(s) contain AI-directive phrasing only inside "
            "<code>, <pre>, <blockquote>, <samp> or <kbd>, e.g. "
            + ", ".join(quoted_only[:3]) + ". Material presented as a quotation or a code "
            "sample is the page writing about the technique, not addressing a machine "
            "reader, so no finding was raised."))

    # ---- 2. hidden non-UI text ----------------------------------------------- #
    if hidden_pages:
        findings.append(A.finding(
            "Substantial text is hidden from view outside ordinary UI patterns",
            "medium",
            f"{len(hidden_pages)}/{total} sampled pages carry text inside elements hidden by "
            "inline CSS or the hidden attribute whose class, id and role name no menu, dialog, "
            "tab panel, carousel, consent notice or screen-reader helper. Each flagged page "
            f"is not an interactive login or tool screen, holds at least "
            f"{int(HIDDEN_RATIO * 100)}% as much hidden as visible text, and carries either "
            f"{HIDDEN_ABS_CHARS}+ hidden characters or {HIDDEN_ABS_REPEATED}+ spread across "
            f"{HIDDEN_BLOCK_COUNT}+ separate hidden blocks: "
            + "; ".join(f"{u} ({h} hidden vs {v} visible chars, {n} blocks)"
                        for u, h, v, n in hidden_pages[:3]) + ".",
            "Text a machine reads but a visitor does not see is a mismatch between the two "
            "audiences. Recognised UI patterns were excluded, but this audit did not execute "
            "CSS or JavaScript, so an element may still become visible through a stylesheet "
            "rule or user interaction.",
            "Open the listed pages and confirm each hidden block is either shown to visitors "
            "through an interaction or genuinely unnecessary. Remove blocks that exist only "
            "for machine readers.",
            "medium", "integrity", checked=total, confidence="medium",
            mechanism="trust", dedup_key="integrity:hidden-text",
            not_verified="whether the hidden elements become visible via external CSS or "
                         "user interaction, which was not executed"))
    if hidden_exempt:
        skips.append(A.skipped(
            "hidden-text check on login and tool screens",
            f"{hidden_exempt} sampled page(s) are interactive screens (a password field, or "
            "several form controls with little prose) that carry hidden text. Hidden form, "
            "error and state containers are inherent to such screens, so the hidden-to-visible "
            "ratio carries no signal there and no finding was raised."))
    if not hidden_pages and ui_hidden_total:
        skips.append(A.skipped(
            "hidden-text check",
            f"hidden text was present but every hidden block carried a recognised UI marker "
            f"(menu, dialog, tab panel, carousel, consent or screen-reader-only), totalling "
            f"{ui_hidden_total} characters. These are legitimate interface states and were "
            "not reported."))

    # ---- 3. invisible Unicode ------------------------------------------------ #
    if zw_pages:
        findings.append(A.finding(
            "Invisible or bidirectional-control Unicode in page text",
            "medium",
            f"{len(zw_pages)}/{total} sampled pages contain five or more zero-width or "
            "bidi-control code points (U+200B, U+200C, U+200D, U+2060, U+FEFF, U+202A-E, "
            "U+2066-9) in their extracted text: "
            + ", ".join(f"{u} ({n} characters)" for u, n in zw_pages[:3]) + ".",
            "These characters are invisible to a reader but are carried into whatever a "
            "machine extracts, where they can split words for a matcher or reorder displayed "
            "text. They are frequently an artefact of a copy-paste or a CMS rather than "
            "deliberate.",
            "Strip zero-width and bidirectional-control characters from stored content, and "
            "normalise text on save so they are not reintroduced.",
            "medium", "integrity", checked=total, confidence="high", material=True,
            mechanism="trust", dedup_key="integrity:zero-width"))

    return findings, skips


if __name__ == "__main__":
    f, s = run(sys.argv[1])
    A.emit(SKILL, f, s)
