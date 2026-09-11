#!/usr/bin/env python3
"""render-extraction-audit: are facts readable in the raw HTML, or only after JS?
This is the highest-signal discoverability check (Round-2 appendix C): a fact that
a human sees but that is absent from the server-sent HTML is invisible to the many
assistants/crawlers that read raw HTML. Usage: render_diff.py <cache_dir>"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "render-extraction-audit"

# thin-shell markers: raw HTML that is basically an empty app container
SPA_ROOTS = [r'<div[^>]+id="root"', r'<div[^>]+id="app"', r'<div[^>]+id="__next"',
             r'ng-app', r'data-reactroot']


def words(text):
    return set(w.lower() for w in re.findall(r"[a-z0-9]{4,}", (text or "").lower()))


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = A.html_pages(meta)
    findings = []

    # 1. Thin static HTML (client-rendered shell)
    thin = []
    for p in pages:
        raw_text_len = p.get("text_len", 0)
        html = A.read_page(cache_dir, p, "html") or ""
        looks_spa = any(re.search(pat, html, re.I) for pat in SPA_ROOTS)
        if raw_text_len < 300 and (looks_spa or len(html) > 1500):
            thin.append((p["url"], raw_text_len))
    if thin:
        # Severity depends on whether we have render evidence: if --render was used
        # and confirmed the gap, it's critical. Without render data, we can only say
        # the raw HTML is sparse — the content may still be accessible after JS.
        render_available = meta.get("render_available", False)
        sev = "critical" if render_available else "high"
        evidence = (
            f"{len(thin)}/{len(pages)} sampled pages have <300 chars of extractable text in "
            f"the server HTML despite a full app shell, e.g. "
            f"{', '.join(f'{u} ({n} chars)' for u, n in thin[:4])}."
        )
        if not render_available:
            evidence += (" (Severity capped at high: re-run with --render to confirm "
                         "whether content is accessible after JavaScript executes.)")
        findings.append(A.finding(
            "Pages are near-empty in raw HTML (client-side rendered)",
            sev,
            evidence,
            "Server-render or pre-render the primary content (SSR/SSG, or a prerender layer "
            "for bots) so the main facts exist in the initial HTML, not only after JavaScript runs.",
            sev, "render-extraction", checked=len(pages)))

    # 2. Static-vs-rendered fact gap (needs render data)
    rendered_pages = [p for p in pages if p.get("rendered") and p.get("rendered_len")]
    if rendered_pages:
        gap = []
        for p in rendered_pages:
            raw = A.read_page(cache_dir, p, "text") or ""
            rendered = A.read_page(cache_dir, p, "rendered") or ""
            rw, dw = words(raw), words(rendered)
            only_rendered = dw - rw
            # significant if the rendered page reveals a lot of new words
            if len(dw) > 40 and len(only_rendered) / max(len(dw), 1) > 0.4:
                sample = list(only_rendered)[:12]
                gap.append((p["url"], round(len(only_rendered) / max(len(dw), 1) * 100), sample))
        if gap:
            findings.append(A.finding(
                "Content appears only after JavaScript renders (static/rendered gap)",
                "high",
                "Comparing raw HTML text to rendered text: " + "; ".join(
                    f"{u}: {pct}% of readable words are JS-only (e.g. {', '.join(s[:6])})"
                    for u, pct, s in gap[:3]),
                "Make the JS-injected facts available in the initial HTML (SSR/SSG or "
                "prerendering). Assistants that fetch raw HTML will otherwise miss them entirely.",
                "high", "render-extraction", checked=len(rendered_pages)))
    else:
        findings.append(A.finding(
            "Render comparison unavailable (headless browser not run)",
            "low",
            "No rendered snapshots in cache; the static-vs-rendered fact gap could not be "
            "measured directly. Thin-HTML heuristics above still apply.",
            "Re-run the crawler with --render (Playwright/Chromium) to measure the JS fact gap directly.",
            "low", "render-extraction"))

    # 3. Facts locked in non-text (images without alt)
    img_pages = [p for p in pages if p.get("n_imgs", 0) >= 3]
    heavy = [(p["url"], p["n_imgs_no_alt"], p["n_imgs"]) for p in img_pages
             if p.get("n_imgs_no_alt", 0) / max(p.get("n_imgs", 1), 1) > 0.6]
    if heavy:
        findings.append(A.finding(
            "Images carry information but lack alt text",
            "medium",
            "Pages where most images have no alt attribute: " + "; ".join(
                f"{u} ({n}/{tot} missing)" for u, n, tot in heavy[:4]),
            "Add descriptive alt text (and prefer real text over text-in-images). Facts locked "
            "in pixels are unreadable to machines that build answers from text.",
            "medium", "render-extraction", checked=len(img_pages)))

    return findings


if __name__ == "__main__":
    A.emit(SKILL, run(sys.argv[1]))
