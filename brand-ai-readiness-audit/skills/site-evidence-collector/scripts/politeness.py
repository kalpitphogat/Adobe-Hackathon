#!/usr/bin/env python3
"""RFC 9309 robots.txt evaluation and per-host crawl politeness. Standard library only.

Why this module exists instead of urllib.robotparser
----------------------------------------------------
`urllib.robotparser` implements the 1994/1996 draft "A Standard for Robot
Exclusion", not RFC 9309 (2022). It has no `*` wildcard support inside paths,
no `$` end-of-match anchor, and no longest-match precedence between Allow and
Disallow. Every real crawler - Googlebot, Bingbot, and the AI retrieval bots we
audit for - implements the RFC semantics. Using the stdlib parser would make
this auditor disagree with the systems it is auditing, and would make us crawl
paths a site intended to exclude.

  * Scrapy documents the same limitation and ships its own matcher for it:
    https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#robotstxt-middleware
  * Tracked upstream as CPython issue #138907, "Support RFC 9309 in robotparser".

Implemented per RFC 9309:
  Section 2.2.1  product token matching, case-insensitive, longest token wins
  Section 2.2.2  path matching with `*` and `$`; the most specific (longest)
                 pattern wins; Allow wins ties
  Section 2.2.3  an empty Disallow value grants access
  Section 2.3    a 4xx robots.txt means unrestricted; 5xx means treat as fully
                 disallowed ("unavailable" vs "unreachable")

Non-standard directives are parsed but never used to restrict our own crawl:
`Crawl-delay` is honoured as politeness, `Sitemap` is collected as discovery.
"""

from __future__ import annotations

import re
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Iterable

__all__ = [
    "Rule",
    "Group",
    "RobotsTxt",
    "Decision",
    "parse_robots",
    "HostThrottle",
]

# A robots.txt larger than this is truncated, per RFC 9309 section 2.5.
MAX_ROBOTS_BYTES = 500 * 1024


@dataclass(frozen=True)
class Rule:
    """One Allow or Disallow directive."""

    allow: bool
    pattern: str
    line_no: int
    raw_line: str

    @property
    def specificity(self) -> int:
        """RFC 9309 2.2.2: the most specific match wins, measured by pattern length."""
        return len(self.pattern)


@dataclass
class Group:
    """One record: a set of user-agent tokens and the rules that apply to them."""

    agents: list[str] = field(default_factory=list)
    agent_lines: dict[str, int] = field(default_factory=dict)
    rules: list[Rule] = field(default_factory=list)
    crawl_delay: float | None = None
    crawl_delay_line: int | None = None
    crawl_delay_raw: str | None = None

    @property
    def is_wildcard(self) -> bool:
        return "*" in self.agents


@dataclass(frozen=True)
class Decision:
    """The outcome of evaluating one path for one user agent.

    Carries the evidence a finding needs: which group matched, which rule fired,
    the verbatim line and its 1-based line number.
    """

    allowed: bool
    matched_agent: str | None
    rule: Rule | None
    reason: str

    @property
    def line_no(self) -> int | None:
        return self.rule.line_no if self.rule else None

    @property
    def raw_line(self) -> str | None:
        return self.rule.raw_line if self.rule else None


def _normalise_path(path: str) -> str:
    """Percent-decode unreserved characters so pattern and path compare alike.

    RFC 9309 2.2.2 compares octets, so we normalise both sides the same way and
    never decode reserved delimiters (a literal %2F must not become a '/').
    """
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    out = []
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == "%" and i + 2 < len(path) + 1 and re.match(r"^%[0-9A-Fa-f]{2}$", path[i : i + 3] or ""):
            code = int(path[i + 1 : i + 3], 16)
            decoded = chr(code)
            if re.match(r"[A-Za-z0-9._~-]", decoded):
                out.append(decoded)
            else:
                out.append(path[i : i + 3].upper())
            i += 3
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _pattern_to_regex(pattern: str) -> re.Pattern[str]:
    """Compile an RFC 9309 path pattern.

    `*` matches any sequence of characters. `$` anchors the end of the match,
    but only as the final character of the pattern; elsewhere it is literal.
    Matching is a prefix match anchored at the start of the path.
    """
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


class RobotsTxt:
    """A parsed robots.txt with RFC 9309 evaluation semantics."""

    def __init__(
        self,
        groups: list[Group],
        sitemaps: list[str],
        errors: list[str],
        status: int | None = 200,
        raw: str = "",
        truncated: bool = False,
    ) -> None:
        self.groups = groups
        self.sitemaps = sitemaps
        self.errors = errors
        self.status = status
        self.raw = raw
        self.truncated = truncated

    # ------------------------------------------------------------ 2.2.1

    def matching_group(self, user_agent: str) -> Group | None:
        """Find the group for a product token. Longest matching token wins.

        Only one group applies to a crawler; a wildcard group is the fallback
        and is never merged with a specific group.
        """
        ua = user_agent.lower()
        best: tuple[int, Group, str] | None = None
        wildcard: Group | None = None
        for group in self.groups:
            for agent in group.agents:
                token = agent.lower()
                if token == "*":
                    if wildcard is None:
                        wildcard = group
                    continue
                if token in ua:
                    if best is None or len(token) > best[0]:
                        best = (len(token), group, agent)
        if best is not None:
            return best[1]
        return wildcard

    def matched_agent_token(self, user_agent: str) -> str | None:
        ua = user_agent.lower()
        best: tuple[int, str] | None = None
        has_wildcard = False
        for group in self.groups:
            for agent in group.agents:
                token = agent.lower()
                if token == "*":
                    has_wildcard = True
                    continue
                if token in ua and (best is None or len(token) > best[0]):
                    best = (len(token), agent)
        if best:
            return best[1]
        return "*" if has_wildcard else None

    # ------------------------------------------------------------ 2.2.2

    def decide(self, user_agent: str, url_or_path: str) -> Decision:
        """Evaluate one path. Returns the decision plus the evidence for it."""
        if self.status is not None and 500 <= self.status < 600:
            return Decision(
                allowed=False,
                matched_agent=None,
                rule=None,
                reason=(
                    f"robots.txt returned HTTP {self.status}; RFC 9309 section 2.3.1.4 "
                    "requires treating an unreachable robots.txt as fully disallowed"
                ),
            )
        if self.status is not None and 400 <= self.status < 500:
            return Decision(
                allowed=True,
                matched_agent=None,
                rule=None,
                reason=(
                    f"robots.txt returned HTTP {self.status}; RFC 9309 section 2.3.1.3 "
                    "treats an unavailable robots.txt as granting unrestricted access"
                ),
            )

        parsed = urllib.parse.urlsplit(url_or_path)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        path = _normalise_path(path)

        group = self.matching_group(user_agent)
        token = self.matched_agent_token(user_agent)
        if group is None:
            return Decision(True, None, None, "no group matches this product token")

        best: Rule | None = None
        for rule in group.rules:
            if not rule.pattern:
                # 2.2.3: an empty Disallow grants access; it never restricts.
                continue
            if _pattern_to_regex(_normalise_path(rule.pattern)).match(path):
                if best is None:
                    best = rule
                elif rule.specificity > best.specificity:
                    best = rule
                elif rule.specificity == best.specificity and rule.allow and not best.allow:
                    # 2.2.2: on an equal-length tie, the Allow rule wins.
                    best = rule

        if best is None:
            return Decision(True, token, None, "no rule matches this path")
        verb = "Allow" if best.allow else "Disallow"
        return Decision(
            allowed=best.allow,
            matched_agent=token,
            rule=best,
            reason=(
                f"{verb}: {best.pattern} (line {best.line_no}) is the longest matching "
                f"pattern for user-agent group {token!r}"
            ),
        )

    def allows(self, user_agent: str, url_or_path: str) -> bool:
        return self.decide(user_agent, url_or_path).allowed

    def crawl_delay_for(self, user_agent: str) -> tuple[float | None, int | None, str | None]:
        group = self.matching_group(user_agent)
        if group is None:
            return None, None, None
        return group.crawl_delay, group.crawl_delay_line, group.crawl_delay_raw

    def blanket_disallow_group(self) -> Group | None:
        """The wildcard group, if it disallows the whole site."""
        for group in self.groups:
            if not group.is_wildcard:
                continue
            for rule in group.rules:
                if not rule.allow and rule.pattern == "/":
                    return group
        return None


def parse_robots(
    text: str, status: int | None = 200
) -> RobotsTxt:
    """Parse robots.txt into groups. Never raises; malformed lines are recorded."""
    truncated = False
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) > MAX_ROBOTS_BYTES:
        text = encoded[:MAX_ROBOTS_BYTES].decode("utf-8", errors="ignore")
        truncated = True

    if text.startswith("﻿"):
        text = text.lstrip("﻿")

    groups: list[Group] = []
    sitemaps: list[str] = []
    errors: list[str] = []

    current: Group | None = None
    # Consecutive User-agent lines accumulate into one group; the first rule
    # line after them closes the agent list.
    accepting_agents = False

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            errors.append(f"line {line_no}: no field separator in {raw.strip()!r}")
            continue
        field_name, _, value = line.partition(":")
        key = field_name.strip().lower()
        value = value.strip()

        if key == "user-agent":
            if not value:
                errors.append(f"line {line_no}: empty user-agent value")
                continue
            if current is None or not accepting_agents:
                current = Group()
                groups.append(current)
                accepting_agents = True
            current.agents.append(value)
            current.agent_lines[value] = line_no
        elif key in ("allow", "disallow"):
            if current is None:
                errors.append(f"line {line_no}: {key} outside any user-agent group")
                continue
            accepting_agents = False
            current.rules.append(
                Rule(
                    allow=(key == "allow"),
                    pattern=value,
                    line_no=line_no,
                    raw_line=raw.rstrip("\n"),
                )
            )
        elif key == "crawl-delay":
            if current is None:
                errors.append(f"line {line_no}: crawl-delay outside any user-agent group")
                continue
            accepting_agents = False
            try:
                current.crawl_delay = float(value)
                current.crawl_delay_line = line_no
                current.crawl_delay_raw = raw.rstrip("\n")
            except ValueError:
                errors.append(f"line {line_no}: non-numeric crawl-delay {value!r}")
        elif key == "sitemap":
            if value:
                sitemaps.append(value)
        else:
            # Unknown fields are legal and ignored, per RFC 9309 section 2.2.4.
            pass

    return RobotsTxt(
        groups=groups,
        sitemaps=sitemaps,
        errors=errors,
        status=status,
        raw=text,
        truncated=truncated,
    )


class HostThrottle:
    """Per-host politeness: a minimum delay between requests, plus Retry-After.

    Thread safe; the crawler runs a small worker pool and every worker shares
    one instance so the delay is per host, not per worker.
    """

    def __init__(self, default_delay: float = 0.4) -> None:
        self.default_delay = default_delay
        self._next_allowed: dict[str, float] = {}
        self._delays: dict[str, float] = {}
        self._lock = threading.Lock()

    def set_delay(self, host: str, delay: float) -> None:
        with self._lock:
            self._delays[host] = max(delay, self.default_delay)

    def delay_for(self, host: str) -> float:
        with self._lock:
            return self._delays.get(host, self.default_delay)

    def wait(self, host: str, sleep=time.sleep, now=time.monotonic) -> float:
        """Block until this host may be hit again. Returns seconds actually slept."""
        with self._lock:
            delay = self._delays.get(host, self.default_delay)
            current = now()
            earliest = self._next_allowed.get(host, 0.0)
            wait_for = max(0.0, earliest - current)
            self._next_allowed[host] = max(current, earliest) + delay
        if wait_for > 0:
            sleep(wait_for)
        return wait_for

    def penalise(self, host: str, retry_after: float, now=time.monotonic) -> None:
        """Honour a Retry-After header by pushing this host out."""
        with self._lock:
            self._next_allowed[host] = max(
                self._next_allowed.get(host, 0.0), now() + max(0.0, retry_after)
            )


def parse_retry_after(value: str, now: float | None = None) -> float | None:
    """Retry-After is either delta-seconds or an HTTP-date (RFC 9110 section 10.2.3)."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        import email.utils

        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed is None:
        return None
    import datetime

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    reference = (
        datetime.datetime.now(datetime.timezone.utc)
        if now is None
        else datetime.datetime.fromtimestamp(now, datetime.timezone.utc)
    )
    return max(0.0, (parsed - reference).total_seconds())


def iter_sitemaps(robots: RobotsTxt) -> Iterable[str]:
    seen = set()
    for url in robots.sitemaps:
        if url not in seen:
            seen.add(url)
            yield url
