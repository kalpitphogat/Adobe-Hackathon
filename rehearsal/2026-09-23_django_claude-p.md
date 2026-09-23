## Django docs audit (docs.djangoproject.com)

The audit ran and finished in 55.6s. It wrote `audit-output/audit-report.json`, `audit-output/report.md` and `audit-output/fix_patches/`. I didn't change anything under `skills/`. The optional `--probe-bot-ua` flag was left off, so the two bot-blocking checks are listed as "not assessed". That's a gap in coverage, not a pass.

### 1. Status and counts
- **audit_status:** `complete`
- **By severity:** critical 0 · high 4 · medium 17 · low 3 · info 0. That's 24 findings, none blocked by an upstream failure.

### 2. Top 10 by ICE (a priority score)

| id | severity | confidence | ICE | title |
|---|---|---|---|---|
| F-005 | medium | confirmed | 7.7 | The site does not clearly state who publishes it |
| F-006 | medium | confirmed | 7.7 | 14 page(s) of dated content carry no date at all |
| F-001 | high | confirmed | 7.3 | The internal link graph only exists after JavaScript runs — on /el/1.11/_modules/django/contrib/messages/api |
| F-002 | high | confirmed | 7.3 | The internal link graph only exists after JavaScript runs — on /en/1.10/_modules/django/contrib/gis/geos/collections |
| F-003 | high | confirmed | 7.3 | The internal link graph only exists after JavaScript runs — on /en/3.2/_modules/django/contrib/messages/storage/cookie |
| F-004 | high | confirmed | 7.3 | 16 of 16 eligible page(s) carry no structured data at all |
| F-022 | low | confirmed | 7.0 | The sitemap does not usefully describe the site |
| F-023 | low | confirmed | 7.0 | 10 article(s) name nobody as the author |
| F-024 | low | confirmed | 7.0 | A category page gives no indication of cost and no path to one |
| F-007 | medium | likely | 6.7 | 2 of 5 passages do not stand on their own |

### 3. The first three findings in report order
F-001, F-002 and F-003 are all the same check (`read.render.nav_links_js_only`), each rated **high** severity with **confirmed** confidence.

**Evidence (as written by the engine):**
- **F-001:** "https://docs.djangoproject.com/el/1.11/_modules/django/contrib/messages/api/: the raw HTML contains 34 internal links, the rendered DOM contains 72. A crawler that does not execute JavaScript has 38 fewer paths onward from this page, so pages reachable only through those links may never be discovered."
- **F-002:** the same wording for `/en/1.10/_modules/django/contrib/gis/geos/collections/`: 25 links in raw HTML against 63 rendered, so 38 fewer.
- **F-003:** the same wording for `/en/3.2/_modules/django/contrib/messages/storage/cookie/`: 29 links in raw HTML against 67 rendered, so 38 fewer.

**Suggested fix (identical for all three):** "Emit navigation and listing links as real <a href> elements in the initial HTML."
- Mechanism: "Crawl discovery follows anchors in the served HTML; a link that only exists after hydration is not a link the crawler can follow."
- Effort: medium. ICE 7.3 (impact 8, confidence 9, ease 5).
- Patch (`fix_patches/F-00N.read.render.nav_links_js_only.txt`):
  ```html
  <!-- Render navigation server-side. A router link must still emit an href: -->
  <a href="/products/widget">Widget</a>
  <!-- not: <div onclick="navigate(...)">Widget</div> -->
  ```
- Verification command: `curl -s <url> | grep -o 'href="/[^"]*"' | sort -u | wc -l`

### 4. Evidence check (my commentary; the report is unchanged)
I fetched each page's raw HTML with urllib and counted the `<a href>` tags.
- **F-001:** The raw HTML doesn't support the finding. It already has 94 plain `<a href>` links and no `onclick` handlers: 39 point to docs.djangoproject.com and 27 to www.djangoproject.com. That totals 66, close to the engine's "rendered" 72, which suggests the 38-link gap comes from counting only docs.djangoproject.com as internal in the raw HTML but including www.djangoproject.com after rendering, not from JavaScript adding links.
- **F-002:** Not supported either. The raw HTML has 87 plain anchors, 32 of them resolving to docs.djangoproject.com, which is already more than the engine's raw count of 25. The extra site-wide links (header, footer, www.djangoproject.com navigation) are present before any JavaScript runs.
- **F-003:** Not supported. The raw HTML has 88 plain anchors, 33 of them internal, and none are created by JavaScript. The gap is exactly 38 on all three pages, which fits one fixed set of shared template links being counted differently rather than content added at render time.

I didn't render the pages in a browser, so I can't show what the engine's renderer counted. However, nothing in the served HTML suggests JavaScript-only navigation, and none of these three findings looks like a real high-severity problem. The patch is also a generic template (`/products/widget`) rather than something built from this site's own pages.
