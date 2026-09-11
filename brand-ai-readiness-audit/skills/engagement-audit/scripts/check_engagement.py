#!/usr/bin/env python3
"""engagement-audit: once a visitor arrives, will they stay?
On-site engagement half of the Round-2 problem: orientation, next-step clarity,
page weight/speed, mobile-readiness, intrusive interstitials.
Usage: check_engagement.py <cache_dir>"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "engagement-audit"

CTA_WORDS = ["get started", "sign up", "start free", "try ", "buy ", "book ", "contact",
             "request", "subscribe", "download", "learn more", "add to cart", "demo",
             "get a quote", "shop"]

# Page roles where a clear CTA / conversion next-step is expected.
# Articles, docs, legal, utility, and about pages don't need marketing CTAs.
ACTIONABLE_ROLES = {"homepage", "product", "content", "contact"}


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = A.html_pages(meta)
    findings = []
    if not pages:
        return findings
    total = len(pages)

    # 1. Mobile viewport
    no_vp = [p["url"] for p in pages if not p.get("has_viewport")]
    if no_vp:
        findings.append(A.finding(
            "Missing mobile viewport meta tag",
            "high" if len(no_vp) == total else "medium",
            f"{len(no_vp)}/{total} HTML pages lack <meta name=viewport>: {', '.join(no_vp[:4])}.",
            "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">. Without "
            "it, mobile visitors get a zoomed-out desktop layout and bounce.",
            "high" if len(no_vp) == total else "medium", "engagement", checked=total))

    # 2. Page weight / latency (proxy for LCP and bounce)
    # Threshold: 500KB of raw HTML is genuinely heavy (not images/JS, just markup).
    heavy = [(p["url"], round(p.get("bytes", 0) / 1024)) for p in pages
             if p.get("bytes", 0) > 500_000]
    slow = [(p["url"], p.get("elapsed_ms", 0)) for p in pages if p.get("elapsed_ms", 0) > 3000]
    if heavy:
        findings.append(A.finding(
            "Very heavy HTML documents",
            "medium",
            "Pages with >500KB of raw HTML: " + "; ".join(f"{u} ({kb}KB)" for u, kb in heavy[:4]),
            "Trim/split oversized documents, defer non-critical assets, and lazy-load below-the-fold "
            "media. Heavy pages raise load time and abandonment.",
            "medium", "engagement", checked=total))
    if slow:
        findings.append(A.finding(
            "Slow server response on sampled pages",
            "medium",
            "Pages taking >3s to return an initial response (TTFB proxy, not a field-data metric): "
            + "; ".join(f"{u} ({ms}ms)" for u, ms in slow[:4]),
            "Investigate TTFB (caching, CDN, server rendering cost). Slow first response delays "
            "everything after it and drives bounce.",
            "medium", "engagement", checked=total))

    # 3. Weak next-step orientation (no CTA) — only for actionable page roles
    # Articles, documentation, legal pages don't need marketing CTAs.
    actionable = [p for p in pages
                  if p.get("page_role", "content") in ACTIONABLE_ROLES
                  and p.get("text_len", 0) > 500]
    no_cta = []
    for p in actionable:
        text = (A.read_page(cache_dir, p, "text") or "").lower()
        if not any(w in text for w in CTA_WORDS):
            no_cta.append(p["url"])
    if actionable and len(no_cta) > len(actionable) / 2:
        findings.append(A.finding(
            "Actionable pages lack a clear call-to-action / next step",
            "medium",
            f"{len(no_cta)}/{len(actionable)} actionable pages (homepage/product/content) "
            f"contain no recognizable CTA phrase.",
            "Give each key page one obvious next step (primary CTA) so an arriving visitor knows "
            "what to do next instead of leaving.",
            "medium", "engagement", checked=len(actionable),
            finding_type="improvement", thin_html_sensitive=True))

    # 4. Thin navigation (orientation) — only for content/homepage/product pages
    nav_roles = {"homepage", "product", "content", "article", "about"}
    nav_pages = [p for p in pages
                 if p.get("page_role", "content") in nav_roles
                 and p.get("text_len", 0) > 300]
    low_links = [p["url"] for p in nav_pages if p.get("n_links", 0) < 5]
    if nav_pages and len(low_links) > len(nav_pages) / 2:
        findings.append(A.finding(
            "Sparse internal navigation on content pages",
            "low",
            f"{len(low_links)}/{len(nav_pages)} content pages expose fewer than 5 same-host "
            f"links in the raw HTML.",
            "Provide clear header/footer navigation and contextual internal links so visitors can "
            "orient and move deeper into the site.",
            "low", "engagement", checked=len(nav_pages),
            finding_type="improvement", thin_html_sensitive=True))

    # 5. Intrusive interstitial / autoplay signals (heuristic from raw HTML)
    # Refined: exclude cookie-consent patterns and muted autoplay backgrounds.
    intrusive = 0
    intrusive_evidence = []
    for p in pages[:6]:
        html = A.read_page(cache_dir, p, "html") or ""
        low = html.lower()
        # Check for popup/interstitial overlays (excluding cookie consent)
        has_overlay = bool(re.search(
            r"(modal|popup|interstitial|newsletter).{0,40}(overlay|backdrop)", low))
        is_cookie = bool(re.search(r"cookie.{0,30}(modal|consent|banner|overlay)", low))
        # Check for non-muted autoplay (muted background videos are standard practice)
        has_intrusive_autoplay = ("autoplay" in low
                                  and not re.search(r"autoplay[^>]*muted", low)
                                  and ("audio" in low or "<video" in low))
        if (has_overlay and not is_cookie) or has_intrusive_autoplay:
            reason = []
            if has_overlay and not is_cookie:
                reason.append("popup/interstitial overlay")
            if has_intrusive_autoplay:
                reason.append("non-muted autoplay media")
            intrusive += 1
            intrusive_evidence.append(f"{p['url']} ({', '.join(reason)})")
    if intrusive:
        findings.append(A.finding(
            "Possible intrusive interstitial or autoplay media",
            "low",
            f"{intrusive} sampled page(s) show markup consistent with engagement barriers: "
            + "; ".join(intrusive_evidence[:3]) + ".",
            "Avoid full-screen interstitials on entry and non-muted autoplaying audio/video; both "
            "are common immediate-bounce triggers (and interstitials are penalized on mobile search).",
            "low", "engagement", checked=min(6, total),
            finding_type="improvement"))

    return findings


if __name__ == "__main__":
    A.emit(SKILL, run(sys.argv[1]))
