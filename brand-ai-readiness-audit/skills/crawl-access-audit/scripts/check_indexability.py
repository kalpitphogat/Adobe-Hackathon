#!/usr/bin/env python3
"""Stage reach: indexability, link integrity, transport and latency.

Everything here is deterministic and evidence-cheap, which is why the reach
stage carries the most checks: these are the findings least likely to be wrong.
"""

from __future__ import annotations

import statistics
import urllib.parse

from bundle import action, finding, threshold

CHECKS = [
    {"id": "reach.index.noindex_on_content", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "critical", "skill": "crawl-access-audit"},
    {"id": "reach.index.canonical_conflict", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "high", "skill": "crawl-access-audit"},
    {"id": "reach.index.redirect_chain_or_loop", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "crawl-access-audit"},
    {"id": "reach.http.soft_404", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "crawl-access-audit"},
    {"id": "reach.http.broken_internal_links", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "crawl-access-audit"},
    {"id": "reach.http.insecure_or_mixed_scheme", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "high", "skill": "crawl-access-audit"},
    {"id": "reach.perf.slow_median_ttfb", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "low", "skill": "crawl-access-audit"},
    {"id": "reach.sitemap.absent_or_invalid", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "crawl-access-audit"},
    {"id": "reach.sitemap.coverage_gap", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "low", "skill": "crawl-access-audit"},
]

# Page types where a noindex is the correct, intentional configuration.
NOINDEX_OK_TYPES = {"utility"}


def _has_noindex(value) -> bool:
    return bool(value) and "noindex" in str(value).lower()


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []
    proactive: list[dict] = []

    # ------------------------------------------------ noindex on content
    offenders = []
    for page in b.html_pages():
        page_type = b.page_type(page, profile)
        meta_robots = page.get("meta_robots")
        header = page.get("x_robots_tag")
        if not (_has_noindex(meta_robots) or _has_noindex(header)):
            continue
        if page_type in NOINDEX_OK_TYPES:
            skipped.append({
                "check_id": "reach.index.noindex_on_content",
                "reason": (
                    f"{page['url']} carries noindex but is a {page_type} page, where excluding it "
                    f"from indexes is the correct configuration."
                ),
                "confidence_effect": "suppressed by design",
            })
            continue
        offenders.append((page, meta_robots, header))

    if offenders:
        lines = "; ".join(
            f"{p['url']} via {'X-Robots-Tag header' if h else 'meta robots'} = "
            f"\"{h or m}\" (page type {b.page_type(p, profile)})"
            for p, m, h in offenders[:6]
        )
        findings.append(finding(
            check_id="reach.index.noindex_on_content",
            title=f"{len(offenders)} content page(s) tell crawlers not to index them",
            severity="critical", confidence="confirmed", stage="reach",
            category="discoverability", scope="url",
            evidence=(
                f"{len(offenders)} of {len(b.html_pages())} crawled pages carry a noindex "
                f"directive: {lines}. A noindex page is fetched, read, and then discarded, so it "
                f"can never be surfaced or cited."
            ),
            affected_urls=[p["url"] for p, _, _ in offenders],
            action=action(
                summary="Remove the noindex directive from these content pages.",
                effort="low",
                mechanism=(
                    "noindex instructs the crawler to drop the page after reading it, so every "
                    "downstream signal on that page is wasted work."
                ),
                source="Google Search Central, Block Search indexing with noindex",
                patch=(
                    "Remove this line from the page head:\n"
                    '  <meta name="robots" content="noindex">\n'
                    "and remove any X-Robots-Tag: noindex response header for these paths."
                ),
                verification=(
                    f"curl -sI {offenders[0][0]['url']} | grep -i x-robots-tag  # expect no noindex\n"
                    f"curl -s {offenders[0][0]['url']} | grep -i 'name=\"robots\"'"
                ),
            ),
        ))

    # ---------------------------------------------------- canonical conflicts
    known = {p["url"] for p in b.pages}
    statuses = {p["url"]: p.get("status") for p in b.pages}
    conflicts = []
    for page in b.html_pages():
        canonical = page.get("canonical")
        if not canonical:
            continue
        if canonical.rstrip("/") == page["url"].rstrip("/"):
            continue
        host_page = urllib.parse.urlsplit(page["url"]).hostname or ""
        host_canon = urllib.parse.urlsplit(canonical).hostname or ""
        target_status = statuses.get(canonical) or statuses.get(canonical.rstrip("/"))
        if host_canon and host_canon != host_page:
            conflicts.append((page["url"], canonical, f"cross-host (page {host_page}, canonical {host_canon})"))
        elif target_status is not None and target_status >= 400:
            conflicts.append((page["url"], canonical, f"canonical target returns HTTP {target_status}"))
        elif canonical in known:
            other = next((p for p in b.pages if p["url"] == canonical), None)
            if other and other.get("canonical") and other["canonical"].rstrip("/") == page["url"].rstrip("/"):
                conflicts.append((page["url"], canonical, "canonical pair points at each other"))

    if conflicts:
        findings.append(finding(
            check_id="reach.index.canonical_conflict",
            title=f"{len(conflicts)} page(s) declare a canonical URL that conflicts with themselves",
            severity="high", confidence="confirmed", stage="reach",
            category="discoverability", scope="url",
            evidence="; ".join(f"{u} -> {c} ({why})" for u, c, why in conflicts[:6]),
            affected_urls=[u for u, _, _ in conflicts],
            action=action(
                summary="Point each canonical at the page's own resolvable URL, or remove it.",
                effort="low",
                mechanism=(
                    "A canonical tells the crawler which URL to keep; pointing it somewhere broken "
                    "or reciprocal makes the crawler discard this page in favour of one that does "
                    "not resolve."
                ),
                source="RFC 6596; Google Search Central, Consolidate duplicate URLs",
                patch="\n".join(f'<link rel="canonical" href="{u}">  <!-- on {u} -->' for u, _, _ in conflicts[:3]),
                verification=f"curl -s {conflicts[0][0]} | grep -i 'rel=\"canonical\"'",
            ),
        ))

    # --------------------------------------------------- redirect chains
    chains = [
        (p["url"], p["redirect_chain"])
        for p in b.pages
        if len(p.get("redirect_chain") or []) > 2
    ]
    if chains:
        findings.append(finding(
            check_id="reach.index.redirect_chain_or_loop",
            title=f"{len(chains)} URL(s) redirect more than twice before resolving",
            severity="medium", confidence="confirmed", stage="reach",
            category="discoverability", scope="url",
            evidence="; ".join(
                f"{u}: " + " -> ".join(f"{h['url']} ({h['status']})" for h in chain)
                for u, chain in chains[:4]
            ),
            affected_urls=[u for u, _ in chains],
            action=action(
                summary="Collapse each chain to a single redirect to the final URL.",
                effort="low",
                mechanism=(
                    "Crawlers cap redirect depth and spend crawl budget per hop, so a long chain "
                    "risks the destination never being reached."
                ),
                source="RFC 9110 section 15.4",
                patch="\n".join(f"# redirect {chain[0]['url']} directly to {chain[-1].get('location')}"
                                for _, chain in chains[:3]),
                verification=f"curl -sIL {chains[0][0]} | grep -E '^HTTP|^location'",
            ),
        ))

    # ----------------------------------------------------------- soft 404
    soft = [s for s in (b.probes.get("soft_404") or []) if s.get("is_soft_404")]
    if soft:
        identical = all("status code" in s.get("verdict", "") for s in soft)
        findings.append(finding(
            check_id="reach.http.soft_404",
            title="Server returns HTTP 200 for URLs that cannot exist",
            severity="low" if identical else "medium",
            confidence="confirmed", stage="reach",
            category="discoverability", scope="site",
            evidence=(
                f"{len(soft)} of {len(b.probes.get('soft_404') or [])} probe URLs that cannot "
                f"legitimately exist returned HTTP 200: "
                + "; ".join(f"{s['probe_url']} -> {s['status']} ({s['wordcount']} words)" for s in soft[:3])
                + ". "
                + (
                    "The body is identical to the real 404 page, so only the status code is wrong."
                    if identical
                    else "This creates unbounded crawlable space: every mistyped URL becomes a new page."
                )
            ),
            affected_urls=[s["probe_url"] for s in soft],
            action=action(
                summary="Return HTTP 404 or 410 for URLs that do not exist.",
                effort="medium",
                mechanism=(
                    "A crawler uses the status code, not the page text, to decide whether a URL is "
                    "real; a 200 on a non-existent URL means crawl budget is spent on infinite "
                    "variations instead of real pages."
                ),
                source="RFC 9110 section 15.5.5",
                patch="# Serve the existing not-found template with status 404 rather than 200.",
                verification=f"curl -sI {soft[0]['probe_url']} | head -1  # expect HTTP/1.1 404",
            ),
        ))

    # ------------------------------------------------- broken internal links
    internal_targets: dict[str, set] = {}
    for page in b.html_pages():
        for link in (page.get("links") or {}).get("internal", []):
            internal_targets.setdefault(link, set()).add(page["url"])
    broken = sorted(
        (target, sorted(sources), statuses[target])
        for target, sources in internal_targets.items()
        if statuses.get(target) is not None and statuses[target] >= 400
    )
    total_links = sum(len(s) for s in internal_targets.values()) or 1
    rate = len(broken) / max(len(internal_targets), 1)
    max_rate = threshold(profile, "broken_link_rate_max", 0.02)
    max_count = threshold(profile, "broken_link_count_max", 5)
    if broken and (rate > max_rate or len(broken) > max_count):
        findings.append(finding(
            check_id="reach.http.broken_internal_links",
            title=f"{len(broken)} internal link target(s) return an error status",
            severity="medium", confidence="confirmed", stage="reach",
            category="discoverability", scope="site",
            evidence=(
                f"{len(broken)} of {len(internal_targets)} distinct internal link targets "
                f"({rate:.1%}) return 4xx or 5xx: "
                + "; ".join(f"{t} ({st}) linked from {srcs[0]}" for t, srcs, st in broken[:6])
            ),
            affected_urls=[t for t, _, _ in broken],
            action=action(
                summary="Fix or remove the broken internal links.",
                effort="low",
                mechanism=(
                    "Internal links are how a crawler discovers pages; links into errors waste "
                    "crawl budget and break the path to anything only reachable that way."
                ),
                source="RFC 9110 section 15.5",
                patch="\n".join(f"# {srcs[0]} links to {t} which returns {st}" for t, srcs, st in broken[:5]),
                verification=f"curl -sI {broken[0][0]} | head -1",
            ),
        ))
    elif broken:
        skipped.append({
            "check_id": "reach.http.broken_internal_links",
            "reason": (
                f"{len(broken)} broken target(s) at {rate:.1%} is below the reporting floor of "
                f"{max_count} links or {max_rate:.0%}. A handful of stale links is normal "
                f"maintenance, not a discoverability defect."
            ),
            "confidence_effect": "suppressed by threshold",
        })

    # ---------------------------------------------------- transport security
    insecure = []
    for name, record in _headers_iter(b):
        if record.get("tls", {}).get("error"):
            insecure.append((record["url"], f"TLS error: {record['tls']['error']}"))
    http_pages = [p["url"] for p in b.pages if p["url"].startswith("http://")]
    if http_pages:
        insecure.append((http_pages[0], f"{len(http_pages)} page(s) served over plain http"))
    if insecure:
        findings.append(finding(
            check_id="reach.http.insecure_or_mixed_scheme",
            title="Transport security problems affect how crawlers and browsers treat the site",
            severity="high", confidence="confirmed", stage="reach",
            category="discoverability", scope="site",
            evidence="; ".join(f"{u}: {why}" for u, why in insecure[:5]),
            affected_urls=[u for u, _ in insecure],
            action=action(
                summary="Serve the whole site over HTTPS with a valid certificate chain.",
                effort="medium",
                mechanism=(
                    "Crawlers and browsers downgrade or refuse content over a broken transport, so "
                    "the page may never be read even though the server answered."
                ),
                source="RFC 9110 section 17",
                patch="# Redirect all http:// requests to https:// with a single 301.",
                verification=f"curl -sI {insecure[0][0]} | head -1",
            ),
        ))

    # ------------------------------------------------------------- latency
    samples = [float(s) for s in (b.probes.get("ttfb_samples_ms") or [])]
    limit = threshold(profile, "ttfb_median_ms_max", 800)
    if len(samples) < 3:
        skipped.append({
            "check_id": "reach.perf.slow_median_ttfb",
            "reason": (
                f"only {len(samples)} TTFB sample(s) collected; this check requires at least 3 so "
                f"it never fires on a single transient measurement."
            ),
            "confidence_effect": "not assessed",
        })
    else:
        med = statistics.median(samples)
        if med > limit:
            findings.append(finding(
                check_id="reach.perf.slow_median_ttfb",
                title=f"Median time to first byte is {med:.0f} ms",
                severity="low", confidence="confirmed", stage="reach",
                category="discoverability", scope="site",
                evidence=(
                    f"Median of {len(samples)} samples is {med:.0f} ms against a threshold of "
                    f"{limit} ms. All samples: {', '.join(f'{s:.0f}' for s in samples)} ms. "
                    f"Reported as a median, not a maximum, so one slow response does not fire it."
                ),
                affected_urls=[b.origin + "/"],
                action=action(
                    summary="Reduce server response time, or put a CDN in front of the origin.",
                    effort="medium",
                    mechanism=(
                        "Crawlers allocate a time budget per host; a slow origin means fewer pages "
                        "fetched per visit, so deep pages are refreshed less often."
                    ),
                    source="Google Search Central, Crawl budget management for large sites",
                    patch="# No markup patch: this is a server or CDN configuration change.",
                    verification=(
                        f"for i in 1 2 3; do curl -s -o /dev/null -w '%{{time_starttransfer}}\\n' "
                        f"{b.origin}/; done  # take the median"
                    ),
                ),
            ))

    # ------------------------------------------------------------ sitemap
    fetched = b.sitemap.get("fetched") or []
    good = [f for f in fetched if f.get("status") == 200 and f.get("type") in ("urlset", "index")]
    if not good:
        tried = ", ".join(f"{f['url']} -> {f.get('status')}" for f in fetched[:3]) or "no candidates"
        if len(b.pages) < 15:
            skipped.append({
                "check_id": "reach.sitemap.absent_or_invalid",
                "reason": (
                    f"no valid sitemap, but only {len(b.pages)} pages were discovered. A sitemap "
                    f"adds little on a site this small and its absence is not a defect."
                ),
                "confidence_effect": "suppressed by threshold",
            })
        else:
            findings.append(finding(
                check_id="reach.sitemap.absent_or_invalid",
                title="No valid XML sitemap was found",
                severity="medium", confidence="confirmed", stage="reach",
                category="discoverability", scope="site",
                evidence=(
                    f"Tried: {tried}. "
                    + "; ".join(f"{f['url']}: {f.get('parse_error')}" for f in fetched if f.get("parse_error"))
                ),
                affected_urls=[b.origin + "/sitemap.xml"],
                action=action(
                    summary="Publish an XML sitemap and declare it in robots.txt.",
                    effort="low",
                    mechanism=(
                        "A sitemap gives a crawler a complete URL list without relying on following "
                        "every internal link, so pages that are weakly linked still get discovered."
                    ),
                    source="sitemaps.org protocol 0.9",
                    patch=(
                        '<?xml version="1.0" encoding="UTF-8"?>\n'
                        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                        + "".join(
                            f"  <loc>{p['url']}</loc>\n" for p in b.html_pages()[:5]
                        )
                        + "</urlset>\n"
                        + f"\n# and in robots.txt:\nSitemap: {b.origin}/sitemap.xml\n"
                    ),
                    verification=f"curl -s {b.origin}/sitemap.xml | head -3",
                ),
            ))
    else:
        listed = {e["loc"] for e in (b.sitemap.get("entries") or [])}
        discovered = {p["url"] for p in b.html_pages()}
        missing = sorted(discovered - listed)
        gap_ratio = len(missing) / max(len(discovered), 1)
        coverage = b.sitemap.get("coverage", {})
        distinct = coverage.get("lastmod_distinct_values", 0)
        useless_lastmod = coverage.get("listed", 0) > 3 and distinct <= 1
        limit_ratio = threshold(profile, "sitemap_coverage_gap_ratio", 0.4)
        if gap_ratio > limit_ratio or useless_lastmod:
            reasons = []
            if gap_ratio > limit_ratio:
                reasons.append(
                    f"{len(missing)} of {len(discovered)} crawled pages ({gap_ratio:.0%}) are not "
                    f"listed, for example {', '.join(missing[:3])}"
                )
            if useless_lastmod:
                reasons.append(
                    f"all {coverage.get('listed')} entries share {distinct} distinct lastmod "
                    f"value(s), so lastmod carries no information about what changed"
                )
            findings.append(finding(
                check_id="reach.sitemap.coverage_gap",
                title="The sitemap does not usefully describe the site",
                severity="low", confidence="confirmed", stage="reach",
                category="discoverability", scope="site",
                evidence="; ".join(reasons),
                affected_urls=[b.origin + "/sitemap.xml"],
                action=action(
                    summary="Regenerate the sitemap from the live route list with real lastmod values.",
                    effort="low",
                    mechanism=(
                        "Crawlers use lastmod to decide what to re-fetch; a constant or absent value "
                        "gives them nothing to prioritise, so changed pages are refreshed no sooner "
                        "than unchanged ones."
                    ),
                    source="sitemaps.org protocol 0.9",
                    patch="\n".join(f"  <url><loc>{u}</loc></url>" for u in missing[:5]),
                    verification=f"curl -s {b.origin}/sitemap.xml | grep -c '<loc>'",
                ),
            ))

    return findings, skipped, proactive


def _headers_iter(b):
    directory = b.root / "headers"
    if not directory.exists():
        return []
    import json as _json

    out = []
    for path in sorted(directory.glob("*.json")):
        try:
            out.append((path.name, _json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError):
            continue
    return out
