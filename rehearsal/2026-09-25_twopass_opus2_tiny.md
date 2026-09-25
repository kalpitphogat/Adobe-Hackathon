<!-- rehearsal: twopass_opus2_tiny | site: 127.0.0.1:8601 tiny test page | model: claude-opus-5-5 | harness: 2.1.282 (Claude Code) via claude -p | python: Python 3.11.15 | playwright: 1.56.0 (Chromium 141) | host: Linux container | prompt: two-pass, final | exit: 0 -->
<!-- engine check after the run:
added by the run      : 84 file(s): __pycache__, audit-output, audit-precheck
RESULT                : ENGINE UNCHANGED
-->

Test sites on 127.0.0.1 need --allow-private-hosts, so the prompt had one extra sentence after the URL: "(this is a test site on this machine: add --allow-private-hosts to both orchestrator runs)".

## Tool calls
```text
session init: model=claude-opus-5-5 tools=39 skills/commands seen=['ai-readiness-orchestrator', 'answerability-audit', 'crawl-access-audit', 'engagement-audit', 'render-gap-audit', 'structured-data-audit', 'trust-freshness-audit']
 1. Skill: ai-readiness-orchestrator
 2. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8601/ --no-render --out ./audit-precheck --allow-private-hosts
 3. Bash: python -c "import json;rows=[json.loads(l) for l in open('audit-precheck/evidence/pages.jsonl') if l.strip()];print(len(rows), sum(1 for r in rows if r.get('sta
 4. Bash: python -c "import json;rows=[json.loads(l) for l in open('audit-precheck/evidence/pages.jsonl') if l.strip()];[print(r.get('url'),r.get('status'),type(r.get('li
 5. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8601/ --bundle ./audit-precheck/evidence --out ./audit-output --allow-private-ho
 6. Read: /tmp/claude-0/-home-user-Adobe-Hackathon/ef823eec-15e5-5f7f-aa17-448c5dab8088/scratchpad/reh/opus2_tiny/brand-ai-readiness-audit/audit-output/audit-report.json
 7. Bash: python -c "import urllib.request,re;h=urllib.request.urlopen('http://127.0.0.1:8601/').read().decode('utf-8','replace');print(len(h),'bytes; meta tags:',len(re.
result: subtype=success turns=9 duration=37s
```

## Final answer
**Pass 2:** I re-analysed the pass-1 evidence with `--bundle` instead of crawling again. All 3 pages returned 200 and each had at least one internal link, so nothing suggested navigation built by JavaScript.

### 1. Status and counts
- **audit_status:** `partial`
- **By severity:** critical 0 · high 4 · medium 7 · low 0 · info 0 (11 findings in total, none blocked)
- **Not assessed:**
  - Listed in `limitations[]`: `reach.edge.bot_ua_blocked` and `reach.edge.bot_ua_challenged`, because `--probe-bot-ua` was not set.
  - Also marked not assessed in `suppressed_by_rule`, because rendering was off: `act.perf.above_fold_weight`, `read.render.nav_links_js_only`, `read.render.raw_text_gap`, and one instance of `extract.ans.fact_coverage_gap`.

### 2. Top 5 findings
| Rank | ID | Severity | Confidence | ICE | Title |
|---|---|---|---|---|---|
| 1 | F-001 | high | confirmed | 8.7 | 3 page(s) declare no mobile viewport |
| 2 | F-002 | high | likely | 7.7 | fact_coverage 0/2: 2 claim(s) cannot be quoted from this page — on /about.html |
| 3 | F-003 | high | likely | 7.7 | fact_coverage 0/2: 2 claim(s) cannot be quoted from this page — on /contact.html |
| 4 | F-004 | high | confirmed | 7.3 | Transport security problems affect how crawlers and browsers treat the site |
| 5 | F-005 | medium | confirmed | 7.7 | The page title is 'Harbor Tools', which does not say what the page is about |

### 3. Evidence check
- **F-001 (high, confirmed): supported.** I fetched `http://127.0.0.1:8601/` with urllib: 525 bytes, 2 `<meta>` tags, 0 with `name="viewport"`. The check isn't a `read.render` one and doesn't compare raw HTML with the rendered page, so Playwright wasn't needed. It was the first check and it held, so I stopped there.

### 4. Drill-down: F-001 (`act.blocker.not_mobile_ready`)
- **Severity / confidence:** high / confirmed. It affects 3 pages: `/`, `/about.html` and `/contact.html`.
- **Evidence:** "No `<meta name="viewport">` on: [all 3 URLs]. Without it a mobile browser renders at a desktop width and scales the whole page down, so body text arrives too small to read and every tap target is too small to hit."
- **Mechanism:** "The viewport meta tag is what tells a mobile browser to lay out at device width instead of emulating a desktop and zooming out."
- **Patch** (`fix_patches/F-001.act.blocker.not_mobile_ready.txt`):
  ```html
  <meta name="viewport" content="width=device-width, initial-scale=1">
  ```
- **ICE:** 8.7 (impact 8.0, confidence 9.0, ease 9.0), effort low. The source cited is WCAG 2.2 SC 1.4.10 Reflow.
- **Findings with `blocked_by` pointing at it:** 0. Every finding has `blocked_by: null`.
- **Verification:** `curl -s http://127.0.0.1:8601/ | grep -i 'name="viewport"'`
