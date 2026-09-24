#!/usr/bin/env python3
"""Stage extract: can a value inside a table be quoted with its meaning?

A table is how a page states a set of facts that only mean something in pairs:
a plan name and its price, a spec and its value, a country and its shipping
time. A machine can only quote such a value if it can bind the cell to what the
column or row SAYS it is. That binding is carried by `<th>`, `scope=`,
`<thead>` or a `<caption>` - and by nothing else. Strip those and a retrieval
system reading the page sees a grid of loose strings: it can find "49" but
cannot say 49 what, of what, per what, so it will not quote the number at all,
or worse, will attach it to the wrong label.

Deliberately conservative, because layout tables are still common and a false
accusation here is worse than a miss:

  * a table with a role of presentation or none is a layout table by the
    author's own declaration and is never judged;
  * fewer than three rows, or fewer than two columns, is not a data grid;
  * any one of <th>, scope=, <thead> or <caption> counts as a header, so a
    table that labels its data in ANY of the four supported ways passes.
"""

from __future__ import annotations

import re

from bundle import action, finding

CHECKS = [
    {"id": "extract.ans.table_not_extractable", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "medium", "skill": "answerability-audit"},
]

_TABLE = re.compile(r"<table\b([^>]*)>(.*?)</table\s*>", re.I | re.S)
_ROW = re.compile(r"<tr\b", re.I)
_CELL = re.compile(r"<t[dh]\b", re.I)
_ROW_BLOCK = re.compile(r"<tr\b[^>]*>(.*?)(?=<tr\b|</t(?:body|able)\s*>|$)", re.I | re.S)
# Any one of these means the table labels its data.
_HEADER = re.compile(r"<th\b|\bscope\s*=|<thead\b|<caption\b", re.I)
# The author declaring the table is layout, not data.
_PRESENTATION = re.compile(r"\brole\s*=\s*[\"']?(presentation|none)\b", re.I)

MIN_ROWS = 3   # a header-plus-two-rows grid is the smallest real data table
MIN_COLS = 2   # one column is a list, not a table of paired facts


def _raw_html(b, page: dict) -> str:
    rel = page.get("raw_html_path")
    if not rel:
        return ""
    try:
        return (b.root / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _widest_row(body: str) -> int:
    """Most cells in any single row - the table's column count."""
    widest = 0
    for row in _ROW_BLOCK.findall(body):
        widest = max(widest, len(_CELL.findall(row)))
    return widest


def _unlabelled_tables(html: str) -> list[tuple[int, int]]:
    """(rows, cols) for each data table that labels none of its data."""
    out: list[tuple[int, int]] = []
    for attrs, body in _TABLE.findall(html):
        if _PRESENTATION.search(attrs):
            continue                      # declared a layout table by the author
        if _HEADER.search(body):
            continue                      # labelled in one of the four supported ways
        rows = len(_ROW.findall(body))
        cols = _widest_row(body)
        if rows >= MIN_ROWS and cols >= MIN_COLS:
            out.append((rows, cols))
    return out


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []

    offenders: list[tuple[str, int, int]] = []
    for page in b.html_pages():
        html = _raw_html(b, page)
        if not html:
            continue
        for rows, cols in _unlabelled_tables(html):
            offenders.append((page["url"], rows, cols))

    if offenders:
        urls = sorted({u for u, _, _ in offenders})
        examples = "; ".join(
            f"{u} ({rows}x{cols} grid)" for u, rows, cols in offenders[:3]
        )
        findings.append(finding(
            check_id="extract.ans.table_not_extractable",
            title=f"Table data on {len(urls)} page(s) carries no column or row labels",
            severity="medium", confidence="confirmed", stage="extract",
            category="discoverability", scope="site" if len(urls) > 1 else "url",
            evidence=(
                f"{len(offenders)} data table(s) across {len(urls)} page(s) contain no <th>, no "
                f"scope attribute, no <thead> and no <caption>, so no cell is bound to what it "
                f"means: {examples}. A retrieval system can read the values but cannot say what "
                f"any of them is a value OF, so it will either decline to quote the table or "
                f"attach a number to the wrong label. Tables marked role=\"presentation\" and "
                f"grids smaller than {MIN_ROWS}x{MIN_COLS} were not judged."
            ),
            affected_urls=urls,
            action=action(
                summary="Label the table: make the first row <th> cells and add a <caption>.",
                effort="low",
                mechanism=(
                    "Extractors bind a cell to its column through the header row; with no <th>, "
                    "scope or caption there is no machine-readable link between a value and its "
                    "meaning, so the fact cannot be quoted with the label that makes it true."
                ),
                source="references/geo-methods.md",
                patch=(
                    "<table>\n"
                    "  <caption>__FILL_IN__:what_this_table_lists</caption>\n"
                    "  <thead>\n"
                    "    <tr><th scope=\"col\">__FILL_IN__:column_1</th>"
                    "<th scope=\"col\">__FILL_IN__:column_2</th></tr>\n"
                    "  </thead>\n"
                    "  <tbody>\n"
                    "    <tr><th scope=\"row\">__FILL_IN__:row_label</th><td>__FILL_IN__:value</td></tr>\n"
                    "  </tbody>\n"
                    "</table>"
                ),
                verification=(
                    "For each data table, confirm every column has a <th scope=\"col\"> and the "
                    "table has a <caption> naming what it lists."
                ),
            ),
        ))

    return findings, skipped, []
