<!-- rehearsal: django_opus_final | url: https://docs.djangoproject.com/ | model: claude-opus-5-5 | harness: 2.1.281 (Claude Code) | python: Python 3.11.15 | playwright: yes | exit: 0 | seconds: 114 | report written: True -->
The audit of https://docs.djangoproject.com/ completed and wrote `audit-output/audit-report.json`. My spot checks back only one of the four confirmed high findings: F-001–F-003 are not supported on the live pages.

## 1. Status, counts and what wasn't assessed

**audit_status:** `complete` (24 findings, 0 blocked, run took 31.6 s)

| critical | high | medium | low | info |
|---|---|---|---|---|
| 0 | 4 | 17 | 3 | 0 |

**Not assessed:**
- **In `limitations[]`:** `reach.edge.bot_ua_blocked` and `reach.edge.bot_ua_challenged`. These need `--probe-bot-ua`, which is off by default and meant only for sites you own.
- **Also marked "not assessed" in `summary.suppressed_by_rule`:** `extract.ans.fact_coverage_gap`, 11 times.

## 2. Top 10 findings (report order)

| # | id | severity | confidence | ICE | title |
|---|---|---|---|---|---|
| 1 | F-001 | high | confirmed | 7.3 | The internal link graph only exists after JavaScript runs — on /el/1.11/_modules/django/contrib/messages/api |
| 2 | F-002 | high | confirmed | 7.3 | The internal link graph only exists after JavaScript runs — on /en/1.10/_modules/django/contrib/gis/geos/collections |
| 3 | F-003 | high | confirmed | 7.3 | The internal link graph only exists after JavaScript runs — on /en/3.2/_modules/django/contrib/messages/storage/cookie |
| 4 | F-004 | high | confirmed | 7.3 | 16 of 16 eligible page(s) carry no structured data at all |
| 5 | F-005 | medium | confirmed | 7.7 | The site does not clearly state who publishes it |
| 6 | F-006 | medium | confirmed | 7.7 | 14 page(s) of dated content carry no date at all |
| 7 | F-007 | medium | likely | 6.7 | 2 of 5 passages do not stand on their own |
| 8 | F-008 | medium | likely | 6.7 | Nothing near the top of the page states plainly what Django is — on /el/1.11/_modules/django/contrib/messages/api |
| 9 | F-009 | medium | likely | 6.7 | Nothing near the top of the page states plainly what Django is — on /el/1.11/misc/api-stability |
| 10 | F-010 | medium | likely | 6.7 | Nothing near the top of the page states plainly what Django is — on /el/2.0/_modules/django/contrib/messages/api |

## 3. Evidence check (the four confirmed highs)

For F-001–F-003 I fetched the raw HTML with urllib and loaded the same page in Playwright, counting only links to the same host.

- **F-001: not supported.** The engine says 34 links in the raw HTML and 72 after rendering. I counted 36 same-host links on both sides (94 links in total on both sides).
- **F-002: not supported.** The engine says 25 raw and 63 rendered. I counted 29 same-host links on both sides (87 in total on both sides).
- **F-003: not supported.** The engine says 29 raw and 67 rendered. I counted 30 same-host links on both sides (88 in total on both sides).
  - **Likely cause:** on F-001's page I recounted three ways (same host, any `*.djangoproject.com` host, `#` fragments) and raw and rendered matched every time: 39, 73 and 3. So the page adds no links through JavaScript. The engine's "72 rendered" is close to my 73 links to any `djangoproject.com` host. Its "34 raw" is close to the same-host count. The engine may count internal links differently on the raw side than on the rendered side.
- **F-004: supported.** In the raw HTML of `/` and `/contents/`, I found 0 `application/ld+json` blocks, 0 `itemscope`, 0 `itemtype` and 0 RDFa `typeof`/`vocab` attributes. I checked 2 of the 16 pages.

This is my commentary only. The report is unchanged.

## 4. Drill-down: F-004 (highest-ranked supported finding)

- **Evidence (verbatim):** "No JSON-LD, microdata or RDFa found on: article (10): https://docs.djangoproject.com/contents/, https://docs.djangoproject.com/el/1.11/misc/api-stability/, https://docs.djangoproject.com/el/2.0/misc/api-stability/; category (1): https://docs.djangoproject.com/en/1.10/_modules/django/contrib/gis/geos/collections/; docs (4): https://docs.djangoproject.com/el/1.11/_modules/django/contrib/messages/api/, https://docs.djangoproject.com/el/2.0/_modules/django/contrib/messages/api/, https://docs.djangoproject.com/el/2.1/_modules/django/contrib/messages/api/; home (1): https://docs.djangoproject.com/. Utility pages and pages under the 200-word floor were excluded from the eligible set and are not counted here."
- **Severity / confidence:** high / confirmed. Stage `extract`, affects 16 URLs.
- **Mechanism:** "Structured data states a fact in a typed form, so a consumer can extract it without having to infer it from prose it may parse differently."
- **Patch** (also written to `fix_patches/F-004.extract.sd.absent_on_eligible_page.txt`):
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
  - The `name` value is copied from the page title, so it repeats "Django documentation". It should be edited before pasting.
- **ICE:** 7.3 (impact 8, confidence 9, ease 5; effort medium).
- **Findings with `blocked_by` pointing at F-004:** 0.
- **Verification:** `curl -s https://docs.djangoproject.com/ | grep -c 'application/ld+json'  # expect at least 1`

I didn't create, change or delete any files myself. The orchestrator wrote everything in `./audit-output`.
