<!-- rehearsal: guardian_opus_final | url: https://www.theguardian.com/ | model: claude-opus-5-5 | harness: 2.1.281 (Claude Code) | python: Python 3.11.15 | playwright: yes | exit: 0 | seconds: 108 | report written: True -->
I ran the audit on https://www.theguardian.com/. It exited with code 0 in 45.5 s and wrote `audit-output/audit-report.json` and `report.md`. I created, changed and deleted no files myself.

## 1. Status

- **audit_status:** `complete`
- **Counts by severity:** critical 1 · high 0 · medium 42 · low 8 · info 1, for 52 findings in total. 45 of them are `blocked_by` another finding.
- **Checks not assessed:**
  - `reach.edge.bot_ua_blocked` and `reach.edge.bot_ua_challenged`. These are listed in `limitations[]`: the run didn't use `--probe-bot-ua`, so it never checked whether the Guardian's CDN or firewall blocks AI crawlers.
  - `extract.ans.fact_coverage_gap`, on 3 pages. The summary lists it under `suppressed_by_rule` with the reason "not assessed".

## 2. Top 10 findings (report order)

| Rank | ID | Severity | Confidence | ICE | Title |
|---|---|---|---|---|---|
| 1 | F-001 | critical | confirmed | 9.3 | robots.txt blocks 6 AI retrieval crawler(s) that cite sources at answer time |
| 2 | F-002 | medium | confirmed | 7.7 | 4 content image(s) carry no alt text — on the homepage |
| 3 | F-003 | medium | confirmed | 7.7 | 5 content image(s) carry no alt text — on /about |
| 4 | F-004 | medium | confirmed | 7.7 | 5 content image(s) carry no alt text — on /football |
| 5 | F-005 | medium | confirmed | 7.7 | 3 content image(s) carry no alt text — on /sport |
| 6 | F-006 | medium | confirmed | 7.7 | The site does not clearly state who publishes it |
| 7 | F-007 | medium | confirmed | 7.7 | 6 page(s) of dated content carry no date at all |
| 8 | F-008 | medium | confirmed | 7.7 | The main action is labelled 'Learn more', which names no outcome — on the homepage |
| 9 | F-009 | medium | confirmed | 7.7 | The main action is labelled 'Learn more', which names no outcome — on /fashion/2026/sep/23/jess-cartner-morley-on-fashion-in-praise-of-fun-clothes |
| 10 | F-010 | medium | likely | 6.7 | robots.txt blocks 4 crawler(s) whose role is contested |

F-002 to F-007 are `blocked_by` F-001. F-008 to F-010 are not blocked.

## 3. Evidence check

F-001 is the only critical or high finding with `confirmed` confidence. It's a robots.txt check, not a `read.render` one, so I didn't need a Playwright comparison.

- **F-001: supported.**
  - The affected URL, the homepage, returned 200 (1,322,112 bytes of HTML).
  - robots.txt has 104 lines, and line 102 is `Disallow: /`.
  - The user-agent group for that rule starts at line 81. It includes Claude-SearchBot (line 83), Claude-User (84), Amazonbot (95), DuckAssistBot (97) and Google-CloudVertexBot (98).
  - PerplexityBot is at line 79, just before that group. Python's `urllib.robotparser` still says it can't fetch `/`, as it says for the other five. Googlebot can fetch `/`.

## 4. Drill-down: F-001, the highest-ranked supported finding

- **Evidence (as written):** "Amazonbot blocked by "Disallow: /" (line 102); Claude-SearchBot blocked by "Disallow: /" (line 102); Claude-User blocked by "Disallow: /" (line 102); DuckAssistBot blocked by "Disallow: /" (line 102); Google-CloudVertexBot blocked by "Disallow: /" (line 102); PerplexityBot blocked by "Disallow: /" (line 102). Each of these fetches pages at answer time to ground or cite a response, so blocking them removes this brand from those assistants' answers entirely. 25 of 25 discovered paths are disallowed for these agents. Bot classification from a snapshot dated 2026-09-09 (upstream commit 0e111dcc24cb). 4 training-only bot(s) are also blocked, which is a separate and legitimate licensing choice."
- **Severity / confidence:** critical / confirmed. Stage is reach; category is discoverability.
- **Mechanism:** "Retrieval crawlers fetch the page at the moment a user asks a question; if they are refused, the brand cannot appear as a source no matter how good the page is."
- **Patch** (`fix_patches/F-001.reach.robots.ai_search_bot_blocked.txt`):
  ```
  User-agent: Amazonbot
  Allow: /

  User-agent: Claude-SearchBot
  Allow: /

  User-agent: Claude-User
  Allow: /

  User-agent: DuckAssistBot
  Allow: /

  User-agent: Google-CloudVertexBot
  Allow: /

  User-agent: PerplexityBot
  Allow: /
  ```
  Summary: "Allow Amazonbot, Claude-SearchBot, Claude-User, DuckAssistBot, Google-CloudVertexBot, PerplexityBot in robots.txt, keeping any training-bot policy separate."
- **ICE:** 9.3, from impact 10.0, confidence 9.0 and ease 9.0. Effort is low.
- **Findings blocked by it:** 45 have `blocked_by` = F-001.
- **Verification step:** "curl -s https://www.theguardian.com/robots.txt and confirm each of Amazonbot, Claude-SearchBot, Claude-User, DuckAssistBot, Google-CloudVertexBot, PerplexityBot has an Allow rule that is at least as specific as any Disallow"

The Guardian publishes a licence link on line 104 of its robots.txt, so this block is probably a deliberate licensing choice rather than an accident. That's my commentary only; the engine's finding stands as written.
