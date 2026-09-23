<!-- rehearsal: django_sonnet5 | url: https://docs.djangoproject.com/ | model: claude-sonnet-5 | harness: 2.1.281 (Claude Code) | python: Python 3.11.15 | playwright: yes | exit: 0 | seconds: 94 | report written: True -->
I ran the orchestrator with `--out ./audit-output` and it exited normally. I created no files myself; the engine wrote `audit-output/`.

## 1. Status and counts
- **audit_status:** `complete`
- **Findings:** 24 in total. There are 0 critical, 4 high, 17 medium, 3 low and 0 info. None are blocked, so `blocked_by` is empty on every finding.
- **Not assessed:** `reach.edge.bot_ua_blocked` and `reach.edge.bot_ua_challenged`. I did not pass `--probe-bot-ua`, so the CDN/WAF check on AI crawlers did not run. This is a blind spot, not a pass.

## 2. Top 10 findings, in report order

| Rank | ID | Severity | Confidence | ICE | Title |
|---|---|---|---|---|---|
| 1 | F-001 | high | confirmed | 7.3 | Internal link graph only exists after JavaScript runs (`/el/1.11/_modules/django/contrib/messages/api`) |
| 2 | F-002 | high | confirmed | 7.3 | Internal link graph only exists after JavaScript runs (`/en/1.10/_modules/django/contrib/gis/geos/collections`) |
| 3 | F-003 | high | confirmed | 7.3 | Internal link graph only exists after JavaScript runs (`/en/3.2/_modules/django/contrib/messages/storage/cookie`) |
| 4 | F-004 | high | confirmed | 7.3 | 16 of 16 eligible pages carry no structured data at all |
| 5 | F-005 | medium | confirmed | 7.7 | The site does not clearly state who publishes it |
| 6 | F-006 | medium | confirmed | 7.7 | 14 pages of dated content carry no date at all |
| 7 | F-007 | medium | likely | 6.7 | 2 of 5 passages do not stand on their own |
| 8 | F-008 | medium | likely | 6.7 | Nothing near the top of the page states plainly what Django is (`/el/1.11/_modules/django/contrib/messages/api`) |
| 9 | F-009 | medium | likely | 6.7 | Same title, on `/el/1.11/misc/api-stability` |
| 10 | F-010 | medium | likely | 6.7 | Same title, on `/el/2.0/_modules/django/contrib/messages/api` |

## 3. Evidence check
I checked F-001 to F-004, the four confirmed high findings. I used urllib for the raw HTML and Playwright for the rendered page.

- **F-001: not supported.** The engine claims 34 internal links raw versus 72 rendered. I saw 34 raw and 34 rendered. Total anchors were 94 raw and 94 rendered.
- **F-002: not supported.** The engine claims 25 raw versus 63 rendered. I saw 25 raw and 25 rendered, with 87 anchors in both.
- **F-003: not supported.** The engine claims 29 raw versus 67 rendered. I saw 29 raw and 29 rendered, with 88 anchors in both.
- **F-004: supported.**
  - The raw HTML of `/`, of `/en/1.10/_modules/django/contrib/gis/geos/collections/` and of `/el/1.11/_modules/django/contrib/messages/api/` has 0 `application/ld+json` blocks, 0 `itemscope`, 0 `itemtype` and 0 `typeof=`. I did not fetch the other 13 listed pages.
  - Playwright also found 0 JSON-LD blocks on the rendered `/`.

The raw count matches the engine's claimed "raw" number in all three cases. The rendered counts the engine reports are about 38 higher than the 34, 25 and 29 I saw. My check does not reproduce the JavaScript-only link claim. This is commentary only, and the report is unchanged.

## 4. Drill-down: F-004, the highest-ranked finding my check supported
- **Evidence:** No JSON-LD, microdata or RDFa on 16 eligible pages. That is 10 article pages, 1 category page, 4 docs pages and 1 home page, including `/`, `/contents/` and the `/el/…/misc/api-stability/` pages.
- **Severity and confidence:** high, confirmed.
- **Mechanism:** Structured data states a fact in a typed form. A consumer can then extract it without inferring it from prose that it may parse differently.
- **Paste-ready patch** (`fix_patches/F-004.extract.sd.absent_on_eligible_page.txt`):
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
- **ICE:** 7.3. Impact is 8.0, confidence 9.0 and ease 5.0. Effort is medium.
- **Blocked findings:** 0 findings have `blocked_by` pointing at F-004.
- **Verification step:** `curl -s https://docs.djangoproject.com/ | grep -c 'application/ld+json'  # expect at least 1`
