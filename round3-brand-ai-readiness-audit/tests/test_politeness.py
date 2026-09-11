#!/usr/bin/env python3
"""RFC 9309 conformance tests for the robots.txt matcher.

Cases are taken from RFC 9309 section 2.2.2 ("Special Characters" and the
precedence examples) plus the documented Google matcher behaviour that the RFC
codified. Standard library only; no network.

Run: python tests/test_politeness.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "site-evidence-collector" / "scripts"))

import politeness  # noqa: E402

FAILURES: list[str] = []
COUNT = 0


def expect(condition: bool, label: str) -> None:
    global COUNT
    COUNT += 1
    if not condition:
        FAILURES.append(label)


def robots_for(pattern_block: str) -> politeness.RobotsTxt:
    return politeness.parse_robots("User-agent: *\n" + pattern_block)


def check_pattern(pattern: str, matches: list[str], non_matches: list[str]) -> None:
    r = robots_for(f"Disallow: {pattern}\n")
    for path in matches:
        d = r.decide("TestBot", path)
        expect(not d.allowed, f"pattern {pattern!r} should match {path!r} (got allowed={d.allowed})")
    for path in non_matches:
        d = r.decide("TestBot", path)
        expect(d.allowed, f"pattern {pattern!r} should NOT match {path!r} (got allowed={d.allowed})")


# ---------------------------------------------------- RFC 9309 section 2.2.2

check_pattern("/", ["/", "/anything", "/deep/path.html"], [])

check_pattern(
    "/fish",
    ["/fish", "/fish.html", "/fish/salmon.html", "/fishheads", "/fishheads/yummy.html", "/fish.php?id=anything"],
    ["/Fish.asp", "/catfish", "/?id=fish", "/desert/fish"],
)

check_pattern(
    "/fish*",
    ["/fish", "/fish.html", "/fish/salmon.html", "/fishheads"],
    ["/Fish.asp", "/catfish", "/?id=fish"],
)

check_pattern(
    "/fish/",
    ["/fish/", "/fish/?id=anything", "/fish/salmon.htm"],
    ["/fish", "/fish.html", "/Fish/Salmon.asp"],
)

check_pattern(
    "/*.php",
    [
        "/index.php",
        "/filename.php",
        "/folder/filename.php",
        "/folder/filename.php?parameters",
        "/folder/any.php.file.html",
        "/filename.php/",
    ],
    ["/", "/windows.PHP"],
)

check_pattern(
    "/*.php$",
    ["/filename.php", "/folder/filename.php"],
    ["/filename.php?parameters", "/filename.php/", "/filename.php5", "/windows.PHP"],
)

check_pattern(
    "/fish*.php",
    ["/fish.php", "/fishheads/catfish.php?parameters"],
    ["/Fish.PHP"],
)

# ------------------------------------------- precedence: longest pattern wins

r = politeness.parse_robots(
    "User-agent: *\nAllow: /example/page/\nDisallow: /example/\n"
)
d = r.decide("TestBot", "/example/page/index.html")
expect(d.allowed, "RFC precedence: longer Allow must beat shorter Disallow")
expect(d.rule is not None and d.rule.pattern == "/example/page/", "precedence picks the longest pattern")

r = politeness.parse_robots("User-agent: *\nAllow: /p\nDisallow: /\n")
expect(r.decide("TestBot", "/page").allowed, "Allow:/p beats Disallow:/ for /page")

r = politeness.parse_robots("User-agent: *\nAllow: /folder\nDisallow: /folder\n")
expect(r.decide("TestBot", "/folder/page").allowed, "equal-length tie must resolve to Allow")

r = politeness.parse_robots("User-agent: *\nAllow: /$\nDisallow: /\n")
expect(r.decide("TestBot", "/").allowed, "Allow:/$ permits the root exactly")
expect(not r.decide("TestBot", "/page").allowed, "Allow:/$ does not permit /page")

# ------------------------------------------------ 2.2.3: empty Disallow allows

r = politeness.parse_robots("User-agent: *\nDisallow:\n")
expect(r.decide("TestBot", "/anything").allowed, "empty Disallow grants access")

# ------------------------------- 2.2.1: product token matching, longest wins

r = politeness.parse_robots(
    "User-agent: *\nDisallow: /\n\n"
    "User-agent: GPTBot\nDisallow: /private/\n\n"
    "User-agent: Googlebot-News\nDisallow: /news/\n"
)
expect(r.decide("GPTBot/1.2", "/public").allowed, "specific group replaces wildcard, not merges with it")
expect(not r.decide("GPTBot/1.2", "/private/x").allowed, "specific group rules apply")
expect(not r.decide("RandomBot", "/public").allowed, "unmatched agent falls back to wildcard group")
expect(
    r.matched_agent_token("Googlebot-News/1.0") == "Googlebot-News",
    "longest matching product token wins over a shorter one",
)

# ------------------------------------------------------ 2.3: status handling

r = politeness.parse_robots("User-agent: *\nDisallow: /\n", status=404)
expect(r.decide("TestBot", "/anything").allowed, "4xx robots.txt grants unrestricted access")

r = politeness.parse_robots("User-agent: *\nAllow: /\n", status=503)
expect(not r.decide("TestBot", "/anything").allowed, "5xx robots.txt must be treated as fully disallowed")

# --------------------------------------------------- evidence quality checks

r = politeness.parse_robots(
    "# comment\nUser-agent: PerplexityBot\nDisallow: /\nSitemap: https://x.test/sitemap.xml\n"
)
d = r.decide("PerplexityBot", "/pricing")
expect(not d.allowed, "PerplexityBot blocked")
expect(d.line_no == 3, f"evidence carries the 1-based line number (got {d.line_no})")
expect(d.raw_line == "Disallow: /", f"evidence carries the verbatim line (got {d.raw_line!r})")
expect(d.matched_agent == "PerplexityBot", "evidence names the matched agent token")
expect(r.sitemaps == ["https://x.test/sitemap.xml"], "sitemap directives are collected")
expect(r.blanket_disallow_group() is None, "a named-agent block is not a blanket disallow")

r = politeness.parse_robots("User-agent: *\nDisallow: /\n")
expect(r.blanket_disallow_group() is not None, "wildcard Disallow:/ is a blanket disallow")

# ------------------------------------------------------- malformed input

r = politeness.parse_robots("this is not robots.txt\n<html><body>404</body></html>\n")
expect(len(r.errors) >= 1, "malformed lines are recorded as errors")
expect(r.decide("TestBot", "/x").allowed, "malformed robots.txt does not accidentally block us")

r = politeness.parse_robots("﻿User-agent: *\nDisallow: /admin\n")
expect(not r.decide("TestBot", "/admin").allowed, "leading BOM is stripped before parsing")

r = politeness.parse_robots("User-agent: *\nCrawl-delay: 10\n")
delay, line, raw = r.crawl_delay_for("TestBot")
expect(delay == 10.0 and line == 2, f"crawl-delay parsed with its line number (got {delay}, {line})")

# ------------------------------------------------------------- throttle

t = politeness.HostThrottle(default_delay=0.4)
slept: list[float] = []
clock = {"t": 100.0}
t.wait("a.test", sleep=slept.append, now=lambda: clock["t"])
t.wait("a.test", sleep=slept.append, now=lambda: clock["t"])
expect(slept and abs(slept[-1] - 0.4) < 1e-9, f"second hit on same host waits the delay (slept={slept})")
slept.clear()
t.wait("b.test", sleep=slept.append, now=lambda: clock["t"])
expect(not slept or slept[-1] == 0, "a different host is not throttled by the first")

expect(politeness.parse_retry_after("120") == 120.0, "Retry-After delta-seconds")
expect(politeness.parse_retry_after("garbage") is None, "Retry-After garbage is ignored")

# ---------------------------------------------------------------- report

if FAILURES:
    print(f"FAILED {len(FAILURES)} of {COUNT} assertions:\n")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print(f"PASS: {COUNT} RFC 9309 conformance assertions")
