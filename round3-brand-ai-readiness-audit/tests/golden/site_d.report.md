# AI-readiness audit — spa-only.test

*Audited 2026-05-28T20:26:40Z · status: **partial***

## What to do first

**F-001 · HIGH** — The served HTML is an empty application shell with no content

- **Do:** Server-render or pre-render this route so the initial HTML response carries the content.
- **Why it works:** The mount point is empty in the served HTML, so every downstream signal - structured data, headings, facts - is absent at the moment the crawler reads the page.
- **Effort:** high · **ICE:** 5.3
- **Verify:** `curl -s https://spa-only.test/ | sed -e 's/<[^>]*>//g' | tr -s '[:space:]' ' ' | wc -w`

**F-002 · HIGH** — The served HTML is an empty application shell with no content

- **Do:** Server-render or pre-render this route so the initial HTML response carries the content.
- **Why it works:** The mount point is empty in the served HTML, so every downstream signal - structured data, headings, facts - is absent at the moment the crawler reads the page.
- **Effort:** high · **ICE:** 5.3
- **Verify:** `curl -s https://spa-only.test/about | sed -e 's/<[^>]*>//g' | tr -s '[:space:]' ' ' | wc -w`

**F-003 · HIGH** — The served HTML is an empty application shell with no content

- **Do:** Server-render or pre-render this route so the initial HTML response carries the content.
- **Why it works:** The mount point is empty in the served HTML, so every downstream signal - structured data, headings, facts - is absent at the moment the crawler reads the page.
- **Effort:** high · **ICE:** 5.3
- **Verify:** `curl -s https://spa-only.test/features | sed -e 's/<[^>]*>//g' | tr -s '[:space:]' ' ' | wc -w`

**F-004 · HIGH** — The served HTML is an empty application shell with no content

- **Do:** Server-render or pre-render this route so the initial HTML response carries the content.
- **Why it works:** The mount point is empty in the served HTML, so every downstream signal - structured data, headings, facts - is absent at the moment the crawler reads the page.
- **Effort:** high · **ICE:** 5.3
- **Verify:** `curl -s https://spa-only.test/pricing | sed -e 's/<[^>]*>//g' | tr -s '[:space:]' ' ' | wc -w`

**F-012 · LOW** — The sitemap does not usefully describe the site

- **Do:** Regenerate the sitemap from the live route list with real lastmod values.
- **Why it works:** Crawlers use lastmod to decide what to re-fetch; a constant or absent value gives them nothing to prioritise, so changed pages are refreshed no sooner than unchanged ones.
- **Effort:** low · **ICE:** 7.0
- **Verify:** `curl -s https://spa-only.test/sitemap.xml | grep -c '<loc>'`


## Summary

| Severity | Count |
|---|---|
| critical | 0 |
| high | 4 |
| medium | 7 |
| low | 5 |
| info | 0 |
| **total** | **16** |

Discoverability 16 · engagement 0.

## Fix these first — everything else is waiting on them

- 5 finding(s) are recorded but capped at medium because F-001 (The served HTML is an empty application shell with no content) blocks them. They become relevant the moment F-001 is fixed.
- 2 finding(s) are recorded but capped at medium because F-002 (The served HTML is an empty application shell with no content) blocks them. They become relevant the moment F-002 is fixed.
- 2 finding(s) are recorded but capped at medium because F-003 (The served HTML is an empty application shell with no content) blocks them. They become relevant the moment F-003 is fixed.
- 2 finding(s) are recorded but capped at medium because F-004 (The served HTML is an empty application shell with no content) blocks them. They become relevant the moment F-004 is fixed.

## Reach — can a crawler get in?

### F-012 · LOW · The sitemap does not usefully describe the site

*confidence: confirmed · check: `reach.sitemap.coverage_gap`*

**Evidence.** all 4 entries share 0 distinct lastmod value(s), so lastmod carries no information about what changed

**Fix.** Regenerate the sitemap from the live route list with real lastmod values.

**Why this works.** Crawlers use lastmod to decide what to re-fetch; a constant or absent value gives them nothing to prioritise, so changed pages are refreshed no sooner than unchanged ones.

**Verify**

```
curl -s https://spa-only.test/sitemap.xml | grep -c '<loc>'
```

*Source: sitemaps.org protocol 0.9*

## Read — can it read the page without running JavaScript?

### F-001 · HIGH · The served HTML is an empty application shell with no content

*confidence: likely · check: `read.render.empty_spa_shell`*

**Evidence.** https://spa-only.test/ serves 0 words of body text. The framework mount point div#__next contains 0 words, 3 JavaScript bundle(s) are loaded (/_next/static/chunks/webpack-0f1a2b3c.js, /_next/static/chunks/framework-4d5e6f70.js), and the <noscript> fallback carries 9 words. A crawler that does not execute JavaScript receives an empty page. No renderer was available, so this is reported at high/likely rather than critical/confirmed: we can see the shell signature but cannot measure what the visitor would have seen.

**Fix.** Server-render or pre-render this route so the initial HTML response carries the content.

**Why this works.** The mount point is empty in the served HTML, so every downstream signal - structured data, headings, facts - is absent at the moment the crawler reads the page.

**Patch**

```
# Enable SSR or static generation for this route.
# Minimum viable stopgap: put the page's key facts in the initial HTML.
<noscript>
  <h1>__FILL_IN__:page_h1</h1>
  <p>__FILL_IN__:one_paragraph_summary_of_this_page</p>
</noscript>
```

**Verify**

```
curl -s https://spa-only.test/ | sed -e 's/<[^>]*>//g' | tr -s '[:space:]' ' ' | wc -w
# currently about 0; expect the real content length
```

*Source: Handout appendix, How machines read a page*

### F-002 · HIGH · The served HTML is an empty application shell with no content

*confidence: likely · check: `read.render.empty_spa_shell`*

**Evidence.** https://spa-only.test/about serves 0 words of body text. The framework mount point div#__next contains 0 words, 3 JavaScript bundle(s) are loaded (/_next/static/chunks/webpack-0f1a2b3c.js, /_next/static/chunks/framework-4d5e6f70.js), and the <noscript> fallback carries 9 words. A crawler that does not execute JavaScript receives an empty page. No renderer was available, so this is reported at high/likely rather than critical/confirmed: we can see the shell signature but cannot measure what the visitor would have seen.

**Fix.** Server-render or pre-render this route so the initial HTML response carries the content.

**Why this works.** The mount point is empty in the served HTML, so every downstream signal - structured data, headings, facts - is absent at the moment the crawler reads the page.

**Patch**

```
# Enable SSR or static generation for this route.
# Minimum viable stopgap: put the page's key facts in the initial HTML.
<noscript>
  <h1>__FILL_IN__:page_h1</h1>
  <p>__FILL_IN__:one_paragraph_summary_of_this_page</p>
</noscript>
```

**Verify**

```
curl -s https://spa-only.test/about | sed -e 's/<[^>]*>//g' | tr -s '[:space:]' ' ' | wc -w
# currently about 0; expect the real content length
```

*Source: Handout appendix, How machines read a page*

### F-003 · HIGH · The served HTML is an empty application shell with no content

*confidence: likely · check: `read.render.empty_spa_shell`*

**Evidence.** https://spa-only.test/features serves 0 words of body text. The framework mount point div#__next contains 0 words, 3 JavaScript bundle(s) are loaded (/_next/static/chunks/webpack-0f1a2b3c.js, /_next/static/chunks/framework-4d5e6f70.js), and the <noscript> fallback carries 9 words. A crawler that does not execute JavaScript receives an empty page. No renderer was available, so this is reported at high/likely rather than critical/confirmed: we can see the shell signature but cannot measure what the visitor would have seen.

**Fix.** Server-render or pre-render this route so the initial HTML response carries the content.

**Why this works.** The mount point is empty in the served HTML, so every downstream signal - structured data, headings, facts - is absent at the moment the crawler reads the page.

**Patch**

```
# Enable SSR or static generation for this route.
# Minimum viable stopgap: put the page's key facts in the initial HTML.
<noscript>
  <h1>__FILL_IN__:page_h1</h1>
  <p>__FILL_IN__:one_paragraph_summary_of_this_page</p>
</noscript>
```

**Verify**

```
curl -s https://spa-only.test/features | sed -e 's/<[^>]*>//g' | tr -s '[:space:]' ' ' | wc -w
# currently about 0; expect the real content length
```

*Source: Handout appendix, How machines read a page*

### F-004 · HIGH · The served HTML is an empty application shell with no content

*confidence: likely · check: `read.render.empty_spa_shell`*

**Evidence.** https://spa-only.test/pricing serves 0 words of body text. The framework mount point div#__next contains 0 words, 3 JavaScript bundle(s) are loaded (/_next/static/chunks/webpack-0f1a2b3c.js, /_next/static/chunks/framework-4d5e6f70.js), and the <noscript> fallback carries 9 words. A crawler that does not execute JavaScript receives an empty page. No renderer was available, so this is reported at high/likely rather than critical/confirmed: we can see the shell signature but cannot measure what the visitor would have seen.

**Fix.** Server-render or pre-render this route so the initial HTML response carries the content.

**Why this works.** The mount point is empty in the served HTML, so every downstream signal - structured data, headings, facts - is absent at the moment the crawler reads the page.

**Patch**

```
# Enable SSR or static generation for this route.
# Minimum viable stopgap: put the page's key facts in the initial HTML.
<noscript>
  <h1>__FILL_IN__:page_h1</h1>
  <p>__FILL_IN__:one_paragraph_summary_of_this_page</p>
</noscript>
```

**Verify**

```
curl -s https://spa-only.test/pricing | sed -e 's/<[^>]*>//g' | tr -s '[:space:]' ' ' | wc -w
# currently about 0; expect the real content length
```

*Source: Handout appendix, How machines read a page*

<details>
<summary>11 finding(s) are moot until the blockers above are fixed</summary>

- **F-005** · medium · The page title is 'Vantage', which does not say what the page is about — blocked by F-001 (`extract.ans.title_not_entity_bearing`)
- **F-006** · medium · The page title is 'Vantage', which does not say what the page is about — blocked by F-002 (`extract.ans.title_not_entity_bearing`)
- **F-007** · medium · The page title is 'Vantage', which does not say what the page is about — blocked by F-003 (`extract.ans.title_not_entity_bearing`)
- **F-008** · medium · The page title is 'Vantage', which does not say what the page is about — blocked by F-004 (`extract.ans.title_not_entity_bearing`)
- **F-009** · medium · The site does not clearly state who publishes it — blocked by F-001 (`extract.sd.identity_graph_weak`)
- **F-010** · medium · The name 'Vantage' is ambiguous and nothing on the homepage distinguishes it — blocked by F-001 (`trust.entity.name_collision`)
- **F-011** · medium · Nothing connects this site to an independent record of the same entity — blocked by F-001 (`trust.entity.no_external_corroboration`)
- **F-013** · low · The heading outline does not divide this page usefully — blocked by F-001 (`extract.ans.heading_structure_unusable`)
- **F-014** · low · The heading outline does not divide this page usefully — blocked by F-002 (`extract.ans.heading_structure_unusable`)
- **F-015** · low · The heading outline does not divide this page usefully — blocked by F-003 (`extract.ans.heading_structure_unusable`)
- **F-016** · low · The heading outline does not divide this page usefully — blocked by F-004 (`extract.ans.heading_structure_unusable`)

</details>

## Worth doing even though nothing is broken

### P-001 · Publish a comparison page for the alternatives buyers already weigh you against

Comparison questions are among the most common commercial queries, and a brand that has not written its own comparison is described using someone else's. This is a gap in coverage rather than a defect on any page, which is why it appears here and not as a finding.

## What this audit could not assess

- **site** — Edge and CDN reachability for named AI crawlers was not assessed, because --probe-bot-ua was not set. This is the highest-value check in this marketplace: a CDN or WAF rule that returns 403 to OAI-SearchBot, PerplexityBot or Claude-SearchBot removes a brand from those assistants entirely, and leaves no trace in robots.txt or in what a human sees. If you own this site, re-run the orchestrator with the --probe-bot-ua flag:
    orchestrate.py <url> --out ./audit-output --probe-bot-ua
That sends ONE request per crawler, to the homepage only, with an auditor token appended to the user-agent string so it is identifiable in your logs. It is off by default because sending named-crawler user-agents to a site you do not own is not something an audit should do without being asked.
  - Checks not run: reach.edge.bot_ua_blocked, reach.edge.bot_ua_challenged
- **site** — Every one of the 4 crawled pages serves an unhydrated application shell, and no rendered DOM was captured for any of them, so the page a visitor actually sees was never observed. All engagement checks are suppressed site-wide rather than reported at reduced confidence, because there is no evidence to reduce. This includes the normally site-scoped act.trust.no_policy_or_contact_path, which would otherwise be evidenced from other pages: on this site there are no other pages either. Re-run with a renderer available to assess engagement.
  - Checks not run: act.blocker.content_gated_by_interaction, act.context.assumes_prior_context, act.context.no_onward_path, act.cta.absent_for_page_type, act.cta.ambiguous_primary_label, act.cta.competing_primaries, act.form.field_count_excessive, act.form.high_friction_required_fields …

## Deliberately not reported

Findings other tools would raise that we suppressed, and why:

- `act.context.assumes_prior_context` ×4 — suppressed entirely
- `act.context.no_onward_path` ×1 — suppressed entirely
- `act.cta.absent_for_page_type` ×2 — suppressed entirely
- `act.orient.no_value_proposition` ×2 — suppressed entirely
- `act.perf.above_fold_weight` ×1 — not assessed
- `act.trust.no_policy_or_contact_path` ×1 — suppressed entirely
- `extract.ans.fact_coverage_gap` ×4 — not assessed
- `extract.ans.no_evidence_markers` ×3 — suppressed by threshold
- `extract.sd.absent_on_eligible_page` ×4 — suppressed by design
- `reach.agent.llms_txt_absent` ×1 — suppressed by design
- `reach.edge.bot_ua_blocked` ×1 — not assessed
- `reach.edge.bot_ua_challenged` ×1 — not assessed
- `read.render.nav_links_js_only` ×1 — not assessed
- `read.render.raw_text_gap` ×1 — not assessed
- `trust.authorship.unattributed` ×1 — suppressed by design

---

*brand-ai-readiness-audit 1.0.0 · 7 of 61 checks ran · AI crawler list snapshot 2026-09-09 (commit 0e111dcc24cb) · recommend-only: nothing was written to the audited site.*
