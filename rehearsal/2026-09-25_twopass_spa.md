<!-- rehearsal: twopass_spa | site: 127.0.0.1:8603 JS-only test app | model: claude-opus-5-5 | harness: 2.1.282 (Claude Code) via claude -p | python: Python 3.11.15 | playwright: 1.56.0 (Chromium 141) | host: Linux container | prompt: two-pass, first draft (without the no-pipes sentence) | exit: 0 -->
<!-- engine check after the run:
added by the run      : 96 file(s): __pycache__, audit-output, audit-precheck
RESULT                : ENGINE UNCHANGED
-->

Test sites on 127.0.0.1 need --allow-private-hosts, so the prompt had one extra sentence after the URL: "(this is a test site on this machine: add --allow-private-hosts to both orchestrator runs)".

## Tool calls
```text
session init: model=claude-opus-5-5 tools=39 skills/commands seen=['ai-readiness-orchestrator', 'answerability-audit', 'crawl-access-audit', 'engagement-audit', 'render-gap-audit', 'structured-data-audit', 'trust-freshness-audit']
 1. Skill: ai-readiness-orchestrator
 2. Bash: ls; ls skills 2>/dev/null; ls .claude/skills; python .claude/skills/ai-readiness-orchestrator/scripts/orchestrate.py --help 2>&1 | head -30; ls skills/ai-readin
 3. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8603/ --no-render --out ./audit-precheck --allow-private-hosts 2>&1 | tail -15; 
 4. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8603/ --no-render --out ./audit-precheck --allow-private-hosts 2>&1 | tail -15
 5. Bash: python -c "
import json
rows=[json.loads(l) for l in open('audit-precheck/evidence/pages.jsonl') if l.strip()]
def st(r): return r.get('status', r.get('status_c
 6. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8603/ --out ./audit-output --allow-private-hosts 2>&1 | tail -15
 7. Bash: python -c "
import json
r=json.load(open('audit-output/audit-report.json'))
print(r['audit_status']); print(json.dumps(r['summary'],indent=1))
print('LIMITATION
 8. Bash: python -c "
import json
r=json.load(open('audit-output/audit-report.json'))
f=r['findings'][0]; print(json.dumps(f,indent=1))
print('blocked_by count', sum(1 fo
 9. Bash: python -c "
import urllib.request,re
r=urllib.request.urlopen('http://127.0.0.1:8603/',timeout=10); h=r.read().decode('utf-8','replace')
print('status',r.status
result: subtype=success turns=11 duration=54s
```

## Final answer
The audit finished with status `complete`, and my evidence check supports the top finding.

**Which pass 2:** The browser-free run found 1 page (the homepage) with status 200 and no internal links. The crawler could be missing links that JavaScript builds, so I ran the full browser pass: `http://127.0.0.1:8603/ --out ./audit-output --allow-private-hosts`.

### 1. Status, counts, not assessed
- **audit_status:** `complete`. The browser-free pass 1 was `partial`, with 7 findings.
- **By severity:** 13 findings in total: critical 0, high 5, medium 7, low 1, info 0. Six of them have `blocked_by` set.
- **Not assessed:** `reach.edge.bot_ua_blocked` and `reach.edge.bot_ua_challenged`, because `--probe-bot-ua` was not set. `extract.ans.fact_coverage_gap` is also listed as "not assessed" under `suppressed_by_rule`.

### 2. Top 5 findings (report order)
| Rank | ID | Severity | Confidence | ICE | Title |
|---|---|---|---|---|---|
| 1 | F-001 | high | confirmed | 8.7 | 1 page(s) declare no mobile viewport |
| 2 | F-002 | high | likely | 7.7 | This home page offers the visitor nothing to do |
| 3 | F-003 | high | confirmed | 7.3 | Transport security problems affect how crawlers and browsers treat the site |
| 4 | F-004 | high | confirmed | 7.3 | The internal link graph only exists after JavaScript runs |
| 5 | F-005 | high | confirmed | 6.3 | Most of this page's text only exists after JavaScript runs |

### 3. Evidence check
- **F-001 (`act.blocker.not_mobile_ready`), supported.** Fetching `http://127.0.0.1:8603/` with urllib returned status 200 and 228 bytes of HTML, with 2 `<meta>` tags and 0 viewport metas. I also loaded it in Playwright, and the rendered page has 0 viewport metas too. The check stopped here because the first finding was supported, so F-003, F-004 and F-005 were not checked.

### 4. Drill-down: F-001
- **Evidence:** "No `<meta name="viewport">` on: http://127.0.0.1:8603/. Without it a mobile browser renders at a desktop width and scales the whole page down, so body text arrives too small to read and every tap target is too small to hit."
- **Severity / confidence:** high / confirmed. It is an engagement finding in the act stage.
- **Mechanism:** "The viewport meta tag is what tells a mobile browser to lay out at device width instead of emulating a desktop and zooming out." The source cited is WCAG 2.2 SC 1.4.10 Reflow.
- **Patch** (saved at `audit-output/fix_patches/F-001.act.blocker.not_mobile_ready.txt`):
  ```html
  <meta name="viewport" content="width=device-width, initial-scale=1">
  ```
- **ICE:** impact 8.0, confidence 9.0, ease 9.0, giving 8.7. Effort is low.
- **Findings with `blocked_by` pointing at it:** 0. The six blocked findings all point at F-003.
- **Verification:** `curl -s http://127.0.0.1:8603/ | grep -i 'name="viewport"'`

I did not create, change or delete any files myself. The two orchestrator runs wrote `audit-precheck/` and `audit-output/`.
