#!/usr/bin/env python3
"""answerability-audit: are key facts stated as short, self-contained, quotable text?
Round-2 appendix B/C: assistants pick pages they can easily *quote a clear fact from*.
Usage: check_answerability.py <cache_dir>"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "answerability-audit"


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = A.html_pages(meta)
    findings = []
    if not pages:
        return findings

    total = len(pages)

    # 1. FAQ / Q&A structure present anywhere?
    faq_pages, faq_schema = 0, 0
    for p in pages:
        html = A.read_page(cache_dir, p, "html") or ""
        low = html.lower()
        if "faqpage" in low or '"question"' in low or "itemtype" in low and "question" in low:
            faq_schema += 1
        text = A.read_page(cache_dir, p, "text") or ""
        if re.search(r"(?:frequently asked|faq)\b", text, re.I) or text.count("?") >= 4:
            faq_pages += 1
    if faq_schema == 0 and faq_pages > 0:
        # Only suggest FAQ schema when question-like prose actually exists on the site.
        # Absence of both questions and FAQ schema is not a finding.
        findings.append(A.finding(
            "Question-like content exists but lacks FAQ structured data",
            "low",
            f"No FAQPage/Question structured data across {total} sampled pages, "
            f"but {faq_pages} page(s) contain question-like prose that could benefit from "
            "FAQ markup.",
            "Consider marking up existing Q&A content with FAQPage JSON-LD to make it "
            "directly quotable by assistants.",
            "low", "answerability", checked=total,
            finding_type="improvement"))

    # 2. Thin content (little for a machine to quote)
    # Exclude pages already identified as SPA shells (text_len < 300) — those are
    # caught by render-extraction-audit and double-counting inflates the finding count.
    quotable_pages = [p for p in pages if p.get("text_len", 0) >= 300]
    thin = [(p["url"], p.get("text_len", 0)) for p in quotable_pages if p.get("text_len", 0) < 500]
    if thin:
        findings.append(A.finding(
            "Thin pages with little quotable text",
            "medium" if len(thin) > len(quotable_pages) / 2 else "low",
            f"{len(thin)}/{len(quotable_pages)} content pages have under 500 characters of body text, e.g. "
            f"{', '.join(f'{u} ({n})' for u, n in thin[:4])}.",
            "Add substantive, plainly-worded copy stating the key facts. Assistants cannot quote "
            "what isn't written; pages that state facts explicitly get cited more.",
            "medium" if len(thin) > len(quotable_pages) / 2 else "low", "answerability",
            checked=len(quotable_pages), thin_html_sensitive=True))

    # 3. Homepage answers 'what is this / who is it for' above the fold
    home = pages[0]
    home_text = (A.read_page(cache_dir, home, "text") or "")[:600].lower()
    signals = ["we ", "our ", "provides", "helps", "platform", "software", "service",
               "company", "for ", "solution", "tool", "app"]
    if len(home_text) < 120 or sum(s in home_text for s in signals) < 2:
        evidence = f"First ~600 chars of homepage text are sparse or vague: \"{home_text[:160].strip()}…\""
        if home.get("text_len", 0) < 300:
            evidence += (" (Note: homepage may be client-side rendered; the text measured "
                         "is the raw HTML shell, not the full rendered content.)")
        findings.append(A.finding(
            "Homepage does not clearly state what the brand is / who it serves",
            "high",
            evidence,
            "Lead with one plain sentence: what it is, who it's for, and the core value. This is "
            "the sentence assistants quote to describe the brand.",
            "high", "answerability", thin_html_sensitive=True))

    # 3b. Answer-formatting / chunkability: substantial pages that are walls of text
    # (no lists, tables, or question-style headings) are hard for assistants to extract from.
    # Exclude legal/utility pages — these legitimately don't need structured content.
    excluded_roles = {"legal", "utility", "sitemap", "non-html"}
    substantial = [p for p in pages
                   if p.get("text_len", 0) >= 800
                   and p.get("page_role", "content") not in excluded_roles]
    unstructured = [p["url"] for p in substantial
                    if p.get("n_lists", 0) == 0 and p.get("n_tables", 0) == 0
                    and p.get("n_question_headings", 0) == 0]
    if substantial and len(unstructured) >= max(1, len(substantial) // 2):
        findings.append(A.finding(
            "Content isn't structured for extraction (walls of text)",
            "medium",
            f"{len(unstructured)}/{len(substantial)} substantial content pages (>=800 chars, "
            "excluding legal/utility) use no lists, tables, or question-style headings, e.g. "
            + ", ".join(unstructured[:3]) + ".",
            "Break key content into scannable structure: question-style H2/H3 headings, bulleted "
            "lists, and comparison tables. Assistants extract and quote discrete chunks far more "
            "readily than long paragraphs.",
            "medium", "answerability", checked=len(substantial),
            thin_html_sensitive=True))

    # 4. Contact/NAP facts present as text (locally-important, highly-queried facts)
    joined = " ".join((A.read_page(cache_dir, p, "text") or "") for p in pages[:5]).lower()
    has_email = bool(re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", joined))
    has_phone = bool(re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", joined))
    if not (has_email or has_phone):
        findings.append(A.finding(
            "No contact facts (email/phone) available as text",
            "low",
            "No email or phone number found as extractable text across sampled pages.",
            "Publish contact details as real text (not only in images or a JS widget) so "
            "assistants can surface them when asked how to reach the brand.",
            "low", "answerability", checked=min(5, total),
            finding_type="improvement"))

    return findings


if __name__ == "__main__":
    A.emit(SKILL, run(sys.argv[1]))
