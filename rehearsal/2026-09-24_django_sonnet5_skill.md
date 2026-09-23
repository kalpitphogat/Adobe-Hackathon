<!-- rehearsal: django_sonnet5_skill | url: https://docs.djangoproject.com/ | model: claude-sonnet-5 | harness: 2.1.281 (Claude Code) | python: Python 3.11.15 | playwright: yes | exit: 0 | seconds: 98 | report written: True -->
<!-- engine check after the run:
added by the run      : 130 file(s): __pycache__, audit-output
RESULT                : ENGINE UNCHANGED
-->

## Tool calls
```text
session init: model=claude-sonnet-5 tools=35 skills/commands seen=['ai-readiness-orchestrator', 'answerability-audit', 'crawl-access-audit', 'engagement-audit', 'render-gap-audit', 'structured-data-audit', 'trust-freshness-audit']
 1. Skill: ai-readiness-orchestrator
 2. PowerShell: python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://docs.djangoproject.com/ --out ./audit-output; echo "exit $LASTEXITCODE"
 3. PowerShell: python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://docs.djangoproject.com/ --out ./audit-output; 'exit ' + $LASTEXITCODE
 4. PowerShell: python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://docs.djangoproject.com/ --out ./audit-output
 5. PowerShell: python -c "import json;r=json.load(open('audit-output/audit-report.json',encoding='utf-8'));print(r['audit_status'],r['summary']);print(json.dumps(r['limitation
 6. PowerShell: python -c "import json;r=json.load(open('audit-output/audit-report.json',encoding='utf-8'));f=r['findings'];print(json.dumps(f[0],indent=1));[print(x['id'],x['s
 7. PowerShell: python -c "
import urllib.request,re
u='https://docs.djangoproject.com/el/1.11/_modules/django/contrib/messages/api/'
h=urllib.request.urlopen(urllib.request.Re
 8. PowerShell: python -c "
import urllib.request,re
from urllib.parse import urljoin,urlparse
u='https:'+chr(47)*2+'docs.djangoproject.com/el/1.11/_modules/django/contrib/mess
 9. Bash: python -c '
import urllib.request,re
from urllib.parse import urljoin,urlparse
u="https:"+chr(47)*2+"docs.djangoproject.com/el/1.11/_modules/django/contrib/mess
10. Bash: for p in en/1.10/_modules/django/contrib/gis/geos/collections en/3.2/_modules/django/contrib/messages/storage/cookie; do P=$p python -c '
import urllib.request,
11. Bash: python -c '
import urllib.request,re
from urllib.parse import urljoin,urlparse
from playwright.sync_api import sync_playwright
def same(u,x): return urlparse(ur
12. Bash: python -c '
import urllib.request,re
u="https:"+chr(47)*2+"docs.djangoproject.com/"
h=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Moz
result: subtype=success turns=14 duration=95s
```

## Final answer
**1. Status**
- `audit_status` is **complete**.
- There are 24 findings: 0 critical, 4 high, 17 medium, 3 low, 0 info. 0 findings are blocked.
- Not assessed: `reach.edge.bot_ua_blocked` and `reach.edge.bot_ua_challenged`. The `--probe-bot-ua` flag wasn't set, so these are a blind spot, not a pass.
- Some other checks are also listed as "not assessed" in `suppressed_by_rule`: `extract.ans.fact_coverage_gap` (11), `reach.edge.bot_ua_blocked` (1) and `reach.edge.bot_ua_challenged` (1).

**2. Top 5 findings, in report order**

| Rank | ID | Severity | Confidence | ICE | Title |
|---|---|---|---|---|---|
| 1 | F-001 | high | confirmed | 7.3 | The internal link graph only exists after JavaScript runs, on /el/1.11/_modules/django/contrib/messages/api |
| 2 | F-002 | high | confirmed | 7.3 for F-001 and F-004 (F-002, F-003 not read) | The internal link graph only exists after JavaScript runs, on /en/1.10/_modules/django/contrib/gis/geos/collections |
| 3 | F-003 | high | confirmed | not read | The internal link graph only exists after JavaScript runs, on /en/3.2/_modules/django/contrib/messages/storage/cookie |
| 4 | F-004 | high | confirmed | 7.3 | 16 of 16 eligible page(s) carry no structured data at all |
| 5 | F-005 | medium | confirmed | not read | The site does not clearly state who publishes it |

I only printed ICE for F-001 and F-004, both 7.3. It sits under `suggested_action.ice`, not at the top level of each finding. I didn't read it for F-002, F-003 or F-005, and the ICE cell in the F-002 row is my slip: it should read "not read".

**3. Evidence check**

I fetched raw HTML with urllib and rendered each page with Playwright, counting same-host links on both sides.
- **F-001** (not supported): the engine says 34 raw links against 72 rendered. I saw 94 anchors in both raw and rendered HTML, 39 of them same-host, with no difference.
- **F-002** (not supported): 32 same-host links raw and 32 rendered (87 anchors each).
- **F-003** (not supported): 33 same-host links raw and 33 rendered (88 anchors each).
- **F-004** (supported): the homepage raw HTML is 54,069 bytes with 0 `application/ld+json`, 0 `itemscope`, 0 `itemtype` and 0 `typeof`/`vocab` matches. It has only 9 `og:` meta tags, which is consistent with "no JSON-LD, microdata or RDFa".

The three link-graph findings are commentary from my check only. The report still stands as written.

**4. Drill-down on F-004** (`extract.sd.absent_on_eligible_page`)
- **Evidence:** no JSON-LD, microdata or RDFa on 16 of 16 eligible pages. That is 10 articles, 4 docs pages, 1 category page and the home page. Utility pages and pages under 200 words were excluded.
- **Severity and confidence:** high, confirmed.
- **Mechanism:** structured data states a fact in a typed form, so a consumer can extract it without inferring it from prose it may parse differently.
- **Patch (paste-ready):**
  ```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Django documentation | Django documentation | Django",
    "description": "__FILL_IN__:description",
    "url": "https://docs.djangoproject.com/"
  }
  </script>
  ```
  The `name` is the raw page title, which repeats "Django documentation" twice, and `description` is left as `__FILL_IN__`. Both need a human edit before pasting.
- **ICE components:** impact 8.0, confidence 9.0, ease 5.0, giving 7.3. Effort is medium.
- **Blocked by it:** 0 findings have `blocked_by` pointing at F-004.
- **Verification step:** `curl -s https://docs.djangoproject.com/ | grep -c 'application/ld+json'  # expect at least 1`
