<!-- rehearsal: twopass_tinylinks | site: 127.0.0.1:8601 tiny test page, 2 internal + 4 social links | model: claude-opus-5-5 | harness: 2.1.282 (Claude Code) via claude -p | python: Python 3.11.15 | playwright: 1.56.0 (Chromium 141) | host: Linux container | prompt: two-pass, first draft (without the no-pipes sentence) | exit: 0 -->
<!-- engine check after the run:
added by the run      : 84 file(s): __pycache__, audit-output, audit-precheck
RESULT                : ENGINE UNCHANGED
-->

Test sites on 127.0.0.1 need --allow-private-hosts, so the prompt had one extra sentence after the URL: "(this is a test site on this machine: add --allow-private-hosts to both orchestrator runs)".

## Tool calls
```text
session init: model=claude-opus-5-5 tools=39 skills/commands seen=['ai-readiness-orchestrator', 'answerability-audit', 'crawl-access-audit', 'engagement-audit', 'render-gap-audit', 'structured-data-audit', 'trust-freshness-audit']
 1. Skill: ai-readiness-orchestrator
 2. Bash: ls; ls skills/ai-readiness-orchestrator/scripts 2>/dev/null || ls .claude/skills/ai-readiness-orchestrator/scripts
 3. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8601/ --no-render --out ./audit-precheck --allow-private-hosts; echo EXIT=$?
 4. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8601/ --no-render --out ./audit-precheck --allow-private-hosts
 5. Bash: python -c "
import json
rows=[json.loads(l) for l in open('audit-precheck/evidence/pages.jsonl') if l.strip()]
hit=[r.get('url') for r in rows if r.get('status'
 6. Bash: python -c "
import json
for l in open('audit-precheck/evidence/pages.jsonl'):
    r=json.loads(l); print(r.get('url'), r.get('status'), type(r.get('links')).__n
 7. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py --bundle ./audit-precheck/evidence --out ./audit-output --allow-private-hosts
 8. Bash: python -c "
import json
r=json.load(open('audit-output/audit-report.json'))
print('status',r['audit_status']); print('summary',json.dumps(r['summary']))
print('
 9. Bash: python -c "
import json
r=json.load(open('audit-output/audit-report.json'))
for l in r.get('limitations',[]): print(json.dumps(l)); print()
f=r['findings'][0]; 
10. Bash: python -c "
import urllib.request,re
for u in ['http://127.0.0.1:8601/','http://127.0.0.1:8601/about.html','http://127.0.0.1:8601/contact.html']:
    h=urllib.r
result: subtype=success turns=12 duration=54s
```

## Final answer
Both passes finished and the report is at `audit-output/audit-report.json`. The site has 11 findings: 4 high and 7 medium.

**Which pass 2 I ran:** I re-analysed the pass 1 evidence (`--bundle ./audit-precheck/evidence`) without crawling again. None of the 3 crawled pages had status 200 with an empty `links.internal` list; the homepage has 2 internal links and the about and contact pages have 1 each.

### 1. Status and counts
- **audit_status:** `partial`
- **Counts by severity:** critical 0, high 4, medium 7, low 0, info 0. No findings are blocked by another.
- **Checks not assessed:**
  - `reach.edge.bot_ua_blocked` and `reach.edge.bot_ua_challenged`, because `--probe-bot-ua` was not set.
  - `read.render.raw_text_gap` and `read.render.nav_links_js_only`.
  - `act.perf.above_fold_weight`.
  - `extract.ans.fact_coverage_gap` on 1 page.

### 2. Top 5 findings
| # | id | severity | confidence | ICE | title |
|---|---|---|---|---|---|
| 1 | F-001 | high | confirmed | 8.7 | 3 page(s) declare no mobile viewport |
| 2 | F-002 | high | likely | 7.7 | fact_coverage 0/2: 2 claim(s) cannot be quoted from this page — on /about.html |
| 3 | F-003 | high | likely | 7.7 | fact_coverage 0/2: 2 claim(s) cannot be quoted from this page — on /contact.html |
| 4 | F-004 | high | confirmed | 7.3 | Transport security problems affect how crawlers and browsers treat the site |
| 5 | F-005 | medium | confirmed | 7.7 | The page title is 'Harbor Tools', which does not say what the page is about |

### 3. Evidence check
- **F-001 (`act.blocker.not_mobile_ready`): supported.** I fetched the raw HTML of all 3 affected URLs with urllib. The pages are 525, 465 and 467 bytes, and each has 2 `<meta>` tags but 0 `name="viewport"` tags. The check reads only the raw HTML and is not a `read.render` check, so I didn't need Playwright. I stopped after this first check.

### 4. Drill-down: F-001
- **Evidence:** "No `<meta name="viewport">` on: http://127.0.0.1:8601/, http://127.0.0.1:8601/about.html, http://127.0.0.1:8601/contact.html. Without it a mobile browser renders at a desktop width and scales the whole page down, so body text arrives too small to read and every tap target is too small to hit."
- **Severity and confidence:** high, confirmed. It is an engagement finding in the act stage, with effort rated low.
- **Mechanism:** "The viewport meta tag is what tells a mobile browser to lay out at device width instead of emulating a desktop and zooming out." The report cites WCAG 2.2 SC 1.4.10 Reflow as its source.
- **Paste-ready patch** (also saved at `fix_patches/F-001.act.blocker.not_mobile_ready.txt`):
  ```html
  <meta name="viewport" content="width=device-width, initial-scale=1">
  ```
- **ICE:** 8.7, from impact 8.0, confidence 9.0 and ease 9.0.
- **Findings with `blocked_by` pointing at F-001:** 0.
- **Verification step:** `curl -s http://127.0.0.1:8601/ | grep -i 'name="viewport"'`
