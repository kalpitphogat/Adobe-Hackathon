#!/usr/bin/env python3
"""Stage trust: would a machine believe this page is current?"""

from __future__ import annotations

import datetime as dt
import re

from bundle import action, finding, threshold

CHECKS = [
    {"id": "trust.date.absent_on_dated_content", "stage": "trust", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "trust-freshness-audit"},
    {"id": "trust.date.signals_disagree", "stage": "trust", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "trust-freshness-audit"},
    {"id": "trust.date.stale_volatile_facts", "stage": "trust", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "trust-freshness-audit"},
]

DATED_TYPES = {"article", "docs"}
VOLATILE = re.compile(
    r"\b(price|pricing|per month|per year|currently|as of|latest|newest|this year|"
    r"opening hours|in stock|available now|current version|roadmap)\b", re.I
)
ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
TEXT_DATE = re.compile(
    r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b"
    r"|\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b",
    re.I,
)
MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}


def parse_any(value) -> dt.date | None:
    if not value:
        return None
    s = str(value)
    m = ISO.search(s)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = TEXT_DATE.search(s)
    if m:
        try:
            if m.group(1):
                return dt.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
            return dt.date(int(m.group(6)), MONTHS[m.group(4).lower()], int(m.group(5)))
        except (ValueError, KeyError):
            return None
    try:
        import email.utils

        parsed = email.utils.parsedate_to_datetime(s)
        return parsed.date() if parsed else None
    except (TypeError, ValueError, IndexError):
        return None


def schema_dates(page: dict) -> tuple[str | None, str | None]:
    published = modified = None

    def walk(node) -> None:
        nonlocal published, modified
        if isinstance(node, dict):
            published = published or node.get("datePublished") or node.get("dateCreated")
            modified = modified or node.get("dateModified")
            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk((page.get("markup") or {}).get("jsonld") or [])
    return published, modified


def visible_date(page: dict, text: str) -> str | None:
    head = text[:600]
    m = TEXT_DATE.search(head) or ISO.search(head)
    return m.group(0) if m else None


def today(b) -> dt.date:
    stamp = parse_any(b.meta.get("audited_at"))
    return stamp or dt.date.today()


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []
    stale_days = threshold(profile, "stale_volatile_days", 540)
    now = today(b)

    undated = []
    disagreements = []
    stale = []

    for page in b.html_pages():
        page_type = b.page_type(page, profile)
        text = b.observed_text(page)
        published, modified = schema_dates(page)
        visible = visible_date(page, text)
        dates = page.get("dates") or {}
        http_lm = dates.get("http_last_modified")
        sitemap_lm = dates.get("sitemap_lastmod")

        signals = {
            "schema datePublished": parse_any(published),
            "schema dateModified": parse_any(modified),
            "visible on page": parse_any(visible),
            "sitemap lastmod": parse_any(sitemap_lm),
            "Last-Modified header": parse_any(http_lm),
        }
        present = {k: v for k, v in signals.items() if v}

        # ---------------------------------------------------- absent
        if page_type in DATED_TYPES and not (published or modified or visible):
            undated.append(page)

        # ------------------------------------------------ disagreement
        if len(present) >= 2:
            values = sorted(present.values())
            spread = (values[-1] - values[0]).days
            if spread > 2:
                disagreements.append((page, present, spread))

        # ------------------------------------------------------- stale
        newest = max(present.values()) if present else None
        if newest and VOLATILE.search(text):
            age = (now - newest).days
            if age > stale_days:
                phrase = VOLATILE.search(text)
                stale.append((page, newest, age, phrase.group(0) if phrase else ""))

    if undated:
        findings.append(finding(
            check_id="trust.date.absent_on_dated_content",
            title=f"{len(undated)} page(s) of dated content carry no date at all",
            severity="medium", confidence="confirmed", stage="trust",
            category="discoverability", scope="url",
            evidence=(
                f"No schema datePublished or dateModified and no visible date in the first 600 "
                f"characters on: {', '.join(p['url'] for p in undated[:5])}. These are "
                f"{'/'.join(sorted({b.page_type(p, profile) for p in undated}))} pages, where a "
                f"reader has to judge whether the content is still current and has nothing to "
                f"judge from."
            ),
            affected_urls=[p["url"] for p in undated],
            action=action(
                summary="Publish datePublished and dateModified, and show the date on the page.",
                effort="low",
                mechanism=(
                    "Freshness is weighed when choosing between sources saying different things; "
                    "an undated page cannot compete with a dated one on that axis."
                ),
                source="schema.org/Article datePublished",
                patch=(
                    '<script type="application/ld+json">\n'
                    "{\n"
                    '  "@context": "https://schema.org",\n'
                    '  "@type": "Article",\n'
                    f'  "headline": {(undated[0].get("title") or "__FILL_IN__:headline")!r},\n'
                    '  "datePublished": "__FILL_IN__:YYYY-MM-DD",\n'
                    '  "dateModified": "__FILL_IN__:YYYY-MM-DD"\n'
                    "}\n"
                    "</script>\n"
                    '<p>Published <time datetime="__FILL_IN__:YYYY-MM-DD">__FILL_IN__:readable_date</time></p>'
                ),
                verification=f"curl -s {undated[0]['url']} | grep -o 'datePublished[^,]*'",
            ),
        ))

    if disagreements:
        findings.append(finding(
            check_id="trust.date.signals_disagree",
            title=f"{len(disagreements)} page(s) report conflicting dates",
            severity="medium", confidence="confirmed", stage="trust",
            category="discoverability", scope="url",
            evidence="; ".join(
                f"{p['url']} spans {spread} days: "
                + ", ".join(f"{k} = {v.isoformat()}" for k, v in sorted(present.items()))
                for p, present, spread in disagreements[:4]
            )
            + ". A spread of two days or less is treated as publishing lag and is not reported.",
            affected_urls=[p["url"] for p, _, _ in disagreements],
            action=action(
                summary="Drive every date signal from one source of truth.",
                effort="medium",
                mechanism=(
                    "When a page states several different dates, a reader has no basis to choose "
                    "between them, so none of them carries weight."
                ),
                source="schema.org/Article; sitemaps.org lastmod",
                patch=(
                    "# Emit schema dateModified, the sitemap lastmod and the Last-Modified header\n"
                    "# from the same stored value, so they cannot drift."
                ),
                verification=(
                    f"curl -sI {disagreements[0][0]['url']} | grep -i last-modified; "
                    f"curl -s {disagreements[0][0]['url']} | grep -o 'dateModified[^,]*'"
                ),
            ),
        ))

    if stale:
        findings.append(finding(
            check_id="trust.date.stale_volatile_facts",
            title=f"{len(stale)} page(s) state time-sensitive facts but have not been updated",
            severity="medium", confidence="likely", stage="trust",
            category="discoverability", scope="url",
            evidence="; ".join(
                f"{p['url']} last dated {d.isoformat()} ({age} days ago) while containing the "
                f"time-sensitive phrase {phrase!r}"
                for p, d, age, phrase in stale[:4]
            )
            + f". The staleness window for this archetype is {stale_days} days.",
            affected_urls=[p["url"] for p, _, _, _ in stale],
            action=action(
                summary="Review these pages and refresh dateModified when the facts are confirmed.",
                effort="low",
                mechanism=(
                    "A page asserting a current price or hours, last touched years ago, is a "
                    "weaker source than a recently confirmed one making the same claim."
                ),
                source="schema.org/Article dateModified",
                patch='"dateModified": "__FILL_IN__:YYYY-MM-DD"  <!-- update when the facts are re-confirmed -->',
                verification=f"curl -s {stale[0][0]['url']} | grep -o 'dateModified[^,]*'",
            ),
        ))

    return findings, skipped, []
