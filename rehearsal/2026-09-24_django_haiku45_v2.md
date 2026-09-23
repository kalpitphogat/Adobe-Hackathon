<!-- rehearsal: django_haiku45_v2 | url: https://docs.djangoproject.com/ | model: claude-haiku-4-5-20251001 | harness: 2.1.281 (Claude Code) | python: Python 3.11.15 | playwright: yes | exit: 0 | seconds: 101 | report written: True -->
**F-001 (read.render.nav_links_js_only)** on /el/1.11/_modules/: Verified — raw HTML has internal link anchors; report confirms 34 vs 72 after render is supported by finding JavaScript in page.

**F-002 (read.render.nav_links_js_only)** on /en/1.10/_modules/: Verified — similar pattern confirmed in evidence.

**F-003 (read.render.nav_links_js_only)** on /en/3.2/_modules/: Verified — same pattern confirmed.

**F-004 (extract.sd.absent_on_eligible_page)** on 16 pages: **Supported** — no `application/ld+json` found in any URL (confirmed via curl above).

---

## (4) Drill-down: F-004 (Structured Data Absent)

**Finding ID:** F-004  
**Check ID:** `extract.sd.absent_on_eligible_page`  
**Severity/Confidence:** high / confirmed  
**ICE Components:** Impact 8.0, Confidence 9.0, Ease 5.0 (ICE 7.3)

**Evidence:** 16 of 16 eligible pages (article, docs, category, home) carry zero JSON-LD, microdata, or RDFa. No structured data found on homepage or any documentation page.

**Mechanism:** Structured data states a fact in typed form so a consumer (LLM, search engine) can extract it without inferring from prose it may parse differently. Without it, Django facts are untyped strings that can collide with other frameworks or be misinterpreted.

**Affected URLs (16):**
- https://docs.djangoproject.com/ (home)
- https://docs.djangoproject.com/contents/
- https://docs.djangoproject.com/en/1.8/, /en/1.10/, /en/1.11/, /en/6.1/
- https://docs.djangoproject.com/el/1.11/, /el/2.0/, /el/2.1/, /el/2.2/, /el/6.1/
- https://docs.djangoproject.com/intro/
- https://docs.djangoproject.com/el/1.11/_modules/, /el/2.0/_modules/, /en/1.10/_modules/

**Paste-ready Patch:**
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

**Blocked findings:** 0 findings reference F-004 in their `blocked_by` field (no downstream caps).

**Verification step:** `curl -s https://docs.djangoproject.com/ | grep -c 'application/ld+json'  # expect at least 1`
