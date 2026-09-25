<!-- rehearsal: twopass_normal | site: 127.0.0.1:8604 normal test site | model: claude-opus-5-5 | harness: 2.1.282 (Claude Code) via claude -p | python: Python 3.11.15 | playwright: 1.56.0 (Chromium 141) | host: Linux container | prompt: two-pass, first draft (without the no-pipes sentence) | exit: 0 -->
<!-- engine check after the run:
added by the run      : 86 file(s): __pycache__, audit-output, audit-precheck
RESULT                : ENGINE UNCHANGED
-->

Test sites on 127.0.0.1 need --allow-private-hosts, so the prompt had one extra sentence after the URL: "(this is a test site on this machine: add --allow-private-hosts to both orchestrator runs)".

## Tool calls
```text
session init: model=claude-opus-5-5 tools=39 skills/commands seen=['ai-readiness-orchestrator', 'answerability-audit', 'crawl-access-audit', 'engagement-audit', 'render-gap-audit', 'structured-data-audit', 'trust-freshness-audit']
 1. Skill: ai-readiness-orchestrator
 2. Bash: ls; ls skills 2>/dev/null; ls .claude/skills/ai-readiness-orchestrator/scripts 2>/dev/null
 3. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8604/ --no-render --out ./audit-precheck --allow-private-hosts; echo EXIT=$?
 4. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8604/ --no-render --out ./audit-precheck --allow-private-hosts
 5. Bash: python -c "
import json
n=0;t=0
for l in open('audit-precheck/evidence/pages.jsonl'):
    l=l.strip()
    if not l: continue
    p=json.loads(l); t+=1
    li=(p
 6. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8604/ --bundle ./audit-precheck/evidence --out ./audit-output --allow-private-ho
 7. Bash: python -c "
import json
r=json.load(open('audit-output/audit-report.json'))
print(r['audit_status']); print(json.dumps(r['summary'],indent=1))
for l in r.get('l
 8. Bash: python -c "
import json
r=json.load(open('audit-output/audit-report.json'))
print(json.dumps(r['findings'][0],indent=1))
print(sum(1 for f in r['findings'] if f
 9. Bash: python -c "
import urllib.request,re
h=urllib.request.urlopen('http://127.0.0.1:8604/').read().decode('utf-8','replace')
print('bytes',len(h),'meta tags',len(re
result: subtype=success turns=11 duration=48s
```

## Final answer
Pass 2 re-analysed the pass 1 evidence without crawling again (`--bundle ./audit-precheck/evidence`). None of the 6 crawled pages had status 200 with an empty `links.internal` list, so there was no sign that JavaScript was building content the crawler missed.

**1. Status**
- **audit_status:** `partial`
- **Findings by severity:** 0 critical, 3 high, 6 medium, 0 low, 0 info. That is 9 findings in total, and none are `blocked_by` another finding.
- **Checks listed as not assessed:**
  - `reach.edge.bot_ua_blocked` and `reach.edge.bot_ua_challenged`, because `--probe-bot-ua` was not set.
  - `read.render.raw_text_gap` and `read.render.nav_links_js_only`, because the evidence was collected with `--no-render`.
  - `extract.ans.fact_coverage_gap` (6 pages) and `act.perf.above_fold_weight` (1).

**2. Top 5 findings**

| Rank | id | Severity | Confidence | ICE | Title |
|---|---|---|---|---|---|
| 1 | F-001 | high | confirmed | 8.7 | 6 page(s) declare no mobile viewport |
| 2 | F-002 | high | confirmed | 7.3 | Transport security problems affect how crawlers and browsers treat the site |
| 3 | F-003 | high | confirmed | 7.3 | 6 of 6 eligible page(s) carry no structured data at all |
| 4 | F-004 | medium | confirmed | 7.7 | The site does not clearly state who publishes it |
| 5 | F-005 | medium | confirmed | 7.7 | The visitor reaches the end of this page with nowhere to go — on 5 of 6 crawled pages |

**3. Evidence check**
- **F-001 (`act.blocker.not_mobile_ready`): supported.** I fetched `http://127.0.0.1:8604/` with urllib. The raw HTML is 2,691 bytes with 2 `<meta>` tags and 0 viewport metas, and the word "viewport" does not appear at all. The page has 0 `<script>` tags, so nothing could add a viewport after load. I didn't use Playwright because this is not a `read.render` check and its evidence doesn't compare raw and rendered versions. I stopped at this first check, as instructed.

**4. Drill-down: F-001**
- **Evidence:** "No `<meta name="viewport">` on: /, /about.html, /contact.html, /faq.html, /pricing.html, /products.html. Without it a mobile browser renders at a desktop width and scales the whole page down, so body text arrives too small to read and every tap target is too small to hit."
- **Severity / confidence:** high / confirmed. It is an engagement finding at the act stage.
- **Mechanism:** "The viewport meta tag is what tells a mobile browser to lay out at device width instead of emulating a desktop and zooming out." The report's source is WCAG 2.2 Success Criterion 1.4.10 Reflow.
- **Patch:** `<meta name="viewport" content="width=device-width, initial-scale=1">` (also written to `audit-output/fix_patches/F-001.act.blocker.not_mobile_ready.txt`)
- **ICE:** 8.7, from impact 8.0, confidence 9.0 and ease 9.0. Effort is low.
- **Findings with `blocked_by` pointing at F-001:** 0.
- **Verification:** `curl -s http://127.0.0.1:8604/ | grep -i 'name="viewport"'`

The report files are `audit-output/audit-report.json` and `audit-output/report.md`. I didn't create, change or delete any files; the only files written are the orchestrator's outputs.
