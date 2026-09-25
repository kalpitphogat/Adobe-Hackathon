<!-- rehearsal: twopass_opus2_spa | site: 127.0.0.1:8603 JS-only test app | model: claude-opus-5-5 | harness: 2.1.282 (Claude Code) via claude -p | python: Python 3.11.15 | playwright: 1.56.0 (Chromium 141) | host: Linux container | prompt: two-pass, final | exit: 0 -->
<!-- engine check after the run:
added by the run      : 93 file(s): __pycache__, audit-output, audit-precheck
RESULT                : ENGINE UNCHANGED
-->

Test sites on 127.0.0.1 need --allow-private-hosts, so the prompt had one extra sentence after the URL: "(this is a test site on this machine: add --allow-private-hosts to both orchestrator runs)".

## Tool calls
```text
session init: model=claude-opus-5-5 tools=39 skills/commands seen=['ai-readiness-orchestrator', 'answerability-audit', 'crawl-access-audit', 'engagement-audit', 'render-gap-audit', 'structured-data-audit', 'trust-freshness-audit']
 1. Skill: ai-readiness-orchestrator
 2. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8603/ --no-render --out ./audit-precheck --allow-private-hosts
 3. Bash: python -c "import json;rows=[json.loads(l) for l in open('audit-precheck/evidence/pages.jsonl') if l.strip()];print(len(rows));print(sum(1 for r in rows if r.ge
 4. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8603/ --out ./audit-output --allow-private-hosts
 5. Read: /tmp/claude-0/-home-user-Adobe-Hackathon/ef823eec-15e5-5f7f-aa17-448c5dab8088/scratchpad/reh/opus2_spa/brand-ai-readiness-audit/audit-output/audit-report.json
 6. Bash: python -c "import urllib.request,re;r=urllib.request.urlopen('http://127.0.0.1:8603/');h=r.read().decode('utf-8','replace');print(r.status,len(h));print('viewpo
result: subtype=success turns=8 duration=42s
```

## Final answer
Pass 2 was the full run with the browser (`--out ./audit-output`). Pass 1 found 1 page with status 200 and no internal links (the homepage, the only page crawled), so the crawler may have been missing links that JavaScript builds.

## 1. Status and counts
- **audit_status:** `complete` (pass 1 without the browser was `partial`).
- **Severity:** 0 critical, 5 high, 7 medium, 1 low, 0 info. 13 findings in total, 6 of them marked `blocked_by`.
- **Not assessed:** `reach.edge.bot_ua_blocked` and `reach.edge.bot_ua_challenged`, because `--probe-bot-ua` was not set. `extract.ans.fact_coverage_gap` is also listed as "not assessed" under suppressed_by_rule.

## 2. Top 5 findings

| Rank | id | Severity | Confidence | ICE | Title |
|---|---|---|---|---|---|
| 1 | F-001 | high | confirmed | 8.7 | 1 page(s) declare no mobile viewport |
| 2 | F-002 | high | likely | 7.7 | This home page offers the visitor nothing to do |
| 3 | F-003 | high | confirmed | 7.3 | Transport security problems affect how crawlers and browsers treat the site |
| 4 | F-004 | high | confirmed | 7.3 | The internal link graph only exists after JavaScript runs |
| 5 | F-005 | high | confirmed | 6.3 | Most of this page's text only exists after JavaScript runs |

## 3. Evidence check
- **F-001 (high, confirmed): supported.** A urllib fetch of `http://127.0.0.1:8603/` returned status 200 and 228 bytes of HTML. It has 0 viewport meta tags; the only meta tags are `charset` and `description`. The check supported the first finding, so I stopped there. Playwright wasn't needed because F-001 is not a `read.render` check and its evidence doesn't compare raw and rendered HTML.

A note that doesn't change the report: F-002 says the home page has "0 links and 0 form(s)", but F-004 says the page has 8 internal links once JavaScript runs. F-002 therefore seems to be based on the raw HTML only.

## 4. Drill-down: F-001 (`act.blocker.not_mobile_ready`)
- **Severity / confidence:** high / confirmed. Category is engagement, stage is act.
- **Evidence:** "No `<meta name="viewport">` on: http://127.0.0.1:8603/. Without it a mobile browser renders at a desktop width and scales the whole page down, so body text arrives too small to read and every tap target is too small to hit."
- **Mechanism:** "The viewport meta tag is what tells a mobile browser to lay out at device width instead of emulating a desktop and zooming out." (Source: WCAG 2.2 SC 1.4.10 Reflow.)
- **Patch** (`fix_patches/F-001.act.blocker.not_mobile_ready.txt`):
  ```html
  <meta name="viewport" content="width=device-width, initial-scale=1">
  ```
- **ICE:** 8.7, from impact 8.0, confidence 9.0 and ease 9.0. Effort is low.
- **Findings with `blocked_by` pointing at it:** 0. All 6 blocked findings point at F-003.
- **Verification:** `curl -s http://127.0.0.1:8603/ | grep -i 'name="viewport"'`
