#!/usr/bin/env python3
"""render-extraction-audit: can a machine read the page's facts from the HTML it
is served, or do they only appear after JavaScript runs?

Mechanism 2 of the chain - read the content. This skill is careful about one
thing above all: a sparse raw HTML document is NOT by itself proof that a site is
invisible to AI. It is evidence that the *server-sent* HTML is sparse. Whether
the content is genuinely unreachable depends on rendering, which is measured only
when --render was used. When it was not, that limitation is reported as audit
scope, never as a website defect.

Usage: render_diff.py <cache_dir>
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "render-extraction-audit"

# Markers of a client-rendered application shell.
SPA_ROOTS = [r'<div[^>]+id=["\']root["\']', r'<div[^>]+id=["\']app["\']',
             r'<div[^>]+id=["\']__next["\']', r'<div[^>]+id=["\']__nuxt["\']',
             r'\bng-app\b', r'\bdata-reactroot\b', r'<div[^>]+id=["\']svelte["\']']

THIN_TEXT_CHARS = 300


def words(text):
    return set(re.findall(r"[a-z0-9]{4,}", (text or "").lower()))


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = A.html_pages(meta)
    findings, skips = [], []

    non_html = A.non_html_resources(meta)
    if non_html:
        skips.append(A.skipped(
            "raw-vs-rendered comparison on non-HTML resources",
            f"{len(non_html)} crawled resource(s) are not HTML documents; they are not "
            "rendered by a browser and carry no client-side content gap."))
    if not pages:
        skips.append(A.skipped("all render checks", "no HTML page was retrieved in this crawl"))
        return findings, skips

    render_used = meta.get("render_available", False)

    # ---- 1. sparse server HTML --------------------------------------------- #
    # Requires an actual application-shell marker. Sparse HTML alone is not
    # enough: a redirect stub, an error page or a genuinely short page would
    # otherwise be misread as a client-rendered site.
    thin = []
    for p in pages:
        if p.get("status") != 200:
            continue
        if A.role_of(p) in ("authentication", "resource"):
            continue
        html = A.read_page(cache_dir, p, "html") or ""
        if not any(re.search(pat, html, re.I) for pat in SPA_ROOTS):
            continue
        if p.get("text_len", 0) < THIN_TEXT_CHARS and len(html) > 1500:
            thin.append((p["url"], p.get("text_len", 0)))

    confirmed_gap = []
    rendered_pages = [p for p in pages if p.get("rendered") and p.get("rendered_len")]

    # ---- 2. measured raw-vs-rendered gap ----------------------------------- #
    if rendered_pages:
        for p in rendered_pages:
            raw = A.read_page(cache_dir, p, "text") or ""
            rendered = A.read_page(cache_dir, p, "rendered") or ""
            rw, dw = words(raw), words(rendered)
            only_rendered = dw - rw
            if len(dw) > 40 and len(only_rendered) / max(len(dw), 1) > 0.4:
                confirmed_gap.append((p["url"],
                                      round(len(only_rendered) / max(len(dw), 1) * 100),
                                      sorted(only_rendered)[:6]))
        if confirmed_gap:
            findings.append(A.finding(
                "Most readable text appears only after JavaScript runs",
                "high",
                f"{len(confirmed_gap)}/{len(rendered_pages)} rendered pages were compared word "
                "by word against their server HTML: "
                + "; ".join(f"{u}: {pct}% of the rendered vocabulary is absent from the server "
                            f"HTML (e.g. {', '.join(s)})" for u, pct, s in confirmed_gap[:3])
                + ".",
                "A consumer that reads the server response without executing JavaScript sees "
                "only the smaller vocabulary. Which consumers do execute JavaScript varies and "
                "was not tested here.",
                "Server-render or pre-render the primary content of these pages so the main "
                "facts are present in the initial HTML response.",
                "high", "render-extraction", checked=len(rendered_pages), confidence="high",
                material=True, mechanism="read-content",
                dedup_key="render-extraction:fact-gap"))
    else:
        # An audit limitation, recorded as scope. Not a finding about the website.
        skips.append(A.skipped(
            "raw-vs-rendered fact gap (direct measurement)",
            "no rendered snapshot is present in the cache, so the difference between the "
            "server HTML and the rendered DOM was not measured. Re-run with --render "
            "(Playwright/Chromium) to measure it directly.",
            pages_affected=len(pages)))

    if thin:
        gap_urls = {u for u, _, _ in confirmed_gap}
        thin_confirmed = [t for t in thin if t[0] in gap_urls]
        if thin_confirmed:
            # Already covered by the measured-gap finding above; do not report twice.
            thin = [t for t in thin if t[0] not in gap_urls]
    if thin:
        findings.append(A.finding(
            "Server HTML is an application shell with almost no text",
            "medium",
            f"{len(thin)}/{len(pages)} sampled pages return a client-side application root "
            f"element with under {THIN_TEXT_CHARS} characters of extractable text in the "
            "server response, e.g. "
            + ", ".join(f"{u} ({n} chars)" for u, n in thin[:4]) + ".",
            "The facts a visitor sees are therefore assembled in the browser. "
            + ("The rendered comparison did not confirm a gap on these specific URLs."
               if render_used else
               "Whether they are reachable after rendering was not measured in this run, so "
               "this is not evidence that the content is inaccessible to AI - only that it is "
               "absent from the initial HTML."),
            "Server-render or pre-render the primary content of these routes so the main facts "
            "exist in the initial HTML response, then re-run this audit with --render to "
            "confirm the gap is closed.",
            "medium", "render-extraction", checked=len(pages),
            confidence="high" if render_used else "medium",
            mechanism="read-content", dedup_key="render-extraction:thin-shell",
            not_verified=None if render_used else
            "whether the content becomes available after JavaScript executes"))

    # ---- 3. information locked in images ------------------------------------ #
    # Only content-area images that are not icon-sized and not marked decorative
    # are considered. A missing alt on a decorative icon carries no facts.
    img_pages = [p for p in pages if p.get("n_content_imgs", 0) >= 3]
    heavy = [(p["url"], p.get("n_content_imgs_no_alt", 0), p.get("n_content_imgs", 0))
             for p in img_pages
             if p.get("n_content_imgs_no_alt", 0) / max(p.get("n_content_imgs", 1), 1) > 0.6]
    if heavy:
        findings.append(A.finding(
            "Content images carry no alt text",
            "low",
            f"{len(heavy)}/{len(img_pages)} sampled pages where at least three images sit in "
            "the content area (outside nav, header, footer and aside, not icon-sized, not "
            "role=presentation) have no alt attribute on most of them: "
            + "; ".join(f"{u} ({n}/{tot} missing)" for u, n, tot in heavy[:4]) + ".",
            "Whether these particular images carry information a reader needs was not "
            "determined; the audit measured their position and size, not their content. "
            "Where they do carry facts, those facts are unavailable to any text-based reader "
            "and to assistive technology.",
            "Review the listed images. Give the ones that convey information a description of "
            "what they show, and mark the purely decorative ones with alt=\"\".",
            "low", "render-extraction", checked=len(img_pages), finding_type="improvement",
            confidence="medium", mechanism="read-content",
            dedup_key="render-extraction:image-alt",
            not_verified="whether the images convey information rather than decoration"))

    return findings, skips


if __name__ == "__main__":
    f, s = run(sys.argv[1])
    A.emit(SKILL, f, s)
