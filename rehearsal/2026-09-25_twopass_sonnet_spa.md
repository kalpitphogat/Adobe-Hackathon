<!-- rehearsal: twopass_sonnet_spa | site: 127.0.0.1:8603 JS-only test app | model: claude-sonnet-5 | harness: 2.1.282 (Claude Code) via claude -p | python: Python 3.11.15 | playwright: 1.56.0 (Chromium 141) | host: Linux container | prompt: two-pass, final | exit: 0 -->
<!-- engine check after the run:
added by the run      : 93 file(s): __pycache__, audit-output, audit-precheck
RESULT                : ENGINE UNCHANGED
-->

Test sites on 127.0.0.1 need --allow-private-hosts, so the prompt had one extra sentence after the URL: "(this is a test site on this machine: add --allow-private-hosts to both orchestrator runs)".

## Tool calls
```text
session init: model=claude-sonnet-5 tools=39 skills/commands seen=['ai-readiness-orchestrator', 'answerability-audit', 'crawl-access-audit', 'engagement-audit', 'render-gap-audit', 'structured-data-audit', 'trust-freshness-audit']
 1. Skill: ai-readiness-orchestrator
 2. Bash: ls skills/ai-readiness-orchestrator/scripts/ 2>&1 | head -20
 3. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8603/ --no-render --out ./audit-precheck --allow-private-hosts
 4. Bash: python -c "
import json
n=0
with open('audit-precheck/evidence/pages.jsonl') as f:
    for line in f:
        p = json.loads(line)
        if p.get('status') ==
 5. Bash: python skills/ai-readiness-orchestrator/scripts/orchestrate.py http://127.0.0.1:8603/ --out ./audit-output --allow-private-hosts
 6. Read: /tmp/claude-0/-home-user-Adobe-Hackathon/ef823eec-15e5-5f7f-aa17-448c5dab8088/scratchpad/reh/sonnet_spa/brand-ai-readiness-audit/audit-output/audit-report.json
 7. Bash: python -c "
import urllib.request
req = urllib.request.Request('http://127.0.0.1:8603/', headers={'User-Agent':'audit-check/1.0'})
html = urllib.request.urlopen
 8. Bash: python -c "
import urllib.request
req = urllib.request.Request('http://127.0.0.1:8603/', headers={'User-Agent':'audit-check/1.0'})
html = urllib.request.urlopen
result: subtype=success turns=10 duration=49s
```

## Final answer
**F-001 — supported.** Raw HTML has `<head>` with `charset`, `<title>`, `meta description`, but no `<meta name="viewport">` — 0 viewport tags found, matching the report's evidence exactly. (This is a raw-HTML-only check, not a render comparison, so Playwright wasn't required here.) I stopped after this first check since it was supported.

## 4. Drill-down: F-001 — No mobile viewport meta tag

- **Evidence:** No `<meta name="viewport">` on `http://127.0.0.1:8603/`. Confirmed by my own fetch — the raw `<head>` (228 bytes total) contains only `charset`, `title`, and `description` meta tags, nothing viewport-related.
- **Severity / confidence:** high / confirmed
- **Mechanism:** The viewport meta tag tells a mobile browser to lay out at device width; without it, the browser renders at desktop width and scales the whole page down, making text unreadably small and tap targets too small to hit.
- **Paste-ready patch:**
  ```html
  <meta name="viewport" content="width=device-width, initial-scale=1">
  ```
- **ICE components:** confidence 9.0, ease 9.0, impact 8.0 → **ICE 8.7**
- **Findings blocked by F-001:** 0 (no other finding lists `F-003` — checked: only `F-003` appears as a `blocked_by` value across the report; nothing points at F-001)
- **Verification step:** `curl -s http://127.0.0.1:8603/ | grep -i 'name="viewport"'`

**Note:** the report's engine findings are reproduced exactly as written above (section 2); this section 4 evidence check and commentary do not alter the report itself. The site's `<div id="root">` + `app.js` shell also visibly explains why F-004/F-005 (JS-only content and links) fired — the entire page body is client-rendered.
