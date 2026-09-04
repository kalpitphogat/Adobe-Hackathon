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


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = [p for p in meta["pages"] if p["status"] == 200]
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
            f"{len(no_vp)}/{total} pages lack <meta name=viewport>: {', '.join(no_vp[:4])}.",
            "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">. Without "
            "it, mobile visitors get a zoomed-out desktop layout and bounce.",
            "high" if len(no_vp) == total else "medium", "engagement", checked=total))

    # 2. Page weight / latency (proxy for LCP and bounce)
    heavy = [(p["url"], round(p.get("bytes", 0) / 1024)) for p in pages if p.get("bytes", 0) > 2_000_000]
    slow = [(p["url"], p.get("elapsed_ms", 0)) for p in pages if p.get("elapsed_ms", 0) > 3000]
    if heavy:
        findings.append(A.finding(
            "Very heavy HTML documents",
            "medium",
            "Pages with >2MB of HTML: " + "; ".join(f"{u} ({kb}KB)" for u, kb in heavy[:4]),
            "Trim/split oversized documents, defer non-critical assets, and lazy-load below-the-fold "
            "media. Heavy pages raise load time and abandonment.",
            "medium", "engagement", checked=total))
    if slow:
        findings.append(A.finding(
            "Slow server response on sampled pages",
            "medium",
            "Pages taking >3s to fetch: " + "; ".join(f"{u} ({ms}ms)" for u, ms in slow[:4]),
            "Investigate TTFB (caching, CDN, server rendering cost). Slow first response delays "
            "everything after it and drives bounce.",
            "medium", "engagement", checked=total))

    # 3. Weak next-step orientation (no CTA)
    no_cta = []
    for p in pages:
        text = (A.read_page(cache_dir, p, "text") or "").lower()
        if not any(w in text for w in CTA_WORDS):
            no_cta.append(p["url"])
    if len(no_cta) > total / 2:
        findings.append(A.finding(
            "Pages lack a clear call-to-action / next step",
            "medium",
            f"{len(no_cta)}/{total} sampled pages contain no recognizable CTA phrase.",
            "Give each key page one obvious next step (primary CTA) so an arriving visitor knows "
            "what to do next instead of leaving.",
            "medium", "engagement", checked=total))

    # 4. Thin navigation (orientation)
    low_links = [p["url"] for p in pages if p.get("n_links", 0) < 5]
    if len(low_links) > total / 2:
        findings.append(A.finding(
            "Sparse internal navigation",
            "low",
            f"{len(low_links)}/{total} sampled pages expose fewer than 5 links, limiting a "
            "visitor's ability to explore.",
            "Provide clear header/footer navigation and contextual internal links so visitors can "
            "orient and move deeper into the site.",
            "low", "engagement", checked=total))

    # 5. Intrusive interstitial / autoplay signals (heuristic from raw HTML)
    intrusive = 0
    for p in pages[:6]:
        low = (A.read_page(cache_dir, p, "html") or "").lower()
        if re.search(r"(modal|popup|interstitial|newsletter).{0,40}(overlay|backdrop)", low) \
           or "autoplay" in low:
            intrusive += 1
    if intrusive:
        findings.append(A.finding(
            "Possible intrusive interstitial or autoplay media",
            "low",
            f"{intrusive} sampled page(s) show markup consistent with overlay pop-ups or autoplay "
            "media.",
            "Avoid full-screen interstitials on entry and autoplaying audio/video; both are common "
            "immediate-bounce triggers (and interstitials are penalized on mobile search).",
            "low", "engagement", checked=min(6, total)))

    return findings


if __name__ == "__main__":
    A.emit(SKILL, run(sys.argv[1]))
