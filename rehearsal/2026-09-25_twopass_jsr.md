<!-- rehearsal: twopass_jsr | site: jsr.io | model: claude-opus-5-5 | harness: 2.1.282 (Claude Code) via claude -p | python: Python 3.11.15 | playwright: 1.56.0 (Chromium 141) | host: Linux container | prompt: two-pass, first draft (without the no-pipes sentence) | exit: 0 -->
<!-- engine check after the run:
added by the run      : 166 file(s): __pycache__, audit-output, audit-precheck
RESULT                : ENGINE UNCHANGED
-->

## Tool calls
```text
session init: model=claude-opus-5-5 tools=39 skills/commands seen=['ai-readiness-orchestrator', 'answerability-audit', 'crawl-access-audit', 'engagement-audit', 'render-gap-audit', 'structured-data-audit', 'trust-freshness-audit']
 1. Skill: ai-readiness-orchestrator
 2. Bash: ls; ls skills/ai-readiness-orchestrator/scripts 2>/dev/null || ls .claude/skills/ai-readiness-orchestrator/scripts
 3. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://jsr.io/ --no-render --out ./audit-precheck; echo EXIT=$?
 4. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://jsr.io/ --no-render --out ./audit-precheck
 5. Bash: python -c "import json;rows=[json.loads(l) for l in open('audit-precheck/evidence/pages.jsonl') if l.strip()];e=[r.get('url') for r in rows if r.get('status')==
 6. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py --bundle ./audit-precheck/evidence --out ./audit-output
 7. Bash: python -c "
import json;r=json.load(open('audit-output/audit-report.json'))
print(r['audit_status']);print(json.dumps(r['summary']))
for l in r.get('limitations
 8. Bash: python -c "
import json;r=json.load(open('audit-output/audit-report.json'))
for l in r.get('limitations',[]): print('LIM',l.get('checks_not_run'),'|',l.get('rea
 9. Bash: python -c "
import urllib.request,re
for u in ['https://jsr.io/@bbc/sqs-consumer@15.0.4']:
  r=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Ag
result: subtype=success turns=11 duration=65s
```

## Final answer
I ran both passes. For pass 2 I re-analysed the pass 1 evidence (`--bundle ./audit-precheck/evidence`) without crawling again, because 0 of the 25 crawled pages had status 200 and an empty `links.internal`.

## (1) Status and counts
- **audit_status:** `partial`
- **By severity:** critical 1 · high 2 · medium 19 · low 7 · info 0. That is 29 findings, 2 of them `blocked_by` another finding.
- **Not assessed:**
  - `reach.edge.bot_ua_blocked` and `reach.edge.bot_ua_challenged`. These are listed in `limitations[]` because `--probe-bot-ua` was not set.
  - `read.render.raw_text_gap`, `read.render.nav_links_js_only` and `act.perf.above_fold_weight`. These are listed as "not assessed" in `summary.suppressed_by_rule` because no browser render was done.
  - `extract.ans.fact_coverage_gap`, which is also "not assessed" there, for 4 pages.

## (2) Top 5 findings
| Rank | ID | Severity | Confidence | ICE | Title |
|---|---|---|---|---|---|
| 1 | F-001 | critical | confirmed | 9.3 | 2 content page(s) tell crawlers not to index them |
| 2 | F-002 | high | likely | 7.7 | fact_coverage 2/4: 2 claim(s) cannot be quoted from this page — on 18 of 25 crawled pages |
| 3 | F-003 | high | confirmed | 7.3 | 16 of 16 eligible page(s) carry no structured data at all |
| 4 | F-004 | medium | confirmed | 7.7 | The site does not clearly state who publishes it |
| 5 | F-005 | medium | confirmed | 7.7 | 10 page(s) of dated content carry no date at all |

## (3) Evidence check
- **F-001** (`reach.index.noindex_on_content`) is **supported**. I fetched `https://jsr.io/@bbc/sqs-consumer@15.0.4` with urllib. It returned status 200 with 172,684 bytes of HTML and the header `X-Robots-Tag: noindex`. It has 0 `<meta name="robots">` tags, which matches the evidence saying the noindex comes from the header. This was my first check, so I stopped there. No Playwright load was needed because this is a header check, not a raw-versus-rendered comparison.

## (4) Drill-down: F-001
- **Evidence:** "2 of 25 crawled pages carry a noindex directive: https://jsr.io/@bbc/sqs-consumer@15.0.4 via X-Robots-Tag header = "noindex" (page type article); https://jsr.io/@cfs/core@10.0.0-beta.545 via X-Robots-Tag header = "noindex" (page type article). A noindex page is fetched, read, and then discarded, so it can never be surfaced or cited."
- **Severity / confidence:** critical / confirmed
- **Mechanism:** "noindex instructs the crawler to drop the page after reading it, so every downstream signal on that page is wasted work."
- **Patch** (from `fix_patches/F-001.reach.index.noindex_on_content.txt`):
  ```
  Remove this line from the page head:
    <meta name="robots" content="noindex">
  and remove any X-Robots-Tag: noindex response header for these paths.
  ```
- **ICE components:** impact 10.0, confidence 9.0, ease 9.0, giving an ICE of 9.3 (effort: low).
- **Findings blocked by it:** 2 (F-009 and F-010, the "no direct answer" findings on these same two URLs).
- **Verification step:**
  ```
  curl -sI https://jsr.io/@bbc/sqs-consumer@15.0.4 | grep -i x-robots-tag  # expect no noindex
  curl -s https://jsr.io/@bbc/sqs-consumer@15.0.4 | grep -i 'name="robots"'
  ```

One thing to weigh before acting on F-001 (my comment only; the report is unchanged): both affected URLs are pages for a specific package version (`@15.0.4`, `@10.0.0-beta.545`). JSR may be marking these pages noindex on purpose so that search points to the latest version. If so, the finding is technically accurate but may not be a defect. Also, the meta-tag half of the patch doesn't apply here, because the page has no meta robots tag, only the header.

Everything is in `audit-output/`: `audit-report.json` and `report.md`.
