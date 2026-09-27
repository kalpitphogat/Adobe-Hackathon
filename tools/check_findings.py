"""Prove the findings shown in Part 2 are real: the engine's own, and true on the live site.

The integrity floor fails a video that shows fabricated findings (CONSTRAINTS.md 6.1), and the
drill-down must show real evidence (3.11). This checks both, on the saved run, after the take:

1. The agent invented nothing (offline). Every row of the agent's table, and every finding id it
   names anywhere, is in audit-report.json with the same severity, confidence, ICE and title. The
   rows are the report's top confirmed findings in report order; the status, the counts by
   severity, the confirmed and likely counts and the drill-down's blocked_by count are the
   report's own numbers.
2. What was shown holds on the live site (network). Each table row is re-fetched and re-counted
   by this file's own code, not the engine's and not the agent's: robots.txt rules (RFC 9309,
   longest match), noindex, JSON-LD / microdata / RDFa, the viewport tag, dates, alt text,
   zero-width characters, the homepage identity node, plain http. Checks with no automatic
   re-check are listed with the engine's own verification step, to do by hand.
   A row the agent called supported that does not hold here fails; so does a drill-down that
   does not hold.

Run it after the take, never before: it fetches the site, and the on-camera site must stay
unaudited until the take.

Usage: python tools/check_findings.py recorded-run
           (reads recorded-run/audit-report.json and recorded-run/session.jsonl,
            writes recorded-run/finding-check.md)
       python tools/check_findings.py --report audit-report.json --answer session.jsonl [--offline]
           (--answer takes a Claude Code transcript, a claude -p stream-json log, or the answer as
            text; "--answer auto" writes the answer a faithful agent would give, to test part 2)
       python tools/check_findings.py --self-test
           (offline: a faithful answer to the site_b golden in submission.zip must pass, and each
            tampered copy of it must fail)
Exit 1 on any FAIL.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

UA = "Mozilla/5.0 (compatible; brand-ai-readiness-audit/1.0 (+read-only auditor))"  # the engine's own
MAX_URLS = 8  # affected URLs re-fetched per finding
FID = re.compile(r"\bF-\d{3,}\b")
SEVERITIES = ("critical", "high", "medium", "low", "info")
IDENTITY_TYPES = {"organization", "localbusiness", "person", "corporation", "store", "ngo", "website"}
ZERO_WIDTH = re.compile("[​‌‍⁠﻿‪-‮⁦-⁩]")
TEXT_DATE = re.compile(
    r"\b(?:\d{1,2}\s+)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+"
    r"(?:\d{1,2}(?:st|nd|rd|th)?,?\s+)?\d{4}\b|\b\d{4}-\d{2}-\d{2}\b", re.I)
META_DATES = {"article:published_time", "article:modified_time", "og:updated_time", "date",
              "dc.date", "dcterms.date", "dcterms.modified", "last-modified"}

lines_out: list[str] = []
counts = {"FAIL": 0, "WARN": 0, "HAND": 0}
QUIET = False  # the self-test runs the checks without printing them


def say(tag: str, msg: str) -> None:
    counts[tag] = counts.get(tag, 0) + 1
    line = f"[{tag:^4}] {msg}"
    if not QUIET:
        print(line)
        lines_out.append(line)


def note(msg: str) -> None:
    if not QUIET:
        print(msg)
        lines_out.append(msg)


# ------------------------------------------------------------------ reading the answer

def read_text(path: str) -> str:
    raw = Path(path).read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):  # Windows PowerShell 5.1 ">" writes UTF-16
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def unmangle(line: str) -> str:
    """Undo UTF-8 read back through a Windows code page. Windows PowerShell 5.1 decodes a program's
    output with the console code page, so a long dash in the agent's answer is logged as three wrong
    characters. Text that was never mangled does not survive the round trip and is left alone."""
    for _ in range(3):  # text captured twice is mangled twice
        if line.isascii():
            break
        for codec in ("cp437", "cp1252"):
            try:
                fixed = line.encode(codec).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if fixed != line:
                line = fixed
                break
        else:
            break
    return line


def repaired(text: str) -> str:
    return "\n".join(unmangle(ln) for ln in text.splitlines())


def answer_from(path: str) -> str:
    """The agent's answer: from a transcript or stream-json log, or the file itself if it is text."""
    return repaired(_answer_from(path))


def _answer_from(path: str) -> str:
    text = read_text(path)
    events = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    if not events:
        return text
    results = [e["result"] for e in events if e.get("type") == "result" and e.get("result")]
    if results:
        return results[-1]
    blocks: list[tuple[str, str]] = []
    for e in events:
        if e.get("type") != "assistant" or e.get("isSidechain"):
            continue
        content = (e.get("message") or {}).get("content") or []
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        for c in content:
            if c.get("type") == "tool_use":
                blocks.append(("tool", json.dumps(c.get("input", {}))))
            elif c.get("type") == "text":
                blocks.append(("text", c.get("text", "")))
    # everything the agent wrote after its last engine run: the table, the checks, the drill-down
    last_run = max((i for i, (k, v) in enumerate(blocks) if k == "tool" and "orchestrate.py" in v),
                   default=-1)
    return "\n".join(v for k, v in blocks[last_run + 1:] if k == "text")


def plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[*`]", "", s)).strip()


def norm_title(s: str) -> str:
    s = plain(s).replace("’", "'").replace("“", '"').replace("”", '"')
    return s.replace("\\|", "|").lower()


def cells(line: str) -> list[str] | None:
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return None
    return [c.strip() for c in re.split(r"(?<!\\)\|", s.strip("|"))]


def find_table(text: str):
    """The last markdown table whose header names an id and a severity column."""
    rows = text.splitlines()
    found = None
    for i in range(len(rows) - 1):
        head, sep = cells(rows[i]), cells(rows[i + 1])
        if not head or not sep or not all(re.fullmatch(r":?-+:?", c or "-") for c in sep):
            continue
        names = [plain(h).lower() for h in head]
        if not any("sever" in n for n in names):
            continue
        body, j = [], i + 2
        while j < len(rows) and cells(rows[j]) is not None:
            body.append(cells(rows[j]))
            j += 1
        if any(FID.search(" ".join(r)) for r in body):
            found = (names, body, i, j)
    return found


def column(names: list[str], *keys: str, skip: int | None = None) -> int | None:
    """The first column matching the first key that matches any column (keys in priority order)."""
    for k in keys:
        for i, n in enumerate(names):
            if i != skip and (n == k or n.startswith(k)):
                return i
    return None


def verdict_class(s: str) -> str:
    s = s.lower()
    if re.search(r"not\s+supported|unsupported|doesn.t hold|does not hold", s):
        return "not"
    if re.search(r"partl|partial", s):
        return "partly"
    if "supported" in s:
        return "supported"
    return "?"


# ------------------------------------------------------------------ part 1: nothing invented

def check_answer(report: dict, answer: str) -> tuple[list[dict], dict, str | None]:
    note("\n== 1. The answer against the engine's report (nothing invented) ==")
    findings = report["findings"]
    by_id = {f["id"]: f for f in findings}
    table = find_table(answer)
    if not table:
        say("FAIL", "no findings table (with an id and a severity column) in the agent's answer")
        return [], by_id, None
    names, body, start, end = table
    lines = answer.splitlines()
    before, after = "\n".join(lines[:start]), "\n".join(lines[end:])
    c_id = next((i for i in range(len(names)) if any(FID.search(r[i]) for r in body if i < len(r))), None)
    c_sev, c_conf = column(names, "sever", skip=c_id), column(names, "confidence", "conf", skip=c_id)
    c_ice, c_title = column(names, "ice", skip=c_id), column(names, "title", "finding", skip=c_id)
    c_verdict = column(names, "verdict", "your verdict", "evidence", skip=c_id)

    rows = []
    for r in body:
        m = FID.search(r[c_id]) if c_id is not None and c_id < len(r) else None
        if not m:
            continue
        get = lambda c: r[c] if c is not None and c < len(r) else ""  # noqa: E731
        rows.append({"id": m.group(0), "severity": plain(get(c_sev)).lower(),
                     "confidence": plain(get(c_conf)).lower(), "ice": plain(get(c_ice)),
                     "title": get(c_title), "verdict": verdict_class(get(c_verdict)) if c_verdict is not None else "?"})

    # verdicts written below the table instead of in it
    for row in rows:
        if row["verdict"] == "?":
            m = re.search(re.escape(row["id"]) + r"\b[^\n]{0,160}?\b(not supported|unsupported|partly supported|"
                          r"partially supported|supported)\b", after, re.I)
            if m:
                row["verdict"] = verdict_class(m.group(1))

    confirmed = [f for f in findings if f.get("confidence") == "confirmed"]
    expected = confirmed[:5]
    if len(expected) < 5:
        expected += [f for f in findings if f.get("confidence") != "confirmed"][:5 - len(expected)]
    shown_ids, want_ids = [r["id"] for r in rows], [f["id"] for f in expected]
    if shown_ids == want_ids:
        say(" OK ", f"table rows are the report's top {len(want_ids)} confirmed findings, in report order: "
                    f"{', '.join(shown_ids)}")
    else:
        say("FAIL", f"table rows {shown_ids} are not the report's top confirmed findings in order {want_ids}")

    for row in rows:
        f = by_id.get(row["id"])
        if not f:
            say("FAIL", f"{row['id']} is in the table but not in the report: an invented finding")
            continue
        problems = []
        if c_sev is not None and row["severity"] != f["severity"]:
            problems.append(f"severity {row['severity']!r}, report {f['severity']!r}")
        if c_conf is not None and row["confidence"] != f["confidence"]:
            problems.append(f"confidence {row['confidence']!r}, report {f['confidence']!r}")
        ice = (f.get("suggested_action") or {}).get("ice")
        m = re.search(r"\d+(?:\.\d+)?", row["ice"])
        if c_ice is not None and ice is not None and (not m or abs(float(m.group(0)) - float(ice)) > 0.051):
            problems.append(f"ICE {row['ice']!r}, report {ice}")
        shown, real = norm_title(row["title"]), norm_title(f["title"])
        shortened = shown.endswith(("…", "...")) and real.startswith(shown.rstrip(".…").strip())
        if c_title is not None and shown != real and not shortened:
            problems.append(f"title {plain(row['title'])!r}, report {f['title']!r}")
        if problems:
            say("FAIL", f"{row['id']} differs from the report: " + "; ".join(problems))
        else:
            say(" OK ", f"{row['id']} {f['check_id']} [{f['severity']}/{f['confidence']}, ICE {ice}] as in the report"
                        + (" (title shortened)" if shortened else "") + f"; agent's verdict: {row['verdict']}")

    unknown = sorted({i for i in FID.findall(answer) if i not in by_id})
    if unknown:
        say("FAIL", f"the answer names finding id(s) the report does not have: {', '.join(unknown)}")
    else:
        say(" OK ", f"every finding id the answer names is in the report ({len(set(FID.findall(answer)))} ids)")

    # (1) status and counts by severity, before the table
    m = re.search(r"audit_status[^\n]{0,40}?\b(complete|partial|failed|incomplete|aborted)\b", before, re.I)
    if m:
        tag = " OK " if m.group(1).lower() == report["audit_status"] else "FAIL"
        say(tag, f"audit_status {m.group(1)!r}, report {report['audit_status']!r}")
    else:
        say("WARN", "audit_status not found above the table")
    # a number goes with a severity word only when nothing but a space, a colon, "=" or a table bar
    # separates them: "1 critical, 4 high" and "critical 1 · high 4" both read right
    flat = plain(before)
    word_first = {s: re.search(rf"\b{s}\b\s*[:=|]?\s*(\d+)", flat, re.I) for s in SEVERITIES}
    number_first = {s: re.search(rf"(\d+)\s+{s}\b", flat, re.I) for s in SEVERITIES}
    a = {s: int(m.group(1)) for s, m in word_first.items() if m}
    b = {s: int(m.group(1)) for s, m in number_first.items() if m}
    got = a if len(a) > len(b) else b if len(b) > len(a) else (a if a == b else None)
    if got is None:
        say("WARN", "can't tell which number goes with which severity above the table; compare by eye")
    elif got:
        wrong = {s: (n, report["summary"].get(s)) for s, n in got.items() if n != report["summary"].get(s)}
        if wrong:
            say("FAIL", "counts by severity differ from the report: "
                        + ", ".join(f"{s} {n} (report {r})" for s, (n, r) in wrong.items()))
        else:
            say(" OK ", "counts by severity match the report: " + ", ".join(f"{s} {n}" for s, n in got.items()))
    else:
        say("WARN", "counts by severity not found above the table")

    # the line under the table: confirmed and likely counts, and the top likely finding
    n_conf = len(confirmed)
    n_likely = sum(1 for f in findings if f.get("confidence") == "likely")
    head = after[:600]
    for label, want in (("confirmed", n_conf), ("likely", n_likely)):
        m = (re.search(rf"(\d+)\s+(?:findings?\s+)?(?:are\s+|is\s+)?{label}\b", head, re.I)
             or re.search(rf"\b{label}\W{{1,3}}(\d+)", head, re.I))
        if not m:
            say("WARN", f"the {label} count is not in the line under the table")
        elif int(m.group(1)) == want:
            say(" OK ", f"{label} count {want}, as in the report")
        else:
            say("FAIL", f"the answer says {m.group(1)} {label}; the report has {want}")
    top_likely = next((f for f in findings if f.get("confidence") == "likely"), None)
    likely_line = next((ln for ln in head.splitlines() if "likely" in ln.lower() and FID.search(ln)), "")
    if top_likely and likely_line:
        named = FID.findall(likely_line)
        tag = " OK " if top_likely["id"] in named else "FAIL"
        say(tag, f"highest-ranked likely finding named: {named}; report: {top_likely['id']}")

    # (4) the drill-down
    d = (re.search(r"(?im)^\s*(?:#+|\*\*|\(?4[.)])[^\n]*drill[- ]?down", after)
         or re.search(r"drill[- ]?down", after, re.I))
    drill_id = None
    if not d:
        say("WARN", "no drill-down section found after the table")
    else:
        text = after[d.start():]
        m = FID.search(text)
        if not m:
            say("WARN", "the drill-down names no finding id (the agent may have found none supported)")
        else:
            drill_id = m.group(0)
            f = by_id.get(drill_id)
            first_supported = next((r["id"] for r in rows if r["verdict"] == "supported"), None)
            if not f:
                say("FAIL", f"the drill-down is on {drill_id}, which is not in the report")
            else:
                tag = " OK " if drill_id == first_supported else "WARN"
                say(tag, f"drill-down on {drill_id}; the highest-ranked row the agent supported: {first_supported}")
                n_blocked = sum(1 for x in findings if x.get("blocked_by") == drill_id)
                said = None
                for ln in text.splitlines():
                    # "blocked_by", "blocked by it": not a robots line such as 'blocked by "Disallow: /" (line 102)'
                    if not re.search(r"blocked_by|blocked by (?:it|this|f-\d)|point(?:s|ing)? (?:at|to) (?:it|this)"
                                     r"|waiting on (?:it|this)", ln, re.I):
                        continue
                    nums = [int(n) for n in re.findall(r"\b\d+\b", FID.sub(" ", ln))]
                    if nums or re.search(r"\b(none|no finding|no other)\b", ln, re.I):
                        said = (nums, ln)
                        break
                if said is None:
                    say("WARN", f"the drill-down gives no blocked_by count (report: {n_blocked})")
                elif n_blocked in said[0] or (not said[0] and n_blocked == 0):
                    say(" OK ", f"blocked_by count {n_blocked}, as in the report")
                else:
                    say("FAIL", f"the drill-down's blocked_by line ({plain(said[1])[:90]!r}) does not give "
                                f"the report's {n_blocked}")
                for word in (f["severity"], f["confidence"]):
                    if not re.search(rf"\b{word}\b", text, re.I):
                        say("WARN", f"the drill-down does not say {word!r}")
                ice = (f.get("suggested_action") or {}).get("ice")
                if ice is not None and f"{float(ice):.1f}" not in text:
                    say("WARN", f"the drill-down does not show ICE {float(ice):.1f}")
    return rows, by_id, drill_id


# ------------------------------------------------------------------ part 2: true on the live site

class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.metas: list[dict] = []
        self.imgs: list[dict] = []
        self.scripts: list[tuple[str, str]] = []
        self.times: list[str] = []
        self.microdata = self.rdfa = 0
        self.text: list[str] = []
        self._skip = 0
        self._script: list | None = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        self.microdata += "itemscope" in a or "itemtype" in a
        self.rdfa += "typeof" in a  # as the engine counts RDFa: a node with typeof, not a bare vocab
        if tag == "meta":
            self.metas.append(a)
        elif tag == "img":
            self.imgs.append(a)
        elif tag == "time" and a.get("datetime"):
            self.times.append(a["datetime"])
        if tag in ("script", "style", "noscript", "template"):
            self._skip += 1
            if tag == "script":
                self._script = [a.get("type", "").lower(), []]

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template") and self._skip:
            self._skip -= 1
            if tag == "script" and self._script is not None:
                self.scripts.append((self._script[0], "".join(self._script[1])))
                self._script = None

    def handle_data(self, data):
        if self._script is not None:
            self._script[1].append(data)
        elif not self._skip:
            self.text.append(data)

    @property
    def jsonld(self) -> list[str]:
        return [body for kind, body in self.scripts if kind == "application/ld+json"]

    @property
    def plain_text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.text)).strip()


_cache: dict[str, tuple] = {}


def fetch(url: str) -> tuple[int, str, object, str]:
    """(status, final URL, headers, body). Status 0 means the request itself failed."""
    if url in _cache:
        return _cache[url]
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
            res = (r.status, r.geturl(), r.headers, body)
    except urllib.error.HTTPError as e:
        res = (e.code, url, e.headers, e.read().decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001 - a failed fetch is itself the answer
        res = (0, url, None, f"{type(e).__name__}: {e}")
    _cache[url] = res
    time.sleep(0.5)  # polite: at most two requests a second
    return res


def page(url: str) -> tuple[int, Page, object]:
    status, _, headers, body = fetch(url)
    p = Page()
    if status:
        p.feed(body)
    return status, p, headers


def urls_of(f: dict) -> list[str]:
    return list(dict.fromkeys(f.get("affected_urls") or []))[:MAX_URLS]


def tally(results: list[tuple[str, bool, str]], what: str, unit: str = "re-fetched page(s)") -> tuple[str, str]:
    """results: (item, claim holds for it, detail). Every item must hold for the finding to hold."""
    ok = [r for r in results if r[1]]
    detail = "; ".join(f"{u}: {d}" for u, _, d in results[:6])
    if not results:
        return "hand", "nothing to re-fetch"
    if len(ok) == len(results):
        return "holds", f"{what}: {len(ok)} of {len(results)} {unit}. {detail}"
    if ok:
        return "partly", f"{what}: only {len(ok)} of {len(results)} {unit}. {detail}"
    return "not", f"{what}: none of {len(results)} {unit}. {detail}"


def robots_groups(txt: str) -> list[dict]:
    groups, cur, in_rules = [], None, False
    for n, raw in enumerate(txt.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (s.strip() for s in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if cur is None or in_rules:
                cur, in_rules = {"agents": [], "rules": []}, False
                groups.append(cur)
            cur["agents"].append(value.lower())
        elif key in ("allow", "disallow") and cur is not None:
            in_rules = True
            cur["rules"].append((key, value, n))
    return groups


def robots_decide(groups: list[dict], bot: str, path: str = "/"):
    """RFC 9309: the bot's own groups (else '*'); the longest matching rule wins, allow on a tie."""
    token = bot.lower()
    mine = [g for g in groups if token in g["agents"]] or [g for g in groups if "*" in g["agents"]]
    best = None
    for kind, pat, line in (r for g in mine for r in g["rules"]):
        if not pat:
            continue
        rx = "".join(".*" if c == "*" else "$" if c == "$" and i == len(pat) - 1 else re.escape(c)
                     for i, c in enumerate(pat))
        if re.match(rx, path):
            key = (len(pat), kind == "allow")
            if best is None or key > best[0]:
                best = (key, kind, pat, line)
    return best


def v_robots(f: dict) -> tuple[str, str]:
    origin = "{0.scheme}://{0.netloc}".format(urlparse((f.get("affected_urls") or [""])[0]))
    status, _, _, txt = fetch(origin + "/robots.txt")
    if status != 200:
        return "not", f"{origin}/robots.txt returned {status or txt}"
    ev = f.get("evidence", "")
    bots = re.findall(r'([A-Za-z0-9._-]+) blocked by "', ev)
    if not bots:
        m = re.search(r"Blocked: ([^.]+)\.", ev)
        bots = [b.strip() for b in m.group(1).split(",")] if m else []
    if f["check_id"] == "reach.robots.blanket_disallow":
        bots = ["*"]
    if not bots:
        return "hand", f"no bot names in the evidence; read {origin}/robots.txt against: {ev[:200]}"
    groups, rows = robots_groups(txt), txt.splitlines()
    results = []
    for bot in bots:
        best = robots_decide(groups, bot)
        blocked = bool(best) and best[1] == "disallow"
        rule = f' by "{best[1].capitalize()}: {best[2]}" (line {best[3]})' if best else " (no rule in its group covers /)"
        results.append((bot, blocked, f"{'blocked' if blocked else 'allowed'} at /{rule}"))
    quoted = list(dict.fromkeys(re.findall(r'"([^"]+)" \(line (\d+)\)', ev)))
    misquoted = [f"line {n} is {rows[int(n) - 1].strip()!r}, not {q!r}" for q, n in quoted
                 if int(n) > len(rows) or plain(rows[int(n) - 1].split("#")[0]).lower() != plain(q).lower()]
    verdict, detail = tally(results, "blocked at /", "named bot(s)")
    if misquoted:
        verdict = "partly" if verdict == "holds" else verdict
        detail += "; quoted line changed: " + "; ".join(misquoted[:3])
    return verdict, f"{origin}/robots.txt ({len(rows)} lines): " + detail


def v_noindex(f: dict) -> tuple[str, str]:
    results = []
    for u in urls_of(f):
        status, p, headers = page(u)
        xrt = ", ".join(headers.get_all("X-Robots-Tag") or []) if headers else ""
        meta = [m.get("content", "") for m in p.metas if m.get("name", "").lower() in ("robots", "googlebot")]
        hit = "noindex" in (xrt + " ".join(meta)).lower()
        results.append((u, hit, f"{status}, X-Robots-Tag {xrt or '-'}, meta robots {meta or '-'}"))
    return tally(results, "noindex present")


def v_sd_absent(f: dict) -> tuple[str, str]:
    results = []
    for u in urls_of(f):
        status, p, _ = page(u)
        n = len(p.jsonld) + p.microdata + p.rdfa
        results.append((u, status == 200 and n == 0,
                        f"{status}, JSON-LD {len(p.jsonld)}, microdata {p.microdata}, RDFa {p.rdfa}"))
    return tally(results, "no JSON-LD, microdata or RDFa in the raw HTML")


def v_viewport(f: dict) -> tuple[str, str]:
    results = []
    for u in urls_of(f):
        status, p, _ = page(u)
        vp = [m.get("content", "") for m in p.metas if m.get("name", "").lower() == "viewport"]
        results.append((u, status == 200 and not vp, f"{status}, viewport {vp[0]!r}" if vp else f"{status}, no viewport"))
    return tally(results, "no <meta name=\"viewport\">")


def v_dates(f: dict) -> tuple[str, str]:
    results, extra = [], []
    for u in urls_of(f):
        status, p, _ = page(u)
        schema = re.findall(r'"date(?:Published|Modified)"\s*:\s*"([^"]+)"', " ".join(p.jsonld))
        metas = [m.get("content") for m in p.metas
                 if (m.get("property") or m.get("name") or "").lower() in META_DATES and m.get("content")]
        visible = TEXT_DATE.search(p.plain_text)
        seen = ([f"schema {schema[0]}"] if schema else []) + ([f"meta {metas[0]}"] if metas else []) \
            + ([f"<time> {p.times[0]}"] if p.times else []) + ([f"text {visible.group(0)!r}"] if visible else [])
        results.append((u, status == 200 and not schema, f"{status}, " + (", ".join(seen) or "no date anywhere")))
        if not schema and (metas or p.times or visible):
            extra.append(u)
    verdict, detail = tally(results, "no schema datePublished/dateModified")
    if verdict == "holds" and extra:
        verdict = "partly"
        detail += (f". But {len(extra)} of them show a date elsewhere on the page, so \"carry no date at "
                   f"all\" says more than the evidence: the engine reads only schema dates and the first "
                   f"600 characters")
    return verdict, detail


def v_identity(f: dict) -> tuple[str, str]:
    home = (f.get("affected_urls") or [""])[0]
    status, p, _ = page(home)
    types, sameas = set(), False
    for body in p.jsonld:
        try:
            data = json.loads(body)
        except ValueError:
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                t = node.get("@type")
                for x in t if isinstance(t, list) else [t]:
                    if isinstance(x, str):
                        types.add(x.split("/")[-1].lower())
                sameas = sameas or bool(node.get("sameAs"))
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
    identity = types & IDENTITY_TYPES
    owner = re.search(r"(?:©|&copy;|copyright)[^.|]{0,80}", p.plain_text, re.I)
    seen = f"{status}, JSON-LD types {sorted(types) or 'none'}, identity node {sorted(identity) or 'none'}, " \
           f"sameAs {'yes' if sameas else 'no'}" + (f"; a person can read {owner.group(0).strip()!r}" if owner else "")
    ev = f.get("evidence", "")
    if "none of it is an Organization" in ev:
        return ("holds" if not identity else "not"), f"{home}: {seen}"
    if "no sameAs" in ev:
        return ("holds" if identity and not sameas else "not"), f"{home}: {seen}"
    return "hand", f"{home}: {seen}; compare with: {ev[:160]}"


def v_alt(f: dict) -> tuple[str, str]:
    ev = f.get("evidence", "")
    url = ev.split(": ", 1)[0] if ev.startswith("http") else (f.get("affected_urls") or [""])[0]
    m = re.search(r"alt text: (.+?)\. Images were classified", ev)
    srcs = [s.strip() for s in m.group(1).split(", ")] if m else []
    status, p, _ = page(url)
    results = []
    for src in srcs:
        img = next((i for i in p.imgs if i.get("src") and (urljoin(url, i["src"]) == urljoin(url, src)
                                                           or i["src"].endswith(src.rsplit("/", 1)[-1]))), None)
        if img is None:
            results.append((src, False, "not on the page now"))
        else:
            alt = img.get("alt")
            results.append((src, not (alt or "").strip(), f"alt {alt!r}" if alt is not None else "no alt attribute"))
    if not srcs:
        return "hand", f"no image sources in the evidence; check {url} by hand"
    verdict, detail = tally(results, "no alt text", "quoted image(s)")
    return verdict, f"{url} ({status}): {detail}"


def v_zero_width(f: dict) -> tuple[str, str]:
    results = []
    for u in urls_of(f):
        status, p, _ = page(u)
        found = ZERO_WIDTH.findall(p.plain_text)
        kinds = sorted({f"U+{ord(c):04X}" for c in found})
        results.append((u, bool(found), f"{status}, {len(found)} invisible character(s) {kinds}"))
    return tally(results, "zero-width or bidi-control characters in the text")


def v_plain_http(f: dict) -> tuple[str, str]:
    results = []
    for part in f.get("evidence", "").split("; ")[:5]:
        u, _, why = part.partition(": ")
        if not u.startswith("http"):
            continue
        status, final, _, body = fetch(u)
        if "plain http" in why:
            results.append((u, status == 200 and final.startswith("http://"),
                            f"{status}, ends at {final}" if status else body[:90]))
        elif "TLS error" in why:
            results.append((u, status == 0 and "SSL" in body.upper(), f"TLS {'fails: ' + body[:90] if status == 0 else 'works now'}"))
    if not results:
        return "hand", "evidence names no URL to re-fetch"
    return tally(results, "transport problem reproduced", "quoted URL(s)")


def v_quote(f: dict) -> tuple[str, str]:
    """Checks a person must judge (prompt injection, wording): show the quoted text in its context."""
    u = (f.get("affected_urls") or [""])[0]
    status, _, _, body = fetch(u)
    p = Page()
    if status:
        p.feed(body)
    text, html = p.plain_text, re.sub(r"\s+", " ", body)
    out = []
    for q in re.findall('["\u201c]([^"\u201d]{12,120})["\u201d]', f.get("evidence", ""))[:2]:
        i, j = text.lower().find(q.lower()), html.lower().find(q.lower())
        if i >= 0:
            out.append(f"{q!r} on the page: ...{text[max(0, i - 120):i + len(q) + 120]}...")
        elif j >= 0:
            out.append(f"{q!r} in the page's HTML, not its text: ...{html[max(0, j - 100):j + len(q) + 100]}...")
        else:
            out.append(f"{q!r} is not in the page: the engine's own wording, or the page changed")
    return "hand", f"{u} ({status}): " + (" | ".join(out) or "judge the evidence by eye") \
        + f". Engine's verification step: {(f.get('suggested_action') or {}).get('verification', '-')}"


VERIFIERS = {
    "reach.robots.ai_search_bot_blocked": v_robots,
    "reach.robots.ai_training_bot_blocked": v_robots,
    "reach.robots.dual_purpose_bot_blocked": v_robots,
    "reach.robots.blanket_disallow": v_robots,
    "reach.index.noindex_on_content": v_noindex,
    "reach.http.insecure_or_mixed_scheme": v_plain_http,
    "extract.sd.absent_on_eligible_page": v_sd_absent,
    "extract.sd.identity_graph_weak": v_identity,
    "act.blocker.not_mobile_ready": v_viewport,
    "trust.date.absent_on_dated_content": v_dates,
    "read.nontext.informative_image_no_alt": v_alt,
    "trust.integrity.invisible_unicode": v_zero_width,
    "trust.integrity.prompt_injection": v_quote,
}


def check_live(rows: list[dict], by_id: dict, drill_id: str | None) -> None:
    note("\n== 2. What was shown, re-checked on the live site now (independent of the engine and the agent) ==")
    note(f"   fetched {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC with the engine's user agent; "
         f"up to {MAX_URLS} affected URLs per finding")
    for row in rows:
        f = by_id.get(row["id"])
        if not f:
            continue
        cid = f["check_id"]
        if cid.startswith("read.render."):
            hint = ("python tools/count_links.py " + (f.get("affected_urls") or [""])[0]
                    if cid == "read.render.nav_links_js_only" else "compare the raw and rendered counts yourself")
            verdict, detail = "hand", f"needs a browser: {hint}. Engine's verification step: " \
                                      f"{(f.get('suggested_action') or {}).get('verification', '-')}"
        elif cid in VERIFIERS:
            verdict, detail = VERIFIERS[cid](f)
        else:
            verdict, detail = v_quote(f)
        label = f"{row['id']} {cid}" + (" (the drill-down)" if row["id"] == drill_id else "")
        agent = row["verdict"]
        if verdict == "hand":
            say("HAND", f"{label}: no automatic re-check; the agent said {agent}. {detail}")
        elif verdict == "holds":
            tag = "WARN" if agent == "not" else " OK "
            say(tag, f"{label}: holds. {detail}" + (" (the agent said not supported: the video "
                                                    "under-claims, which is safe)" if agent == "not" else ""))
        elif verdict == "partly":
            tag = "FAIL" if row["id"] == drill_id else "WARN"
            say(tag, f"{label}: holds only in part; the agent said {agent}. {detail}")
        else:
            tag = "FAIL" if agent in ("supported", "partly", "?") or row["id"] == drill_id else " OK "
            say(tag, f"{label}: does NOT hold on the live site; the agent said {agent}. {detail}")


def faithful_answer(report: dict, verdicts: list[str] | None = None) -> str:
    """The answer the step-2 prompt asks for, written straight from the report, with no mistakes."""
    findings, s = report["findings"], report["summary"]
    confirmed = [f for f in findings if f.get("confidence") == "confirmed"]
    top = confirmed[:5] + [f for f in findings if f.get("confidence") != "confirmed"][:max(0, 5 - len(confirmed))]
    likely = [f for f in findings if f.get("confidence") == "likely"]
    v = ((verdicts or []) + ["supported"] * 5)[:len(top)]
    drill = next((f for f, x in zip(top, v) if x == "supported"), None)
    ice = lambda f: float((f.get("suggested_action") or {}).get("ice") or 0)  # noqa: E731
    out = ["## 1. Status", f"- **audit_status:** `{report['audit_status']}`",
           "- **Counts by severity:** " + " · ".join(f"{k} {s.get(k, 0)}" for k in SEVERITIES), "",
           "## 2. Top findings", "", "| Rank | ID | Severity | Confidence | ICE | Title | Verdict |",
           "|---|---|---|---|---|---|---|"]
    out += [f"| {i} | {f['id']} | {f['severity']} | {f['confidence']} | {ice(f):.1f} | "
            f"{f['title'].replace('|', chr(92) + '|')} | {x} |" for i, (f, x) in enumerate(zip(top, v), 1)]
    out += ["", f"{len(confirmed)} findings are confirmed and {len(likely)} are likely"
            + (f"; the highest-ranked likely finding is {likely[0]['id']} ({likely[0]['severity']}): "
               f"{likely[0]['title']}." if likely else "."), "", "## 3. Evidence check", ""]
    if drill:
        n = sum(1 for f in findings if f.get("blocked_by") == drill["id"])
        out += [f"## 4. Drill-down: {drill['id']}", f"- Severity / confidence: {drill['severity']} / "
                f"{drill['confidence']}", f"- ICE: {ice(drill):.1f}",
                f"- Findings blocked by it: {n} have `blocked_by` pointing at it."]
    return "\n".join(out) + "\n"


def number_first(answer: str, add_to_high: int) -> str:
    """The severity counts rewritten as "1 critical, 2 high, ..." (adding add_to_high to high)."""
    return re.sub(r"(critical|high|medium|low|info) (\d+)( · )?",
                  lambda m: f"{int(m.group(2)) + add_to_high * (m.group(1) == 'high')} {m.group(1)}"
                            + (", " if m.group(3) else ""), answer)


def self_test() -> int:
    """A faithful answer to the golden report passes; every tampered copy of it fails."""
    global QUIET
    with zipfile.ZipFile(Path(__file__).resolve().parent.parent / "round3-frozen" / "submission.zip") as z:
        report = json.loads(z.read("tests/golden/site_b.audit-report.json").decode("utf-8"))
    good = faithful_answer(report)
    rows = [ln for ln in good.splitlines() if ln.startswith("| ") and FID.search(ln)]
    first, second = rows[0], rows[1]
    fields = second.split(" | ")
    cases = {
        "faithful answer": (good, 0),
        "an invented finding in the table": (good.replace(second, second.replace(FID.search(second).group(0), "F-099")), 1),
        "a severity changed": (good.replace(second, " | ".join(fields[:2] + ["critical"] + fields[3:])), 1),
        "an ICE changed": (good.replace(second, " | ".join(fields[:4] + ["9.9"] + fields[5:])), 1),
        "a title changed": (good.replace(second, " | ".join(fields[:5] + ["Something the engine never said"] + fields[6:])), 1),
        "rows out of report order": (good.replace(first + "\n" + second, second + "\n" + first), 1),
        "the confirmed count changed": (re.sub(r"(\d+) findings are confirmed", lambda m: f"{int(m.group(1)) + 3} findings are confirmed", good), 1),
        "the blocked_by count changed": (re.sub(r"(\d+) have `blocked_by`", lambda m: f"{int(m.group(1)) + 2} have `blocked_by`", good), 1),
        "an id the report lacks, named in passing": (good + "\nF-042 also looks bad.\n", 1),
        "the severity counts changed": (re.sub(r"medium (\d+)", lambda m: f"medium {int(m.group(1)) + 1}", good), 1),
        "counts written '1 critical, 2 high, ...'": (number_first(good, 0), 0),
        "counts written '1 critical, 2 high, ...', one wrong": (number_first(good, 1), 1),
        "the answer read back through code page 437 (PowerShell 5.1)": (good.encode("utf-8").decode("cp437"), 0),
    }
    bad = 0
    for name, (answer, want_fail) in cases.items():
        counts.update({"FAIL": 0, "WARN": 0, "HAND": 0})
        QUIET = True
        check_answer(report, repaired(answer))
        QUIET = False
        caught = counts["FAIL"] > 0
        ok = caught == bool(want_fail)
        bad += not ok
        print(f"[{' OK ' if ok else 'FAIL'}] {name}: {'fails' if caught else 'passes'}"
              f"{'' if ok else ' (expected the opposite)'}")
    print(f"\n{bad} problem(s)")
    return 1 if bad else 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if args == ["--self-test"]:
        return self_test()
    offline = "--offline" in args
    args = [a for a in args if a != "--offline"]
    out_file = None
    if "--report" in args and "--answer" in args:
        report_path, answer_path = args[args.index("--report") + 1], args[args.index("--answer") + 1]
    elif len(args) == 1 and Path(args[0]).is_dir():
        run = Path(args[0])
        report_path, answer_path, out_file = run / "audit-report.json", run / "session.jsonl", run / "finding-check.md"
    else:
        print(__doc__)
        return 2
    report = json.loads(read_text(str(report_path)))
    answer = faithful_answer(report) if str(answer_path) == "auto" else answer_from(str(answer_path))
    site = report.get("site")
    note(f"# Finding check: {site.get('url') if isinstance(site, dict) else site}")
    note(f"report {report_path} (audited {report.get('audited_at')}), answer {answer_path}")
    rows, by_id, drill_id = check_answer(report, answer)
    if not offline and rows:
        check_live(rows, by_id, drill_id)
    note(f"\n{counts['FAIL']} problem(s), {counts['WARN']} warning(s), {counts['HAND']} to check by hand")
    if out_file:
        out_file.write_text("```\n" + "\n".join(lines_out) + "\n```\n", encoding="utf-8")
        print(f"saved {out_file}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
