#!/usr/bin/env python3
"""Stage reach: robots.txt policy checks.

The question this file answers is not "does robots.txt block anything" but
"does robots.txt block something whose blocking actually costs the brand
visibility". Those are different questions, and conflating them is the single
most common false positive in this field: a site that blocks GPTBot has made a
content-licensing decision, not a mistake, and reporting it as a defect wastes
the reader's attention on a choice they already made deliberately.

Bot classification comes from references/ai-bots.json, a dated snapshot.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from bundle import action, finding

REFERENCES = Path(__file__).resolve().parent.parent / "references"

CHECKS = [
    {"id": "reach.robots.ai_search_bot_blocked", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "critical", "skill": "crawl-access-audit"},
    {"id": "reach.robots.blanket_disallow", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "critical", "skill": "crawl-access-audit"},
    {"id": "reach.robots.ai_training_bot_blocked", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "info", "skill": "crawl-access-audit"},
    {"id": "reach.robots.dual_purpose_bot_blocked", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "crawl-access-audit"},
    {"id": "reach.robots.unparseable", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "crawl-access-audit"},
    {"id": "reach.robots.crawl_delay_excessive", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "crawl-access-audit"},
]


def load_bots() -> dict:
    return json.loads((REFERENCES / "ai-bots.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------- RFC 9309

def _pattern_to_regex(pattern: str) -> re.Pattern[str]:
    parts: list[str] = []
    last = len(pattern) - 1
    for i, ch in enumerate(pattern):
        if ch == "*":
            parts.append(".*")
        elif ch == "$" and i == last:
            parts.append(r"\Z")
        else:
            parts.append(re.escape(ch))
    return re.compile("".join(parts))


def parse_groups(text: str) -> tuple[list[dict], list[str]]:
    """Parse robots.txt into groups. Mirrors site-evidence-collector's matcher.

    Duplicated rather than imported: no script may reach into a sibling skill
    folder. See references/skill-cli-contract.md.
    """
    groups: list[dict] = []
    errors: list[str] = []
    current: dict | None = None
    accepting = False
    for line_no, raw in enumerate(text.lstrip("﻿").splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            errors.append(f"line {line_no}: no field separator in {raw.strip()!r}")
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if not value:
                errors.append(f"line {line_no}: empty user-agent value")
                continue
            if current is None or not accepting:
                current = {"agents": [], "rules": [], "crawl_delay": None,
                           "crawl_delay_line": None, "crawl_delay_raw": None}
                groups.append(current)
                accepting = True
            current["agents"].append(value)
        elif key in ("allow", "disallow"):
            if current is None:
                errors.append(f"line {line_no}: {key} outside any user-agent group")
                continue
            accepting = False
            current["rules"].append(
                {"allow": key == "allow", "pattern": value, "line": line_no, "raw": raw.rstrip()}
            )
        elif key == "crawl-delay":
            if current is None:
                errors.append(f"line {line_no}: crawl-delay outside any user-agent group")
                continue
            accepting = False
            try:
                current["crawl_delay"] = float(value)
                current["crawl_delay_line"] = line_no
                current["crawl_delay_raw"] = raw.strip()
            except ValueError:
                errors.append(f"line {line_no}: non-numeric crawl-delay {value!r}")
        elif key == "sitemap":
            pass
        else:
            pass
    return groups, errors


def group_for(groups: list[dict], token: str) -> dict | None:
    best = None
    wildcard = None
    lowered = token.lower()
    for group in groups:
        for agent in group["agents"]:
            a = agent.lower()
            if a == "*":
                wildcard = wildcard or group
            elif a in lowered or lowered in a:
                if best is None or len(a) > len(best[0]):
                    best = (a, group)
    return best[1] if best else wildcard


def decide(group: dict | None, path: str) -> dict | None:
    """Longest-match rule for one path, or None if nothing matches."""
    if group is None:
        return None
    best = None
    for rule in group["rules"]:
        if not rule["pattern"]:
            continue
        if _pattern_to_regex(rule["pattern"]).match(path):
            if (
                best is None
                or len(rule["pattern"]) > len(best["pattern"])
                or (len(rule["pattern"]) == len(best["pattern"]) and rule["allow"] and not best["allow"])
            ):
                best = rule
    return best


def blocked_paths(group: dict, sample_paths: list[str]) -> list[str]:
    out = []
    for path in sample_paths:
        rule = decide(group, path)
        if rule is not None and not rule["allow"]:
            out.append(path)
    return out


# ----------------------------------------------------------------- checks


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    """Returns (findings, skipped, proactive)."""
    findings: list[dict] = []
    skipped: list[dict] = []
    bots = load_bots()
    text = b.robots_text
    status = b.meta.get("crawl", {}).get("robots_status")
    snapshot = f"{bots['snapshot_date']} (upstream commit {bots['source']['commit'][:12]})"

    is_2xx = bool(status and 200 <= status < 300)
    looks_like_html = "<html" in text[:400].lower() or "<!doctype" in text[:400].lower()

    # An ABSENT robots.txt is permissive and correct, and absence is signalled by a
    # non-2xx status EVEN WHEN the server returns an HTML error page as the body. A
    # 404 whose body is a styled "Not Found" page is "no robots.txt", not an
    # "unparseable robots.txt" — treating it as a defect is a false positive that
    # fires on a large share of ordinary sites. Only a 2xx response is a robots.txt
    # whose content we are entitled to expect to parse.
    if not is_2xx:
        if looks_like_html or not text.strip() or (status and status >= 300):
            return findings, skipped, []
        # status unknown and the body is non-HTML: fall through and try to parse it.

    if not text.strip():
        if is_2xx:
            findings.append(_unparseable_finding(b, "robots.txt returned 200 with an empty body", status))
        return findings, skipped, []

    groups, errors = parse_groups(text)
    sample_paths = sorted({
        "/" + p["url"].split("://", 1)[-1].split("/", 1)[-1] if "/" in p["url"].split("://", 1)[-1] else "/"
        for p in b.pages
    }) or ["/"]

    # ---- unparseable / not actually robots.txt (only meaningful for a 2xx response)
    if looks_like_html or (errors and not groups):
        if is_2xx:
            findings.append(
                _unparseable_finding(
                    b,
                    "body is HTML, not a robots.txt directive file" if looks_like_html
                    else "; ".join(errors[:5]),
                    status,
                )
            )
        return findings, skipped, []

    # ---- blanket disallow
    for group in groups:
        if "*" not in [a.lower() for a in group["agents"]]:
            continue
        root = next((r for r in group["rules"] if not r["allow"] and r["pattern"] == "/"), None)
        if root and not any(r["allow"] and len(r["pattern"]) > 1 for r in group["rules"]):
            findings.append(finding(
                check_id="reach.robots.blanket_disallow",
                title="robots.txt forbids every crawler from the entire site",
                severity="critical", confidence="confirmed", stage="reach",
                category="discoverability", scope="site",
                evidence=(
                    f"robots.txt at {b.origin}/robots.txt contains a wildcard group with "
                    f"\"{root['raw']}\" on line {root['line']} and no narrower Allow rule that "
                    f"re-admits content. Every crawler, including every AI retrieval bot, is "
                    f"excluded from all {len(sample_paths)} discovered paths. This auditor "
                    f"honoured it and fetched no page content."
                ),
                affected_urls=[b.origin + "/"],
                action=action(
                    summary="Replace the site-wide Disallow with rules that exclude only genuinely private paths.",
                    effort="low",
                    mechanism=(
                        "A crawler that is refused at robots.txt never requests the page, so no "
                        "amount of on-page quality can compensate; this is the first of the three "
                        "steps that must succeed in order."
                    ),
                    source="RFC 9309 section 2.2.2",
                    patch=(
                        "User-agent: *\n"
                        "Disallow: /admin/\n"
                        "Disallow: /cart/\n"
                        "Disallow: /checkout/\n"
                        "Allow: /\n"
                        f"\nSitemap: {b.origin}/sitemap.xml\n"
                    ),
                    verification=f"curl -s {b.origin}/robots.txt | grep -A5 'User-agent: \\*'",
                ),
            ))
            break

    # ---- per-bot classification
    by_category: dict[str, list[dict]] = {"retrieval": [], "training": [], "dual_purpose": []}
    for bot in bots["bots"]:
        group = group_for(groups, bot["token"])
        if group is None:
            continue
        # Only count a group that names this bot explicitly, or the wildcard
        # group when it blocks. A wildcard block is already reported above.
        named = any(a.lower() == bot["token"].lower() for a in group["agents"])
        if not named:
            continue
        blocked = blocked_paths(group, sample_paths)
        if not blocked:
            continue
        rule = decide(group, "/")
        by_category[bot["category"]].append(
            {"bot": bot, "rule": rule, "blocked": blocked, "group": group}
        )

    retrieval = by_category["retrieval"]
    training = by_category["training"]
    dual = by_category["dual_purpose"]

    if retrieval:
        names = sorted(r["bot"]["token"] for r in retrieval)
        lines = "; ".join(
            f"{r['bot']['token']} blocked by \"{r['rule']['raw']}\" (line {r['rule']['line']})"
            for r in sorted(retrieval, key=lambda r: r["bot"]["token"])
            if r["rule"]
        )
        allowed_note = (
            f"{len(training)} training-only bot(s) are also blocked, which is a separate and "
            f"legitimate licensing choice."
            if training else ""
        )
        findings.append(finding(
            check_id="reach.robots.ai_search_bot_blocked",
            title=f"robots.txt blocks {len(names)} AI retrieval crawler(s) that cite sources at answer time",
            severity="critical", confidence="confirmed", stage="reach",
            category="discoverability", scope="site",
            evidence=(
                f"{lines}. Each of these fetches pages at answer time to ground or cite a "
                f"response, so blocking them removes this brand from those assistants' answers "
                f"entirely. {len(retrieval[0]['blocked'])} of {len(sample_paths)} discovered paths "
                f"are disallowed for these agents. Bot classification from a snapshot dated "
                f"{snapshot}. {allowed_note}"
            ).strip(),
            affected_urls=[b.origin + "/"],
            action=action(
                summary=f"Allow {', '.join(names)} in robots.txt, keeping any training-bot policy separate.",
                effort="low",
                mechanism=(
                    "Retrieval crawlers fetch the page at the moment a user asks a question; if "
                    "they are refused, the brand cannot appear as a source no matter how good the "
                    "page is."
                ),
                source="RFC 9309 section 2.2.2; vendor crawler documentation per references/ai-bots.json",
                patch="".join(f"User-agent: {n}\nAllow: /\n\n" for n in names).rstrip() + "\n",
                verification=(
                    f"curl -s {b.origin}/robots.txt and confirm each of {', '.join(names)} "
                    f"has an Allow rule that is at least as specific as any Disallow"
                ),
            ),
        ))

    if training:
        names = sorted(t["bot"]["token"] for t in training)
        findings.append(finding(
            check_id="reach.robots.ai_training_bot_blocked",
            title=f"robots.txt blocks {len(names)} training-only crawler(s) — recorded as an observation, not a defect",
            severity="info", confidence="confirmed", stage="reach",
            category="discoverability", scope="site",
            evidence=(
                f"Blocked: {', '.join(names)}. These collect content for model training corpora, "
                f"not for answering questions at retrieval time. Blocking them does not reduce "
                f"whether this brand is found or cited by AI assistants. "
                + (
                    "The retrieval crawlers that do affect citation are allowed."
                    if not retrieval
                    else "Retrieval crawlers are separately blocked and are reported above as the real problem."
                )
                + f" Classification from a snapshot dated {snapshot}."
            ),
            affected_urls=[b.origin + "/"],
            action=action(
                summary="No change required. This is a content-licensing decision, and we report it only so it is visible.",
                effort="low",
                mechanism=(
                    "Training-corpus collection and answer-time retrieval are separate pipelines "
                    "with separate user-agent tokens; blocking the former does not affect the latter."
                ),
                source="references/bot-taxonomy.md",
                patch="",
                verification="No action to verify. Revisit only if the site's licensing stance changes.",
            ),
        ))

    if dual:
        names = sorted(d["bot"]["token"] for d in dual)
        notes = " ".join(d["bot"]["note"] for d in sorted(dual, key=lambda d: d["bot"]["token"]))
        findings.append(finding(
            check_id="reach.robots.dual_purpose_bot_blocked",
            title=f"robots.txt blocks {len(names)} crawler(s) whose role is contested",
            severity="medium", confidence="likely", stage="reach",
            category="discoverability", scope="site",
            evidence=(
                f"Blocked: {', '.join(names)}. These are genuinely contested rather than clearly "
                f"training-only or clearly retrieval. {notes} We report this as a trade-off the "
                f"site may have chosen deliberately, not as an error. Snapshot {snapshot}."
            ),
            affected_urls=[b.origin + "/"],
            action=action(
                summary=f"Decide deliberately whether the AI-surface exposure {', '.join(names)} controls is wanted.",
                effort="low",
                mechanism=(
                    "These tokens modify how already-crawled content may be used on AI surfaces "
                    "rather than whether the page can be fetched, so the cost is exposure, not access."
                ),
                source="references/bot-taxonomy.md",
                patch="",
                verification="No mechanical check; this is a policy decision to record, not a defect to fix.",
            ),
        ))

    # ---- crawl-delay
    honoured = set(bots["crawl_delay_honoured_by"]["honours"])
    ignored = set(bots["crawl_delay_honoured_by"]["ignores"])
    retrieval_tokens = {x["token"] for x in bots["bots"] if x["category"] == "retrieval"}
    page_count = max(len(b.pages), len(b.sitemap.get("entries", [])) or 0, 1)

    for group in groups:
        delay = group.get("crawl_delay")
        if not delay or delay <= 2:
            continue
        agents = [a for a in group["agents"]]
        # SUPPRESS: only fires when the directive reaches a retrieval-relevant bot.
        reaches_retrieval = any(
            a == "*" or any(a.lower() == t.lower() for t in retrieval_tokens) for a in agents
        )
        if not reaches_retrieval:
            skipped.append({
                "check_id": "reach.robots.crawl_delay_excessive",
                "reason": (
                    f"Crawl-delay {delay} applies only to {', '.join(agents)}, none of which we "
                    f"classify as retrieval-relevant. Setting a crawl delay for a non-retrieval "
                    f"agent is a deliberate, supported choice."
                ),
                "confidence_effect": "not assessed",
            })
            continue
        implied_hours = (delay * page_count) / 3600.0
        affected_named = sorted(a for a in agents if a != "*")
        findings.append(finding(
            check_id="reach.robots.crawl_delay_excessive",
            title=f"Crawl-delay of {delay:g}s would take {implied_hours:.1f} hours to crawl this site once",
            severity="medium" if page_count >= 50 else "low",
            confidence="confirmed", stage="reach",
            category="discoverability", scope="site",
            evidence=(
                f"\"{group['crawl_delay_raw']}\" on line {group['crawl_delay_line']} applies to "
                f"{', '.join(agents)}. At {delay:g}s between requests, one full pass over "
                f"{page_count} known URLs takes about {implied_hours:.1f} hours. "
                f"Crawl-delay is not part of RFC 9309: "
                f"{', '.join(sorted(honoured))} honour it, {', '.join(sorted(ignored))} ignore it, "
                f"and the AI retrieval crawlers "
                f"({', '.join(bots['crawl_delay_honoured_by']['unknown'][:3])}) have not documented "
                f"their behaviour. So the effect is real but uneven."
            ),
            affected_urls=[b.origin + "/"],
            action=action(
                summary="Lower Crawl-delay to 1-2s, or scope it to the specific agents that were causing load.",
                effort="low",
                mechanism=(
                    "A crawler that can only fetch one page every few seconds will not complete a "
                    "pass over a large site before its next scheduled crawl, so deep pages are "
                    "never refreshed."
                ),
                source="RFC 9309 (Crawl-delay is not specified); references/ai-bots.json",
                patch=(
                    f"User-agent: {affected_named[0] if affected_named else '*'}\n"
                    f"Crawl-delay: 1\n"
                ),
                verification=f"curl -s {b.origin}/robots.txt | grep -i crawl-delay",
            ),
        ))
        break

    if errors and groups:
        findings.append(_unparseable_finding(b, "; ".join(errors[:5]), status, severity="low"))

    return findings, skipped, []


def _unparseable_finding(b, reason: str, status, severity: str = "medium") -> dict:
    return finding(
        check_id="reach.robots.unparseable",
        title="robots.txt could not be parsed as a directive file",
        severity=severity, confidence="confirmed", stage="reach",
        category="discoverability", scope="site",
        evidence=(
            f"{b.origin}/robots.txt returned HTTP {status}. {reason}. A crawler that cannot parse "
            f"robots.txt may apply its own fallback, and different crawlers fall back differently, "
            f"so the site's actual crawl policy becomes unpredictable."
        ),
        affected_urls=[b.origin + "/robots.txt"],
        action=action(
            summary="Serve a plain-text robots.txt with valid directives and content-type text/plain.",
            effort="low",
            mechanism=(
                "Crawlers parse robots.txt line by line before requesting anything else; an "
                "unparseable file makes every later access decision undefined."
            ),
            source="RFC 9309 section 2.3",
            patch=f"User-agent: *\nAllow: /\n\nSitemap: {b.origin}/sitemap.xml\n",
            verification=f"curl -sI {b.origin}/robots.txt  # expect 200 and content-type: text/plain",
        ),
    )
