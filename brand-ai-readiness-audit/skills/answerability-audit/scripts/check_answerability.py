#!/usr/bin/env python3
"""answerability-audit: are the page's important facts stated clearly enough to
be extracted and quoted?

Mechanism 4 of the chain - are the facts sufficiently clear. The test applied
here is whether important facts are hard to identify, NOT whether the page
contains a particular density of lists, tables or FAQ markup. Legal pages,
essays, documentation and editorial prose are legitimately paragraph-heavy and
are not penalised for that.

Usage: check_answerability.py <cache_dir>
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "answerability-audit"

FAQ_SCHEMA = re.compile(r'"@type"\s*:\s*"(?:FAQPage|QAPage|Question)"', re.I)
QUESTION_LINE = re.compile(r"(?:^|[.!?]\s)([A-Z][^.!?]{10,120}\?)")


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = A.html_pages(meta)
    findings, skips = [], []

    non_html = A.non_html_resources(meta)
    if non_html:
        skips.append(A.skipped(
            "content and answerability checks on non-HTML resources",
            f"{len(non_html)} crawled resource(s) are not HTML documents; they contain no "
            "prose for a reader to quote."))
    if not pages:
        skips.append(A.skipped("all answerability checks",
                               "no HTML page was retrieved in this crawl"))
        return findings, skips

    total = len(pages)

    # ---- 1. FAQ structure --------------------------------------------------- #
    # Never a defect. Raised only when the site plainly contains a real Q&A block
    # (several full question sentences on one page) that is not marked up.
    faq_schema_pages, qa_prose_pages = 0, []
    for p in pages:
        html = A.read_page(cache_dir, p, "html") or ""
        if FAQ_SCHEMA.search(html):
            faq_schema_pages += 1
            continue
        text = A.read_page(cache_dir, p, "text") or ""
        questions = QUESTION_LINE.findall(text)
        q_headings = p.get("n_question_headings", 0)
        # Require either several question-style headings, or several full question
        # sentences. A stray question mark in marketing copy is not a Q&A block.
        if q_headings >= 3 or len(questions) >= 4:
            qa_prose_pages.append((p["url"], max(q_headings, len(questions))))
    if qa_prose_pages and faq_schema_pages == 0:
        findings.append(A.finding(
            "Question-and-answer content is present but not marked up as FAQ data",
            "low",
            f"{len(qa_prose_pages)}/{total} sampled pages contain at least three question-style "
            "headings or four full question sentences, and no page in the sample declares "
            "FAQPage, QAPage or Question structured data: "
            + ", ".join(f"{u} ({n} questions)" for u, n in qa_prose_pages[:3]) + ".",
            "The answers are already readable as prose. Marking them up states explicitly "
            "which text answers which question, rather than leaving a consumer to infer the "
            "pairing from layout.",
            "Wrap the existing question-and-answer blocks on the listed pages in FAQPage "
            "JSON-LD. Do not create new questions to justify the markup.",
            "low", "answerability", checked=total, finding_type="improvement",
            confidence="medium", mechanism="clarity-of-facts",
            dedup_key="answerability:faq-markup"))

    # ---- 2. thin content ---------------------------------------------------- #
    # Only for roles whose purpose is to convey information. A login screen, a
    # tool and a directory listing are legitimately short on prose.
    content_roles = {"homepage", "article", "product", "documentation", "generic", "contact"}
    candidates = [p for p in pages
                  if A.role_of(p) in content_roles and A.role_confident(p)
                  and p.get("status") == 200]
    thin = [(p["url"], p.get("text_len", 0), A.role_of(p)) for p in candidates
            if p.get("text_len", 0) < 500]
    if thin and len(thin) >= max(2, len(candidates) // 2):
        findings.append(A.finding(
            "Information pages carry very little extractable text",
            "medium",
            f"{len(thin)}/{len(candidates)} sampled pages whose role is to convey information "
            "have under 500 characters of text in the server HTML: "
            + ", ".join(f"{u} ({n} chars, {r})" for u, n, r in thin[:4]) + ".",
            "There is little for a consumer to quote from these pages as served. The "
            "measurement is of the server response, so text added by JavaScript is not "
            "counted here.",
            "State the page's key facts as plain sentences in the page body: what it is, who "
            "it is for, and the specific details a reader would ask about.",
            "medium", "answerability", checked=len(candidates), confidence="medium",
            mechanism="clarity-of-facts", dedup_key="answerability:thin-content",
            thin_html_sensitive=True))

    # ---- 3. homepage states what the brand is -------------------------------- #
    # A homepage that names neither itself nor what it does leaves a machine to
    # infer identity from the domain. The test requires real absence of evidence,
    # and the finding stays cautious because "clear to a human" was not measured.
    home = A.homepage_of(meta)
    if home is not None:
        home_text = (A.read_page(cache_dir, home, "text") or "")
        opening = home_text[:800]
        title = (home.get("title") or "").strip()
        headings = home.get("headings") or []
        has_descriptor = bool(re.search(
            r"\b(?:is|are|we|our|helps?|provides?|builds?|makes?|offers?|platform|software|"
            r"service|tool|app|company|studio|agency|store|shop|blog|community|library|"
            r"network|for)\b", opening, re.I))
        sentences = len(re.findall(r"[.!?]", opening))
        if len(opening.strip()) < 120 or (not has_descriptor and sentences < 2):
            not_verified = None
            if home.get("text_len", 0) < 300:
                not_verified = ("what the homepage shows a visitor, since the measurement is "
                                "of the server HTML and this page may be client-rendered")
            findings.append(A.finding(
                "Homepage server HTML contains no sentence describing what the site is",
                "medium",
                f"The first 800 characters of the homepage's extracted text contain "
                f"{sentences} sentence-ending marks and no descriptive phrasing. "
                f"<title> is {('empty' if not title else repr(title[:60]))}; "
                f"{len(headings)} heading(s) were found. Extracted opening: "
                f"\"{opening[:150].strip()}\".",
                "A consumer summarising this brand from the server HTML has no explicit "
                "self-description to quote and must infer one. Whether a visitor sees such a "
                "statement on screen was not assessed.",
                "Put one plain sentence near the top of the homepage saying what the site is, "
                "who it is for, and what it does, and make sure it is present in the "
                "server-rendered HTML.",
                "medium", "answerability", checked=1, checked_unit="homepage",
                confidence="medium", page_role="homepage", mechanism="clarity-of-facts",
                dedup_key="answerability:homepage-identity",
                not_verified=not_verified, thin_html_sensitive=True))

    # ---- 4. extractability of important facts -------------------------------- #
    # NOT a "walls of text" rule. Paragraph-heavy prose is fine. This fires only
    # where a page's role implies discrete, look-up-able facts (product details,
    # reference documentation) and the page presents none of the structure those
    # facts normally need, while also being long.
    factual_roles = {"product", "documentation"}
    factual = [p for p in pages
               if A.role_of(p) in factual_roles and A.role_confident(p)
               and p.get("text_len", 0) >= 1200]
    unstructured = [p["url"] for p in factual
                    if p.get("n_lists_content", 0) == 0 and p.get("n_tables", 0) == 0
                    and len(p.get("heading_levels") or []) <= 1]
    if unstructured:
        findings.append(A.finding(
            "Reference-style pages present their details as unbroken prose",
            "low",
            f"{len(unstructured)}/{len(factual)} sampled product or documentation pages with "
            "1200+ characters of text contain no list, no table and at most one heading "
            "outside nav, header and footer: " + ", ".join(unstructured[:3]) + ".",
            "Pages of these roles usually hold discrete look-up facts such as specifications, "
            "parameters or options. With no headings or list structure, each such fact has to "
            "be located within continuous prose. This is about these roles specifically; "
            "articles, essays and legal text are not assessed by this check.",
            "Give each distinct detail on these pages its own heading, list item or table row, "
            "so a specific fact can be located and quoted without the surrounding paragraph.",
            "low", "answerability", checked=len(factual), finding_type="improvement",
            confidence="medium", mechanism="clarity-of-facts",
            dedup_key="answerability:unstructured-reference"))
    skips.append(A.skipped(
        "content-structure assessment on prose page roles",
        "articles, legal pages, generic content and unclassified pages were excluded from "
        "the structure check: paragraph-heavy prose is a legitimate form for them."))

    # ---- 5. contact facts as text --------------------------------------------- #
    # Only asked where the site presents a contact route at all, so a personal
    # blog or a documentation site is not told to publish a phone number.
    contact_pages = [p for p in pages if A.role_of(p) == "contact"]
    if contact_pages:
        reachable = any(p.get("n_mailto", 0) or p.get("n_tel", 0) for p in contact_pages)
        joined = " ".join((A.read_page(cache_dir, p, "text") or "") for p in contact_pages)
        has_email = bool(re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", joined, re.I))
        has_form = any(p.get("n_forms", 0) for p in contact_pages)
        if not (reachable or has_email or has_form):
            findings.append(A.finding(
                "Contact pages expose no contact route in the server HTML",
                "medium",
                f"{len(contact_pages)} sampled page(s) classified as contact pages contain no "
                "mailto: link, no tel: link, no email address as text and no form element.",
                "A consumer asked how to reach this brand has nothing to extract from these "
                "pages as served. A contact widget loaded by JavaScript would not appear in "
                "this measurement.",
                "Publish at least one contact route as real text or a mailto:/tel: link on "
                "these pages, in addition to any JavaScript widget.",
                "medium", "answerability", checked=len(contact_pages), confidence="medium",
                page_role="contact", mechanism="clarity-of-facts",
                dedup_key="answerability:no-contact-facts", thin_html_sensitive=True))
    else:
        skips.append(A.skipped(
            "contact-facts check",
            "no sampled page was classified as a contact page, so the site was not assessed "
            "for published contact details."))

    return findings, skips


if __name__ == "__main__":
    f, s = run(sys.argv[1])
    A.emit(SKILL, f, s)
