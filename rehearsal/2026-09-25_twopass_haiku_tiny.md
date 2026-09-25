<!-- rehearsal: twopass_haiku_tiny | site: 127.0.0.1:8601 tiny test page | model: claude-haiku-4-5-20251001 | harness: 2.1.282 (Claude Code) via claude -p | python: Python 3.11.15 | playwright: 1.56.0 (Chromium 141) | host: Linux container | prompt: two-pass, final | exit: 0 -->
<!-- engine check after the run:
added by the run      : 84 file(s): __pycache__, audit-output, audit-precheck
RESULT                : ENGINE UNCHANGED
-->

Test sites on 127.0.0.1 need --allow-private-hosts, so the prompt had one extra sentence after the URL: "(this is a test site on this machine: add --allow-private-hosts to both orchestrator runs)".

## Tool calls
```text
session init: model=claude-haiku-4-5-20251001 tools=43 skills/commands seen=['ai-readiness-orchestrator', 'answerability-audit', 'crawl-access-audit', 'engagement-audit', 'render-gap-audit', 'structured-data-audit', 'trust-freshness-audit']
 1. Read: /tmp/claude-0/-home-user-Adobe-Hackathon/ef823eec-15e5-5f7f-aa17-448c5dab8088/scratchpad/reh/haiku_tiny/brand-ai-readiness-audit/skills/ai-readiness-orchestrato
 2. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8601/ --no-render --out ./audit-precheck --allow-private-hosts
 3. Bash: python -c "
import json
count = 0
with open('audit-precheck/evidence/pages.jsonl') as f:
    for line in f:
        page = json.loads(line)
        if page.get(
 4. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8601/ --bundle ./audit-precheck/evidence --out ./audit-output --allow-private-ho
 5. Read: /tmp/claude-0/-home-user-Adobe-Hackathon/ef823eec-15e5-5f7f-aa17-448c5dab8088/scratchpad/reh/haiku_tiny/brand-ai-readiness-audit/audit-output/audit-report.json
 6. Bash: python -c "
import urllib.request
import re

url = 'http://127.0.0.1:8601/'
try:
    with urllib.request.urlopen(url) as response:
        html = response.read(
 7. Bash: python -c "
import urllib.request
import re

url = 'http://127.0.0.1:8601/'
try:
    with urllib.request.urlopen(url) as response:
        html = response.read(
 8. Bash: python -c "
import urllib.request

url = 'http://127.0.0.1:8601/'
try:
    with urllib.request.urlopen(url) as response:
        print(f'Scheme: http, Status: {
 9. Bash: python -c "
import urllib.request
import re

url = 'http://127.0.0.1:8601/about.html'
try:
    with urllib.request.urlopen(url) as response:
        html = resp
10. Bash: python << 'EOF'
import urllib.request
import re

url = 'http://127.0.0.1:8601/about.html'
try:
    with urllib.request.urlopen(url) as response:
        html = 
result: subtype=success turns=11 duration=60s
```

## Final answer
**Pass 2 executed**: Re-analyzed same evidence without crawling (no pages with status 200 and empty internal links found).

## Audit Summary

**(1) Audit Status & Severity Counts:**
- **audit_status**: partial
- **High**: 4, **Medium**: 7, **Critical/Low/Info**: 0
- **Checks not assessed**: reach.edge.bot_ua_blocked, reach.edge.bot_ua_challenged (requires --probe-bot-ua)

**(2) Top 5 Findings (by report order):**

| Rank | ID | Severity | Confidence | ICE | Title |
|------|----|----|---|-----|-------|
| 1 | F-001 | High | Confirmed | 8.7 | 3 page(s) declare no mobile viewport |
| 2 | F-002 | High | Likely | 7.7 | fact_coverage 0/2: 2 claim(s) cannot be quoted from /about.html |
| 3 | F-003 | High | Likely | 7.7 | fact_coverage 0/2: 2 claim(s) cannot be quoted from /contact.html |
| 4 | F-004 | High | Confirmed | 7.3 | Transport security problems affect how crawlers and browsers treat the site |
| 5 | F-005 | Medium | Confirmed | 7.7 | The page title is 'Harbor Tools', which does not say what the page is about |

**(3) Evidence Check:**
- **F-001**: No viewport meta tag found in HTML — **supported**
- **F-004**: Site served over plain http, Status 200 — **supported**
- **F-002**: /about.html has 13 total words (6 main content), title "About Harbor Tools", meta description repeats name — **supported** (thin content and generic title prevent claim extraction)

**(4) Drill-Down on F-001 (Mobile Viewport):**

**Evidence**: No `<meta name="viewport">` on homepage, /about.html, /contact.html

**Severity/Confidence**: High/Confirmed

**Mechanism**: Mobile browsers without viewport meta tag emulate desktop width and scale down the entire page, rendering body text unreadable and tap targets unusable.

**Patch**: `<meta name="viewport" content="width=device-width, initial-scale=1">`

**ICE Components**: Confidence 9.0, Ease 9.0, Impact 8.0 (ICE 8.7)

**Verification**: `curl -s http://127.0.0.1:8601/ | grep -i 'name="viewport"'`

**Blocking other findings**: 0 (not a root blocker; gated check suppressions are unrelated)
