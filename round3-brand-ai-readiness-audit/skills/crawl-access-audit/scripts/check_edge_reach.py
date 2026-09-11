#!/usr/bin/env python3
"""Stage reach: edge and CDN reachability for AI crawler user agents.

This is the highest-value finding in the whole audit when it fires - a WAF that
403s retrieval crawlers is invisible in robots.txt and invisible to a human
browsing the site - and it is OFF BY DEFAULT.

Probing requires --probe-bot-ua at collection time. Without it, we say so in
limitations rather than guessing, and fall back to a CDN header fingerprint at
hypothesis confidence, which is honest about being an inference.
"""

from __future__ import annotations

from bundle import action, finding

CHECKS = [
    {"id": "reach.edge.bot_ua_blocked", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "critical", "skill": "crawl-access-audit"},
    {"id": "reach.edge.bot_ua_challenged", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "high", "skill": "crawl-access-audit"},
]

BLOCKING_STATUSES = {401, 403, 405, 406, 429, 503}

# Collected by run.py into the report's limitations[]. Not a proactive
# recommendation: a blind spot is not an improvement suggestion.
LIMITATIONS: list[dict] = []


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []
    reach = b.probes.get("bot_reach") or {}

    if not reach.get("enabled"):
        reason = reach.get("reason") or "bot user-agent probing was not enabled"
        for check_id in ("reach.edge.bot_ua_blocked", "reach.edge.bot_ua_challenged"):
            skipped.append({
                "check_id": check_id,
                "reason": (
                    f"{reason}. Edge and CDN reachability for named AI crawlers was NOT assessed, "
                    f"and this is the single highest-value check in the audit. A WAF or CDN rule "
                    f"that refuses AI crawlers is invisible in robots.txt and invisible to anyone "
                    f"browsing the site normally, so a brand can be entirely absent from AI answers "
                    f"with nothing on the site to show why. THIS IS A BLIND SPOT, NOT A PASS. "
                    f"To assess it, re-run with --probe-bot-ua, which sends one request per crawler "
                    f"to the homepage only, with our auditor token appended to the user-agent so "
                    f"your logs show it was an audit. Use it on sites you own or have permission "
                    f"to test."
                ),
                "confidence_effect": "not assessed",
            })
        LIMITATIONS.clear()
        LIMITATIONS.append({
            "scope": "site",
            "reason": (
                "Edge and CDN reachability for named AI crawlers was not assessed, because "
                "--probe-bot-ua was not set. This is the highest-value check in this marketplace: "
                "a CDN or WAF rule that returns 403 to OAI-SearchBot, PerplexityBot or "
                "Claude-SearchBot removes a brand from those assistants entirely, and leaves no "
                "trace in robots.txt or in what a human sees. If you own this site, re-run the "
                "orchestrator with the --probe-bot-ua flag:\n"
                "    orchestrate.py <url> --out ./audit-output --probe-bot-ua\n"
                "That sends ONE request per crawler, to the homepage only, with an auditor token "
                "appended to the user-agent string so it is identifiable in your logs. It is off "
                "by default because sending named-crawler user-agents to a site you do not own is "
                "not something an audit should do without being asked."
            ),
            "checks_not_run": ["reach.edge.bot_ua_blocked", "reach.edge.bot_ua_challenged"],
            "confidence_effect": "not assessed; re-run with --probe-bot-ua to close this gap",
            # An opt-in check that was not opted into is not a DEGRADATION: the
            # audit ran exactly as configured. Marking it stops every report
            # downgrading itself to "partial" and rendering that status useless.
            "optional_feature": True,
        })
        return findings, skipped, []

    baseline = reach.get("baseline_status")
    results = reach.get("results") or []
    blocked = [r for r in results if r.get("status") in BLOCKING_STATUSES]
    challenged = [r for r in results if r.get("challenged") and r.get("status") not in BLOCKING_STATUSES]

    # SUPPRESS: if the site refuses our honest baseline too, this is not
    # bot-specific targeting, it is a site that refuses everything.
    if baseline in BLOCKING_STATUSES:
        skipped.append({
            "check_id": "reach.edge.bot_ua_blocked",
            "reason": (
                f"the baseline request with our own user agent also returned HTTP {baseline}, so "
                f"the refusal is not specific to AI crawlers and reporting it as bot targeting "
                f"would be wrong."
            ),
            "confidence_effect": "suppressed by design",
        })
        return findings, skipped, []

    if blocked:
        table = "; ".join(
            f"{r['bot']} -> HTTP {r['status']}"
            + (f" (server: {r['server']})" if r.get("server") else "")
            for r in blocked
        )
        findings.append(finding(
            check_id="reach.edge.bot_ua_blocked",
            title=f"The edge refuses {len(blocked)} AI crawler user agent(s) that a browser is served",
            severity="critical", confidence="confirmed", stage="reach",
            category="discoverability", scope="site",
            evidence=(
                f"A request to {b.origin}/ with a normal user agent returned HTTP {baseline}, but "
                f"{table}. The user agent sent carried our auditor token appended, for example "
                f"\"{blocked[0].get('user_agent_sent', '')}\". robots.txt does not mention these "
                f"agents, so this block is at the CDN or WAF and is invisible both in robots.txt "
                f"and to anyone browsing the site normally."
            ),
            affected_urls=[b.origin + "/"],
            action=action(
                summary=f"Allowlist {', '.join(sorted(r['bot'] for r in blocked))} at the CDN or WAF.",
                effort="medium",
                mechanism=(
                    "The request never reaches the origin, so robots.txt, structured data and page "
                    "quality are all irrelevant: the crawler is refused before it can read anything."
                ),
                source="references/ai-bots.json; vendor crawler documentation",
                patch=(
                    "# Cloudflare: Security > WAF > Tools > User Agent Blocking, or a custom rule:\n"
                    "#   (http.user_agent contains \""
                    + blocked[0]["bot"]
                    + "\") -> Skip (all remaining custom rules)\n"
                    "# Verify against published IP ranges rather than trusting the UA string alone."
                ),
                verification=(
                    f"curl -A '{blocked[0]['bot']}/1.0' -I {b.origin}/ | head -1  "
                    f"# expect HTTP 200, currently {blocked[0]['status']}"
                ),
            ),
        ))

    if challenged:
        findings.append(finding(
            check_id="reach.edge.bot_ua_challenged",
            title=f"{len(challenged)} AI crawler user agent(s) receive an interstitial instead of content",
            severity="high", confidence="confirmed", stage="reach",
            category="discoverability", scope="site",
            evidence=(
                "; ".join(
                    f"{r['bot']} -> HTTP {r['status']} but the body is a challenge page "
                    f"({r['wordcount']} words)"
                    for r in challenged
                )
                + ". A 200 with a challenge body is worse than a clean refusal, because the "
                  "crawler may store the interstitial as if it were the page."
            ),
            affected_urls=[b.origin + "/"],
            action=action(
                summary="Exempt verified AI crawlers from the bot challenge.",
                effort="medium",
                mechanism=(
                    "A JavaScript challenge is designed to be solved by a browser; a crawler that "
                    "does not execute it stores the challenge text as the page content."
                ),
                source="references/ai-bots.json",
                patch="# Add a WAF skip rule for verified crawler IP ranges before the challenge rule.",
                verification=f"curl -A '{challenged[0]['bot']}/1.0' -s {b.origin}/ | head -c 400",
            ),
        ))

    return findings, skipped, []
