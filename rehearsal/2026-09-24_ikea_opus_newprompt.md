<!-- rehearsal: ikea_opus_newprompt | url: https://www.ikea.com/ | model: claude-opus-5-5 | harness: 2.1.281 (Claude Code) | python: Python 3.11.15 | playwright: yes | exit: 0 | seconds: 135 | report written: True -->
The audit ran to completion (exit 0). The report is at `audit-output/audit-report.json`, with `report.md` and `fix_patches/` beside it. I didn't create or edit any files myself.

## 1. Status and counts

- **audit_status:** `complete`. 51 findings; none are blocked.
- **By severity:** 0 critical, 7 high, 43 medium, 1 low, 0 info.
- **Not assessed:** `reach.edge.bot_ua_blocked` and `reach.edge.bot_ua_challenged`. These run only when `--probe-bot-ua` is set, and the run didn't set it. The summary also lists 2 instances of `extract.ans.fact_coverage_gap` as "not assessed".

## 2. Top 10 findings (report order)

| # | id | severity | confidence | ICE | title |
|---|---|---|---|---|---|
| 1 | F-001 | high | likely | 7.7 | fact_coverage 2/4: 2 claim(s) cannot be quoted from this page — on /at/en |
| 2 | F-002 | high | likely | 7.7 | fact_coverage 1/2: 1 claim(s) cannot be quoted from this page — on /global/en/newsroom |
| 3 | F-003 | high | likely | 7.7 | fact_coverage 1/2: 1 claim(s) cannot be quoted from this page — on /global/en/stories |
| 4 | F-004 | high | likely | 7.7 | The first screen never says who this is for or what it does — on 13 of 25 crawled pages |
| 5 | F-005 | high | confirmed | 7.3 | The internal link graph only exists after JavaScript runs |
| 6 | F-006 | high | confirmed | 7.3 | 2 of 20 eligible page(s) carry no structured data at all |
| 7 | F-007 | high | confirmed | 7.3 | Structured data disagrees with the visible page on 8 value(s) |
| 8 | F-008 | medium | confirmed | 7.7 | 5 content image(s) carry no alt text — on 18 of 25 crawled pages |
| 9 | F-009 | medium | confirmed | 7.7 | 8 page(s) of dated content carry no date at all |
| 10 | F-010 | medium | confirmed | 7.7 | Invisible / zero-width Unicode in the content of 2 page(s) |

## 3. Evidence check (confirmed critical/high findings)

- **F-005: supported.** On `/ae/ar/`, the raw HTML (urllib) has 184 anchors, which come to exactly **112 unique internal links**, the same as the engine's number. After Playwright renders the page there are **204 unique internal links** (375 internal anchors). The engine counted 219, so my gap is about 92 links against its 107. The claim still holds: the rendered page has almost twice as many links.
- **F-006: supported.** On `/global/en/international-sales/` and `/global/en/jobs/`, the raw HTML has **0** `application/ld+json` blocks, 0 `itemscope`/`itemtype` and 0 RDFa `typeof`/`vocab`.
- **F-007: not supported.** On the product page `…s69274177/`, the schema has `"price":"132"` EUR. The rendered page shows the main price as **"132€ / Hind 132€"**, so the two agree. The other numbers the engine quotes don't look like competing prices: 25€ and 10€ are what switching to a different size adds or takes off, and 68 is a dimension ("68x80 cm").

## 4. Drill-down: F-005 (the highest-ranked finding I marked supported)

- **Evidence (as written):** "https://www.ikea.com/ae/ar/: the raw HTML contains 112 internal links, the rendered DOM contains 219. A crawler that does not execute JavaScript has 107 fewer paths onward from this page, so pages reachable only through those links may never be discovered."
- **Severity / confidence:** high / confirmed. Stage `read`, category discoverability, affects 1 URL.
- **Mechanism:** "Crawl discovery follows anchors in the served HTML; a link that only exists after hydration is not a link the crawler can follow."
- **Suggested action:** "Emit navigation and listing links as real `<a href>` elements in the initial HTML." Effort is medium.
- **Paste-ready patch** (`fix_patches/F-005.read.render.nav_links_js_only.txt`):
  ```html
  <!-- Render navigation server-side. A router link must still emit an href: -->
  <a href="/products/widget">Widget</a>
  <!-- not: <div onclick="navigate(...)">Widget</div> -->
  ```
- **ICE:** 7.3 (impact 8.0, confidence 9.0, ease 5.0).
- **Findings with `blocked_by` pointing at F-005:** 0. No finding in the report is blocked.
- **Verification:** `curl -s https://www.ikea.com/ae/ar/ | grep -o 'href="/[^"]*"' | sort -u | wc -l`
- **Source:** "Handout appendix, How search visibility works".

Of the three confirmed high findings, my own fetches back up F-005 and F-006 but not F-007. The report is exactly as the engine wrote it; these checks are commentary only.
