#!/usr/bin/env python3
"""engagement-audit: why might an arriving visitor fail to get what they came for?

This skill does NOT equate engagement with having a CTA, a footer, five links or
any particular HTML pattern. Those are supporting signals at most. The question
is:

    Given what this page appears to be FOR, can a visitor tell what it is, do the
    thing it exists to let them do, and find the next relevant step?

So every judgement starts from the page's role, and technical measurements
(viewport, response latency, document size, intrusive overlays) are treated as
contextual supporting evidence rather than as universal requirements.

Usage: check_engagement.py <cache_dir>
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "engagement-audit"

# The likely primary task a visitor arrives with, per page role. This is what a
# "next step" has to serve; a generic marketing CTA is only one possible answer.
ROLE_TASK = {
    "homepage":       "understand what this site is and reach the section they need",
    "product":        "understand the offering and act on it (buy, sign up, get pricing)",
    "article":        "read the piece and find related reading",
    "documentation":  "find a specific answer and navigate to adjacent topics",
    "contact":        "obtain a contact route and use it",
    "directory":      "scan the list and open the right entry",
    "utility":        "operate the tool",
    "authentication": "sign in or create an account",
    "legal":          "read the policy",
    "generic":        "read the page's content",
}

# Task-relevant next actions, per role. Deliberately role-specific: counting the
# word "contact" in a footer is not evidence that a product page offers a next
# step, and a documentation page needs navigation rather than conversion.
TASK_ACTIONS = {
    "homepage": [r"\bget started\b", r"\bsign up\b", r"\bstart (?:free|now|here)\b",
                 r"\btry\s+\w+", r"\bcreate (?:an )?account\b", r"\bbook a\b",
                 r"\brequest (?:a )?demo\b", r"\bcontact (?:us|sales)\b",
                 r"\bsee (?:pricing|plans)\b", r"\bshop\b", r"\bbrowse\b",
                 r"\blearn more\b", r"\bexplore\b", r"\bview (?:all|our)\b",
                 r"\bdownload\b", r"\bsubscribe\b", r"\bread more\b", r"\bsearch\b"],
    "product":  [r"\bbuy\b", r"\badd to (?:cart|bag|basket)\b", r"\bsign up\b",
                 r"\bget started\b", r"\bstart (?:free|trial)\b", r"\brequest (?:a )?demo\b",
                 r"\bcontact sales\b", r"\bget a quote\b", r"\bchoose (?:a )?plan\b",
                 r"\bsubscribe\b", r"\border\b", r"\bbook\b", r"\bdownload\b",
                 r"\bview (?:pricing|plans|details)\b"],
    "contact":  [r"\bsubmit\b", r"\bsend (?:message|enquiry|inquiry)\b", r"\bemail us\b",
                 r"\bcall\b", r"\bbook\b"],
}

# Overlay markup that is plausibly an entry interstitial rather than ordinary UI.
# TWO independent signals are required: an element must express a capture INTENT
# *and* carry a blocking/overlay indicator. A newsletter section sitting in a page
# footer expresses intent alone, and is not an interstitial.
_CAPTURE_INTENT = re.compile(
    r"(?:newsletter|subscribe|signup|sign-?up|email-?capture|paywall|interstitial|"
    r"welcome-?mat|exit-?intent|register-?wall|survey)", re.I)
_BLOCKING = re.compile(
    r"(?:modal|overlay|popup|pop-?up|lightbox|interstitial|backdrop|welcome-?mat|"
    r"exit-?intent|takeover|fullscreen)", re.I)
_ELEMENT = re.compile(r"<(?:div|section|aside|dialog)\b[^>]*>", re.I)
_ATTR = re.compile(r"\b(class|id|role|aria-modal|style)\s*=\s*[\"']([^\"']*)[\"']", re.I)
# Elements inside a page footer are page furniture, never an entry interstitial.
_FOOTER_BLOCK = re.compile(r"<footer\b.*?</footer>", re.I | re.S)
_CONSENT = re.compile(
    r"(?:cookie|consent|gdpr|ccpa|privacy[-_ ]?(?:banner|notice|preferences)|"
    r"onetrust|cookiebot|usercentrics|klaro|cookieyes|trustarc)", re.I)
_AGE_GATE = re.compile(r"(?:age[-_ ]?(?:gate|verification)|are you (?:over|at least) \d+)", re.I)

# Raw-HTML size threshold. Chosen so it flags documents far outside the ordinary
# range rather than merely large ones: the median HTML document is well under
# 100KB, and 1MB of markup alone (excluding all sub-resources) is unusual.
HTML_SIZE_THRESHOLD = 1_000_000
SLOW_MS = 3000


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = A.html_pages(meta)
    findings, skips = [], []
    non_html = A.non_html_resources(meta)
    if non_html:
        skips.append(A.skipped(
            "all engagement checks on non-HTML resources",
            f"{len(non_html)} crawled resource(s) are not HTML documents. Viewport, "
            "navigation, next-step and overlay checks describe pages a visitor lands on "
            "and are meaningless for a sitemap, feed or API response."))
    if not pages:
        skips.append(A.skipped("all engagement checks",
                               "no HTML page was retrieved in this crawl"))
        return findings, skips

    total = len(pages)

    # ---- 1. mobile viewport ------------------------------------------------ #
    # This is a genuine universal: without it a mobile browser renders a desktop
    # layout at desktop width, whatever the page is for.
    no_vp = [p["url"] for p in pages if not p.get("has_viewport")]
    if no_vp:
        # "Every sampled page" only means something when the sample is big enough
        # to say so; on one or two pages it is a page-level observation.
        all_pages_affected = len(no_vp) == total and total >= 3
        findings.append(A.finding(
            "Pages declare no mobile viewport",
            "high" if all_pages_affected else "medium",
            f"{len(no_vp)}/{total} sampled HTML pages have no <meta name=\"viewport\">: "
            + ", ".join(no_vp[:4]) + ".",
            "Mobile browsers fall back to a ~980px virtual viewport for such pages and "
            "scale the result down, so text renders small and taps land imprecisely. This "
            "is a property of the markup and applies regardless of what the page is for.",
            "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> to "
            "the affected templates.",
            "high" if all_pages_affected else "medium", "engagement", checked=total,
            confidence="high", material=True,
            mechanism="visitor-usability", dedup_key="engagement:no-viewport",
            not_verified="what a mobile browser receives. This audit fetched each page with "
                         "one desktop-class user-agent, and a site that serves a different "
                         "document to mobile user-agents may declare a viewport there"))

    # ---- 2. crawler-observed latency --------------------------------------- #
    # This is the auditor's own single-sample request time. It is NOT a Core Web
    # Vitals measurement and is not LCP; that is stated in the evidence.
    slow = [(p["url"], p.get("elapsed_ms", 0)) for p in pages
            if p.get("elapsed_ms", 0) > SLOW_MS]
    if slow and len(slow) >= max(2, total // 3):
        findings.append(A.finding(
            "Slow server response time observed during the crawl",
            "medium",
            f"{len(slow)}/{total} sampled pages took over {SLOW_MS}ms to return their initial "
            "response to this auditor's single request, e.g. "
            + "; ".join(f"{u} ({ms}ms)" for u, ms in slow[:4]) + ".",
            "This is the auditor's own one-off request latency from one network location. It "
            "is not Largest Contentful Paint and not field data from real users, and it "
            "includes network distance to this crawler. It is a prompt to measure properly, "
            "not a measurement of what visitors experience.",
            "Measure real-user Core Web Vitals (for example via the Chrome UX Report) before "
            "acting. If server think-time is confirmed as the cause, investigate caching, CDN "
            "coverage and server-render cost.",
            "medium", "engagement", checked=total, confidence="medium",
            mechanism="visitor-usability", dedup_key="engagement:slow-response",
            not_verified="real-user load performance, which was not measured"))

    # ---- 3. unusually large HTML documents --------------------------------- #
    heavy = [(p["url"], round(p.get("bytes", 0) / 1024)) for p in pages
             if p.get("bytes", 0) > HTML_SIZE_THRESHOLD]
    if heavy:
        findings.append(A.finding(
            "Unusually large HTML documents",
            "low",
            f"{len(heavy)}/{total} sampled pages return over "
            f"{HTML_SIZE_THRESHOLD // 1000}KB of raw HTML markup: "
            + "; ".join(f"{u} ({kb}KB)" for u, kb in heavy[:4]) + ".",
            "This measures the size of the HTML document only. It excludes images, scripts, "
            "stylesheets and fonts, so it is not total page weight and does not establish "
            "that visitors experience a slow page. Markup this far above the ordinary range "
            "usually indicates inlined data or an unpaginated listing.",
            "Check what is inflating the markup on these specific URLs, most commonly inlined "
            "JSON state or an unpaginated list, and move it out of the document or paginate it.",
            "low", "engagement", checked=total, finding_type="improvement", confidence="medium",
            mechanism="visitor-usability", dedup_key="engagement:heavy-html",
            not_verified="total page weight and real-user load time"))

    # ---- 4. task-relevant next step ---------------------------------------- #
    # Only roles whose purpose actually implies a conversion-style next action are
    # considered, and only when the role was assigned with confidence. An article,
    # a documentation page, a legal notice, a login screen and a tool are all
    # perfectly good without one.
    candidates = [p for p in pages
                  if A.role_of(p) in TASK_ACTIONS and A.role_confident(p)
                  and p.get("text_len", 0) > 400]
    if candidates:
        missing = []
        for p in candidates:
            role = A.role_of(p)
            text = (A.read_page(cache_dir, p, "text") or "").lower()
            patterns = TASK_ACTIONS[role]
            if not any(re.search(pat, text) for pat in patterns):
                missing.append((p["url"], role))
        if missing and len(missing) >= max(1, len(candidates) // 2):
            roles_hit = sorted({r for _, r in missing})
            findings.append(A.finding(
                "Pages whose role implies an action offer no task-relevant next step",
                "medium",
                f"{len(missing)}/{len(candidates)} sampled pages with a confidently-classified "
                f"{'/'.join(roles_hit)} role contain no text matching an action relevant to "
                f"that role, e.g. " + ", ".join(f"{u} ({r})" for u, r in missing[:3]) + ".",
                "For these roles the visitor's likely task is "
                + "; ".join(ROLE_TASK.get(r, "act on the page") for r in roles_hit)
                + ". No wording matching such an action was found in the extracted text. "
                "Pages of other roles were excluded from this check, and the absence of a "
                "generic marketing call-to-action is not itself treated as a problem.",
                "On the listed pages, state the one action the page exists to enable, in "
                "words that name the action, and place it where it is reachable without "
                "scrolling past the explanation.",
                "medium", "engagement", checked=len(candidates),
                finding_type="improvement", confidence="medium",
                page_role="/".join(roles_hit), mechanism="visitor-task",
                dedup_key="engagement:no-next-step", thin_html_sensitive=True))
    else:
        skips.append(A.skipped(
            "task-relevant next step",
            "no sampled page was confidently classified into a role whose purpose implies a "
            "conversion-style action (homepage, product, contact), so the check did not run. "
            "Articles, documentation, tools, legal and login pages are not expected to carry one."))

    # ---- 5. orientation / navigation --------------------------------------- #
    # Not a link-count rule. A page is flagged only when it offers no navigation
    # affordance of ANY kind: no nav/header/footer landmark, no internal links,
    # and no on-page search - i.e. a genuine dead end.
    orient_roles = {"homepage", "article", "product", "documentation", "directory",
                    "generic", "contact"}
    orient = [p for p in pages
              if A.role_of(p) in orient_roles and A.role_confident(p)
              and p.get("text_len", 0) > 300]
    dead_ends = [p["url"] for p in orient
                 if p.get("n_internal_links", 0) == 0
                 and not (p.get("has_nav") or p.get("has_header") or p.get("has_footer"))
                 and p.get("n_forms", 0) == 0]
    if dead_ends:
        findings.append(A.finding(
            "Content pages offer no route onward",
            "medium",
            f"{len(dead_ends)}/{len(orient)} sampled content pages expose zero same-host links "
            "and no nav, header or footer landmark in the server HTML: "
            + ", ".join(dead_ends[:4]) + ".",
            "A visitor landing here has no in-page route to anywhere else on the site, and a "
            "crawler following links has no path onward either. The measurement is of the "
            "server-sent HTML; navigation injected later by JavaScript would not appear here.",
            "Add the site's primary navigation and a small set of contextual internal links "
            "to these templates, and ensure they are present in the server-rendered HTML.",
            "medium", "engagement", checked=len(orient), confidence="medium",
            mechanism="visitor-task", dedup_key="engagement:dead-end",
            thin_html_sensitive=True))

    # ---- 6. intrusive interstitials and autoplay ---------------------------- #
    # Requires markup that is plausibly a blocking entry overlay. Cookie consent,
    # accessibility UI, navigation menus and muted background video are excluded,
    # and anything short of clear evidence is reported as an improvement.
    overlay_hits, autoplay_hits = [], []
    sample = pages[:6]
    for p in sample:
        html = A.read_page(cache_dir, p, "html") or ""
        # Strip footers first: a newsletter block in the page footer is furniture.
        body = _FOOTER_BLOCK.sub(" ", html)
        for m in _ELEMENT.finditer(body):
            tag = m.group(0)
            attrs = {k.lower(): v for k, v in _ATTR.findall(tag)}
            blob = " ".join(attrs.get(k, "") for k in ("class", "id"))
            if not _CAPTURE_INTENT.search(blob):
                continue
            if _CONSENT.search(tag) or _AGE_GATE.search(tag):
                continue
            # Second, independent signal: the element must also look blocking.
            blocking = (_BLOCKING.search(blob)
                        or attrs.get("aria-modal", "").lower() == "true"
                        or attrs.get("role", "").lower() == "dialog"
                        or re.search(r"position\s*:\s*fixed", attrs.get("style", ""), re.I))
            if not blocking:
                continue
            overlay_hits.append((p["url"], re.sub(r"\s+", " ", tag)[:110]))
            break
        # Attribute-order-independent: read the parsed media elements, so the
        # common "muted autoplay" ordering is not misread as unmuted autoplay.
        for mel in (p.get("media") or []):
            if mel.get("autoplay") and not mel.get("muted"):
                autoplay_hits.append((p["url"], mel.get("tag", "media")))
                break

    if autoplay_hits:
        findings.append(A.finding(
            "Media set to autoplay with sound",
            "medium",
            f"{len(autoplay_hits)}/{len(sample)} sampled pages contain a <video> or <audio> "
            "element with an autoplay attribute and no muted attribute: "
            + ", ".join(f"{u} (<{t}>)" for u, t in autoplay_hits[:3]) + ".",
            "Unmuted autoplay is blocked by default in current desktop and mobile browsers, "
            "so the practical effect is usually that the media fails to start rather than "
            "that sound plays unexpectedly. The attribute still signals intent to autoplay "
            "with sound.",
            "Add the muted attribute if the media should start automatically, or remove "
            "autoplay and let the visitor start it.",
            "medium", "engagement", checked=len(sample), finding_type="improvement",
            confidence="medium", mechanism="visitor-usability",
            dedup_key="engagement:autoplay"))

    if overlay_hits:
        findings.append(A.finding(
            "Markup consistent with an entry overlay that is not a consent notice",
            "low",
            f"{len(overlay_hits)}/{len(sample)} sampled pages contain an element outside the "
            "page footer that names a capture intent (newsletter, sign-up, email capture, "
            "paywall, exit-intent) AND independently looks blocking (a modal/overlay/popup "
            "class, role=dialog, aria-modal, or position:fixed): "
            + "; ".join(f"{u}: {t}" for u, t in overlay_hits[:2]) + ". "
            "Cookie-consent, privacy and age-gate elements were excluded.",
            "The markup is present; whether the overlay is actually shown on arrival, and "
            "whether it blocks the content, depends on JavaScript and display rules this "
            "audit did not execute. Treat this as a pointer to verify, not as a confirmed "
            "barrier.",
            "Open these pages as a first-time visitor on a phone and confirm the overlay does "
            "not cover the content on arrival. If it does, delay it or move it inline.",
            "low", "engagement", checked=len(sample), finding_type="improvement",
            confidence="low", mechanism="visitor-usability",
            dedup_key="engagement:interstitial",
            not_verified="whether the overlay is displayed on page load, since no rendering "
                         "or interaction was performed"))

    return findings, skips


if __name__ == "__main__":
    f, s = run(sys.argv[1])
    A.emit(SKILL, f, s)
