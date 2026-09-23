<!-- rehearsal: django_sonnet5_final | url: https://docs.djangoproject.com/ | model: claude-sonnet-5 | harness: 2.1.281 (Claude Code) | python: Python 3.11.15 | playwright: yes | exit: 0 | seconds: 111 | report written: True -->
<!-- engine check after the run:
added by the run      : 130 file(s): __pycache__, audit-output
RESULT                : ENGINE UNCHANGED
-->
session init: model=claude-sonnet-5 tools=35 skills/commands seen=['ai-readiness-orchestrator', 'answerability-audit', 'crawl-access-audit', 'engagement-audit', 'render-gap-audit', 'structured-data-audit', 'trust-freshness-audit']
 1. Skill: ai-readiness-orchestrator
 2. Bash: cd C:/Users/kalpi/Kalpit_round_4/runs/rehearse_django_sonnet5_final/brand-ai-readiness-audit && python skills/ai-readiness-orchestrator/scripts/orchestrate.py h
 3. Bash: cd C:/Users/kalpi/Kalpit_round_4/runs/rehearse_django_sonnet5_final/brand-ai-readiness-audit && python -c "
import json
r=json.load(open('audit-output/audit-rep
 4. Bash: cd C:/Users/kalpi/Kalpit_round_4/runs/rehearse_django_sonnet5_final/brand-ai-readiness-audit && python -c "
import json
r=json.load(open('audit-output/audit-rep
 5. Bash: cd /tmp 2>/dev/null; cat > /tmp/c.py <<'E'
import urllib.request,re
from urllib.parse import urljoin,urlparse
from html.parser import HTMLParser
u="https://docs
 6. PowerShell: python -c "
import urllib.request
from urllib.parse import urljoin,urlparse
from html.parser import HTMLParser
u='https://docs.djangoproject.com/el/1.11/_module
 7. PowerShell: python -c "
import urllib.request as R,re
from urllib.parse import urljoin as J,urlparse as U
u='https://docs.djangoproject.com/el/1.11/_modules/django/contrib/
 8. Bash: python -c '
import urllib.request as R,re
from urllib.parse import urljoin as J,urlparse as U
u="https://docs.djangoproject.com/el/1.11/_modules/django/contrib/
 9. Bash: for u in "https://docs.djangoproject.com/en/1.10/_modules/django/contrib/gis/geos/collections/" "https://docs.djangoproject.com/en/3.2/_modules/django/contrib/m
10. Bash: python -c '
import urllib.request as R,re
from urllib.parse import urljoin as J,urlparse as U
u="https://docs.djangoproject.com/en/1.10/_modules/django/contrib/
11. Bash: python -c '
import urllib.request as R,re
from urllib.parse import urljoin as J,urlparse as U
u="https://docs.djangoproject.com/en/3.2/_modules/django/contrib/m
12. Bash: python -c '
import urllib.request as R,re
for u in ["https://docs.djangoproject.com/","https://docs.djangoproject.com/contents/","https://docs.djangoproject.com
13. Bash: python -c '
import json
r=json.load(open("audit-output/audit-report.json",encoding="utf-8"))
f=r["findings"][3];print(json.dumps(f,indent=1)[:4500])
print(sum(1
result: subtype=success turns=15 duration=108s

----- final answer -----
**(1) Status**
- `audit_status`: **complete**
- Findings: 24 in total. Critical 0, high 4, medium 17, low 3, info 0. No finding is blocked.
- Not assessed: `reach.edge.bot_ua_blocked` and `reach.edge.bot_ua_challenged`. `--probe-bot-ua` wasn't set, so the WAF/CDN check for AI crawlers didn't run.
- Suppressed checks (recorded in `summary.suppressed_by_rule`): `extract.ans.fact_coverage_gap` (11) was not assessed. `reach.agent.llms_txt_absent` (1) was not applicable. The rest were suppressed by design or by threshold.

**(2) Top 5 in report order**

| Rank | ID | Severity | Confidence | ICE | Title |
|---|---|---|---|---|---|
| 1 | F-001 | high | confirmed | 7.3 | Internal link graph only exists after JavaScript runs, on /el/1.11/_modules/django/contrib/messages/api |
| 2 | F-002 | high | confirmed | 7.3 | Internal link graph only exists after JavaScript runs, on /en/1.10/_modules/django/contrib/gis/geos/collections |
| 3 | F-003 | high | confirmed | 7.3 | Internal link graph only exists after JavaScript runs, on /en/3.2/_modules/django/contrib/messages/storage/cookie |
| 4 | F-004 | high | confirmed | 7.3 | 16 of 16 eligible page(s) carry no structured data at all |
| 5 | F-005 | medium | confirmed | 7.7 | The site does not clearly state who publishes it |

**(3) Evidence check** (commentary only; the report is unchanged). I checked the confirmed high findings in report order and stopped at the first one my check supported.
- **F-001: not supported.** The engine says the raw HTML has 34 internal links and the rendered DOM has 72. I counted same-host `<a href>` links on the page. Raw HTML (urllib) gave 39, and the rendered page (Playwright) also gave 39. Unique links were 35 on both sides.
- **F-002: not supported.** The engine says 25 raw and 63 rendered. I counted 32 raw and 32 rendered (26 unique on both sides).
- **F-003: not supported.** The engine says 29 raw and 67 rendered. I counted 33 raw and 33 rendered (30 unique on both sides).
- **F-004: supported.** I fetched three of the affected pages: `/`, `/contents/` and `/el/1.11/misc/api-stability/`. Each had 0 `application/ld+json`, 0 `itemscope`, 0 `itemtype` and 0 `typeof=` matches. Each did have 9 `og:` meta tags. This matches the finding, since OpenGraph isn't JSON-LD, microdata or RDFa. It doesn't involve a raw-versus-rendered comparison, so no Playwright run was needed for it.

**(4) Drill-down: F-004** (`extract.sd.absent_on_eligible_page`)
- **Evidence:** No JSON-LD, microdata or RDFa was found on 16 eligible pages, out of 16 that were eligible. By page type: 10 article, 4 docs, 1 category and 1 home. Utility pages and pages under 200 words are excluded from the count.
- **Severity and confidence:** high, confirmed.
- **Mechanism:** Structured data states a fact in a typed form. A consumer can then extract it without inferring it from prose it may parse differently.
- **Patch (paste-ready, from `fix_patches/F-004.extract.sd.absent_on_eligible_page.txt`):**
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
  The `name` value is copied from the page title as the engine wrote it. `description` is left as `__FILL_IN__`.
- **ICE:** 7.3, made up of confidence 9.0, ease 5.0 and impact 8.0. Effort is medium.
- **Blocked findings:** 0 findings have `blocked_by` pointing at F-004.
- **Verification:** `curl -s https://docs.djangoproject.com/ | grep -c 'application/ld+json'  # expect at least 1`
