I ran the audit on https://docs.djangoproject.com/ with `--out ./audit-output`. It exited cleanly in about 37 seconds and I didn't change anything under `skills/`. My own check found that the three findings reported first are likely false positives. I haven't changed the report; the details are in section 4.

## 1. Status and counts by severity
- **audit_status:** `complete`
- **By severity:** critical 0 · high 4 · medium 17 · low 3 · info 0. That's 24 findings in total, and none are blocked by an upstream failure.
- **Limitation:** the checks for whether the site's CDN or firewall blocks AI crawlers were not assessed, because `--probe-bot-ua` was off.

## 2. Top 10 findings by suggested_action.ice (highest first)
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

Findings F-007 to F-019 all score 6.7. I kept report order for that tie, so F-007 takes the tenth place.

## 3. The first three findings in report order
All three have the same check (`read.render.nav_links_js_only`), severity, fix and patch.

**F-001: high, confirmed**
- **Evidence:** "https://docs.djangoproject.com/el/1.11/_modules/django/contrib/messages/api/: the raw HTML contains 34 internal links, the rendered DOM contains 72. A crawler that does not execute JavaScript has 38 fewer paths onward from this page, so pages reachable only through those links may never be discovered."

**F-002: high, confirmed**
- **Evidence:** "https://docs.djangoproject.com/en/1.10/_modules/django/contrib/gis/geos/collections/: the raw HTML contains 25 internal links, the rendered DOM contains 63. A crawler that does not execute JavaScript has 38 fewer paths onward from this page, …" (the rest is the same as F-001)

**F-003: high, confirmed**
- **Evidence:** "https://docs.djangoproject.com/en/3.2/_modules/django/contrib/messages/storage/cookie/: the raw HTML contains 29 internal links, the rendered DOM contains 67. A crawler that does not execute JavaScript has 38 fewer paths onward from this page, …" (the rest is the same as F-001)

**Suggested fix (all three):** "Emit navigation and listing links as real <a href> elements in the initial HTML." Effort is medium; ICE is 7.3 (impact 8, confidence 9, ease 5). The stated reason is: "Crawl discovery follows anchors in the served HTML; a link that only exists after hydration is not a link the crawler can follow."

**Patch** (written to `fix_patches/F-00N.read.render.nav_links_js_only.txt`):
```html
<!-- Render navigation server-side. A router link must still emit an href: -->
<a href="/products/widget">Widget</a>
<!-- not: <div onclick="navigate(...)">Widget</div> -->
```
The report's check for each fix is a `curl … | grep -o 'href="/[^"]*"' | sort -u | wc -l` against the affected URL.

## 4. Evidence check (my commentary; the report is unchanged)
I fetched each page with a plain Python `urllib` request, which doesn't run JavaScript, and counted `<a href>` tags.

| URL | links to docs.djangoproject.com | links to any *.djangoproject.com | engine: raw → rendered |
|---|---|---|---|
| el/1.11 …/messages/api/ | 39 | **73** | 34 → 72 |
| en/1.10 …/geos/collections/ | 32 | **66** | 25 → 63 |
| en/3.2 …/storage/cookie/ | 33 | **67** | 29 → 67 |

- **F-001:** Not supported. The served HTML already has 73 links to djangoproject.com, roughly the engine's "rendered" count of 72, and there are no `onclick` handlers.
- **F-002:** Not supported. The served HTML already has 66 djangoproject.com links against the engine's rendered count of 63, so the 38 "missing" links are not added by JavaScript.
- **F-003:** Not supported. The served HTML has 67 djangoproject.com links, exactly the engine's rendered count, so nothing is hidden from a crawler that doesn't run JavaScript.

The gap is the same 38 links on all three pages. That suggests the engine counted only docs.djangoproject.com links in the raw HTML but also counted the shared header and footer links to www.djangoproject.com in the rendered page. I haven't confirmed that in the engine's code. On these three pages the links are plain server-rendered HTML, so the engine's "confirmed" high severity looks overstated.

Files are in `./audit-output`:
- `audit-report.json`
- `report.md`
- `fix_patches/`
