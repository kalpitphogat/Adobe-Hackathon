# AI-readiness audit — www.npr.org

*Audited 2026-09-26T20:18:51Z · status: **partial***

*Evidence basis: **25 page(s) fetched**, 0 rendered. Every finding below applies only to the URLs it lists. Pages this crawl did not fetch were not assessed — absence of a finding for a page is not a pass for it.*

## What to do first

**F-001 · CRITICAL** — robots.txt blocks 5 AI retrieval crawler(s) that cite sources at answer time

- **Do:** Allow ChatGPT-User, Claude-SearchBot, Claude-User, OAI-SearchBot, PerplexityBot in robots.txt, keeping any training-bot policy separate.
- **Why it works:** Retrieval crawlers fetch the page at the moment a user asks a question; if they are refused, the brand cannot appear as a source no matter how good the page is.
- **Effort:** low · **ICE:** 9.3
- **Verify:** `curl -s https://www.npr.org/robots.txt and confirm each of ChatGPT-User, Claude-SearchBot, Claude-User, OAI-SearchBot, PerplexityBot has an Allow rule that is at least as specific as any Disallow`

**F-002 · HIGH** — The first screen never says who this is for or what it does

- **Do:** Open with one sentence naming the audience and the outcome.
- **Why it works:** A visitor decides whether to stay from the first screen; without a sentence that names them, they have to do the work of inferring relevance, and most leave instead.
- **Effort:** low · **ICE:** 7.7
- **Verify:** `Open https://www.npr.org/ and read only the first screen: can a stranger say who it is for and what it does?`

**F-007 · MEDIUM** — robots.txt blocks 3 crawler(s) whose role is contested

- **Do:** Decide deliberately whether the AI-surface exposure Applebot-Extended, FacebookBot, Google-Extended controls is wanted.
- **Why it works:** These tokens modify how already-crawled content may be used on AI surfaces rather than whether the page can be fetched, so the cost is exposure, not access.
- **Effort:** low · **ICE:** 6.7
- **Verify:** `No mechanical check; this is a policy decision to record, not a defect to fix.`

**F-039 · MEDIUM** — 1 passage(s) assume context a first-time visitor does not have — on /about-npr/178660742/public-radio-finances

- **Do:** Rewrite these passages so they stand on their own for a first-time reader.
- **Why it works:** A reference to state the visitor does not hold cannot be resolved, so the sentence carries no information and signals the page was not meant for them.
- **Effort:** low · **ICE:** 6.7
- **Verify:** `Read each passage cold, as a stranger: does it depend on something you were never told?`

**F-040 · MEDIUM** — 3 passage(s) assume context a first-time visitor does not have — on /about-npr/179876898/terms-of-use

- **Do:** Rewrite these passages so they stand on their own for a first-time reader.
- **Why it works:** A reference to state the visitor does not hold cannot be resolved, so the sentence carries no information and signals the page was not meant for them.
- **Effort:** low · **ICE:** 6.7
- **Verify:** `Read each passage cold, as a stranger: does it depend on something you were never told?`


## Summary

| Severity | Count |
|---|---|
| critical | 1 |
| high | 1 |
| medium | 41 |
| low | 4 |
| info | 1 |
| **total** | **48** |

Discoverability 42 · engagement 6.

## Fix these first — everything else is waiting on them

- 38 finding(s) are recorded but capped at medium because F-001 (robots.txt blocks 5 AI retrieval crawler(s) that cite sources at answer time) blocks them. They become relevant the moment F-001 is fixed.

## Reach — can a crawler get in?

### F-001 · CRITICAL · robots.txt blocks 5 AI retrieval crawler(s) that cite sources at answer time

*confidence: confirmed · check: `reach.robots.ai_search_bot_blocked`*

**Evidence.** ChatGPT-User blocked by "Disallow: /" (line 47); Claude-SearchBot blocked by "Disallow: /" (line 74); Claude-User blocked by "Disallow: /" (line 77); OAI-SearchBot blocked by "Disallow: /" (line 54); PerplexityBot blocked by "Disallow: /" (line 98). Each of these fetches pages at answer time to ground or cite a response, so blocking them removes this brand from those assistants' answers entirely. 25 of 25 discovered paths are disallowed for these agents. Bot classification from a snapshot dated 2026-09-09 (upstream commit 0e111dcc24cb). 8 training-only bot(s) are also blocked, which is a separate and legitimate licensing choice.

**Fix.** Allow ChatGPT-User, Claude-SearchBot, Claude-User, OAI-SearchBot, PerplexityBot in robots.txt, keeping any training-bot policy separate.

**Why this works.** Retrieval crawlers fetch the page at the moment a user asks a question; if they are refused, the brand cannot appear as a source no matter how good the page is.

**Patch**

```
User-agent: ChatGPT-User
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: Claude-User
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

```

**Verify**

```
curl -s https://www.npr.org/robots.txt and confirm each of ChatGPT-User, Claude-SearchBot, Claude-User, OAI-SearchBot, PerplexityBot has an Allow rule that is at least as specific as any Disallow
```

*Source: RFC 9309 section 2.2.2; vendor crawler documentation per references/ai-bots.json*

### F-007 · MEDIUM · robots.txt blocks 3 crawler(s) whose role is contested

*confidence: likely · check: `reach.robots.dual_purpose_bot_blocked`*

**Evidence.** Blocked: Applebot-Extended, FacebookBot, Google-Extended. These are genuinely contested rather than clearly training-only or clearly retrieval. Contested. Controls use of Applebot-crawled content for training Apple foundation models while leaving Applebot search indexing in place. Blocking is a licensing decision, not a visibility defect. Contested. Historically a link-preview crawler, also cited in AI-training contexts. Contested. Google documents this token as controlling whether content helps improve Gemini apps and grounded answers. It is not a crawler in its own right - it modifies how Googlebot-crawled content may be used - so blocking it does not remove the site from Google Search, but it can affect AI-surface grounding. Report as a trade-off the site may have chosen deliberately, never as an error. We report this as a trade-off the site may have chosen deliberately, not as an error. Snapshot 2026-09-09 (upstream commit 0e111dcc24cb).

**Fix.** Decide deliberately whether the AI-surface exposure Applebot-Extended, FacebookBot, Google-Extended controls is wanted.

**Why this works.** These tokens modify how already-crawled content may be used on AI surfaces rather than whether the page can be fetched, so the cost is exposure, not access.

**Verify**

```
No mechanical check; this is a policy decision to record, not a defect to fix.
```

*Source: references/bot-taxonomy.md*

### F-044 · LOW · The sitemap does not usefully describe the site

*confidence: confirmed · check: `reach.sitemap.coverage_gap`*

**Evidence.** 13 of 25 crawled pages (52%) are not listed, for example https://www.npr.org/, https://www.npr.org/2021/01/11/955692434/procrastination-is-more-than-putting-things-off-heres-how-to-kick-the-habit, https://www.npr.org/2022/07/11/1110926267/digital-minimalism-can-help-find-balance; all 160 entries share 0 distinct lastmod value(s), so lastmod carries no information about what changed

**Fix.** Regenerate the sitemap from the live route list with real lastmod values.

**Why this works.** Crawlers use lastmod to decide what to re-fetch; a constant or absent value gives them nothing to prioritise, so changed pages are refreshed no sooner than unchanged ones.

**Patch**

```
  <url><loc>https://www.npr.org/</loc></url>
  <url><loc>https://www.npr.org/2021/01/11/955692434/procrastination-is-more-than-putting-things-off-heres-how-to-kick-the-habit</loc></url>
  <url><loc>https://www.npr.org/2022/07/11/1110926267/digital-minimalism-can-help-find-balance</loc></url>
  <url><loc>https://www.npr.org/2022/12/09/1141872654/build-a-healthy-relationship-with-your-in-laws</loc></url>
  <url><loc>https://www.npr.org/about-npr/1136563345/accessibility</loc></url>
```

**Verify**

```
curl -s https://www.npr.org/sitemap.xml | grep -c '<loc>'
```

*Source: sitemaps.org protocol 0.9*

### F-048 · INFO · robots.txt blocks 8 training-only crawler(s) — recorded as an observation, not a defect

*confidence: confirmed · check: `reach.robots.ai_training_bot_blocked`*

**Evidence.** Blocked: Bytespider, CCBot, ClaudeBot, Diffbot, GPTBot, Omgilibot, anthropic-ai, cohere-ai. These collect content for model training corpora, not for answering questions at retrieval time. Blocking them does not reduce whether this brand is found or cited by AI assistants. Retrieval crawlers are separately blocked and are reported above as the real problem. Classification from a snapshot dated 2026-09-09 (upstream commit 0e111dcc24cb).

**Fix.** No change required. This is a content-licensing decision, and we report it only so it is visible.

**Why this works.** Training-corpus collection and answer-time retrieval are separate pipelines with separate user-agent tokens; blocking the former does not affect the latter.

**Verify**

```
No action to verify. Revisit only if the site's licensing stance changes.
```

*Source: references/bot-taxonomy.md*

## Act — does a visitor who arrives stay and act?

### F-002 · HIGH · The first screen never says who this is for or what it does

*confidence: likely · check: `act.orient.no_value_proposition`*

**Evidence.** https://www.npr.org/ (page type home). H1 is '(none)'. The first 400 characters of observed content read: "NPR - Breaking News, Analysis, Music, Arts & Podcasts Top stories in the U.S." | "and world news, politics, health, science, business, music, arts and culture." | "Nonprofit journalism with a mission.". None of these names an audience or an outcome - no phrase of the form "for <who>", "helps <who> <do what>", or "<product> is a <category>" appears. A first-time visitor has to infer what this is.

**Fix.** Open with one sentence naming the audience and the outcome.

**Why this works.** A visitor decides whether to stay from the first screen; without a sentence that names them, they have to do the work of inferring relevance, and most leave instead.

**Patch**

```
<h1>__FILL_IN__:what_this_page_is</h1>
<p>__FILL_IN__:product_name is __FILL_IN__:category for __FILL_IN__:audience. It __FILL_IN__:primary_outcome.</p>
```

**Verify**

```
Open https://www.npr.org/ and read only the first screen: can a stranger say who it is for and what it does?
```

*Source: references/cro-frameworks.md*

### F-039 · MEDIUM · 1 passage(s) assume context a first-time visitor does not have — on /about-npr/178660742/public-radio-finances

*confidence: likely · check: `act.context.assumes_prior_context`*

**Evidence.** https://www.npr.org/about-npr/178660742/public-radio-finances: "That is the promise of a free press in a democracy." (opens with the unresolved reference 'That'). Most visitors arrive on a deep page from search or a shared link with no prior session, so copy written for someone mid-journey reads as though they have missed something.

**Fix.** Rewrite these passages so they stand on their own for a first-time reader.

**Why this works.** A reference to state the visitor does not hold cannot be resolved, so the sentence carries no information and signals the page was not meant for them.

**Patch**

```
<!-- was: That is the promise of a free press in a democracy. -->
<p>__FILL_IN__:restate_without_assuming_prior_context</p>
```

**Verify**

```
Read each passage cold, as a stranger: does it depend on something you were never told?
```

*Source: Handout appendix, Personalization and prior context*

### F-040 · MEDIUM · 3 passage(s) assume context a first-time visitor does not have — on /about-npr/179876898/terms-of-use

*confidence: likely · check: `act.context.assumes_prior_context`*

**Evidence.** https://www.npr.org/about-npr/179876898/terms-of-use: "NPR will make the NPR+ Benefits available to you for so long as you continue your recurring donation to your s" (assumes a selection the visitor has not made via 'your selected station or to the '); "You agree that you will indemnify and hold harmless NPR, its Member stations, Content Providers, and their res" (assumes an earlier reference via 'the above representations'); "IF APPLICABLE LAW DOES NOT ALLOW THE EXCLUSION OF SOME OR ALL OF THE ABOVE IMPLIED OR STATUTORY WARRANTIES TO " (assumes an earlier reference via 'THE ABOVE IMPLIED'). Most visitors arrive on a deep page from search or a shared link with no prior session, so copy written for someone mid-journey reads as though they have missed something.

**Fix.** Rewrite these passages so they stand on their own for a first-time reader.

**Why this works.** A reference to state the visitor does not hold cannot be resolved, so the sentence carries no information and signals the page was not meant for them.

**Patch**

```
<!-- was: NPR will make the NPR+ Benefits available to you for so long as you continue your recurrin -->
<p>__FILL_IN__:restate_without_assuming_prior_context</p>
<!-- was: You agree that you will indemnify and hold harmless NPR, its Member stations, Content Prov -->
<p>__FILL_IN__:restate_without_assuming_prior_context</p>
<!-- was: IF APPLICABLE LAW DOES NOT ALLOW THE EXCLUSION OF SOME OR ALL OF THE ABOVE IMPLIED OR STAT -->
<p>__FILL_IN__:restate_without_assuming_prior_context</p>
```

**Verify**

```
Read each passage cold, as a stranger: does it depend on something you were never told?
```

*Source: Handout appendix, Personalization and prior context*

### F-041 · MEDIUM · 2 passage(s) assume context a first-time visitor does not have — on /about-npr/179878450/privacy-policy

*confidence: likely · check: `act.context.assumes_prior_context`*

**Evidence.** https://www.npr.org/about-npr/179878450/privacy-policy: "As described above, we may work with third-party analytics services to set tracking cookies or pixels on brows" (assumes text earlier on the page via 'As described above'); "For example, as described above, when you enter your email address on our Services (either to log in, or to si" (assumes text earlier on the page via 'as described above'). Most visitors arrive on a deep page from search or a shared link with no prior session, so copy written for someone mid-journey reads as though they have missed something.

**Fix.** Rewrite these passages so they stand on their own for a first-time reader.

**Why this works.** A reference to state the visitor does not hold cannot be resolved, so the sentence carries no information and signals the page was not meant for them.

**Patch**

```
<!-- was: As described above, we may work with third-party analytics services to set tracking cookie -->
<p>__FILL_IN__:restate_without_assuming_prior_context</p>
<!-- was: For example, as described above, when you enter your email address on our Services (either -->
<p>__FILL_IN__:restate_without_assuming_prior_context</p>
```

**Verify**

```
Read each passage cold, as a stranger: does it depend on something you were never told?
```

*Source: Handout appendix, Personalization and prior context*

### F-042 · MEDIUM · 1 passage(s) assume context a first-time visitor does not have — on /lifekit

*confidence: likely · check: `act.context.assumes_prior_context`*

**Evidence.** https://www.npr.org/lifekit: "As your current self, go back in time and give your younger self the reassurance you needed to hear back then." (assumes a selection the visitor has not made via 'your current self'). Most visitors arrive on a deep page from search or a shared link with no prior session, so copy written for someone mid-journey reads as though they have missed something.

**Fix.** Rewrite these passages so they stand on their own for a first-time reader.

**Why this works.** A reference to state the visitor does not hold cannot be resolved, so the sentence carries no information and signals the page was not meant for them.

**Patch**

```
<!-- was: As your current self, go back in time and give your younger self the reassurance you neede -->
<p>__FILL_IN__:restate_without_assuming_prior_context</p>
```

**Verify**

```
Read each passage cold, as a stranger: does it depend on something you were never told?
```

*Source: Handout appendix, Personalization and prior context*

### F-047 · LOW · A category page gives no indication of cost and no path to one

*confidence: confirmed · check: `act.trust.no_cost_signal`*

**Evidence.** https://www.npr.org/sections/news/ is a category page. No currency amount appears in its 2463 words of observed content, no schema.org offers.price is declared, no phrase such as "contact sales" or "request pricing" appears, and none of its 110 internal links leads to a pricing or quote page.

**Fix.** State a price, a price range, or an explicit route to getting one.

**Why this works.** Cost is the question a visitor on a commercial page is trying to answer; leaving it unanswerable ends the visit rather than deferring it.

**Patch**

```
<p class="price">__FILL_IN__:amount __FILL_IN__:currency</p>
<!-- or, if pricing is genuinely quote-based: -->
<p><a href="/contact">Request pricing</a> — typical range __FILL_IN__:range</p>
```

**Verify**

```
curl -s https://www.npr.org/sections/news/ | grep -Eo '[$£€][0-9,]+' | head -3
```

*Source: references/cro-frameworks.md*

<details>
<summary>38 finding(s) are moot until the blockers above are fixed</summary>

- **F-003** · medium · 45 content image(s) carry no alt text — blocked by F-001 (`read.nontext.informative_image_no_alt`)
- **F-004** · medium · Table data on 1 page(s) carries no column or row labels — blocked by F-001 (`extract.ans.table_not_extractable`)
- **F-005** · medium · The page title is 'Life Kit : NPR', which does not say what the page is about — blocked by F-001 (`extract.ans.title_not_entity_bearing`)
- **F-006** · medium · The site does not clearly state who publishes it — blocked by F-001 (`extract.sd.identity_graph_weak`)
- **F-008** · medium · 5 of 7 passages do not stand on their own — on /2022/07/11/1110926267/digital-minimalism-can-help-find-balance — blocked by F-001 (`extract.ans.chunk_not_self_contained`)
- **F-009** · medium · 6 of 7 passages do not stand on their own — on /2022/12/09/1141872654/build-a-healthy-relationship-with-your-in-laws — blocked by F-001 (`extract.ans.chunk_not_self_contained`)
- **F-010** · medium · 10 of 11 passages do not stand on their own — on /2026/09/24/nx-s1-5931971/trump-nih-science-funding-disruptions-charts — blocked by F-001 (`extract.ans.chunk_not_self_contained`)
- **F-011** · medium · 4 of 5 passages do not stand on their own — on /2026/09/24/nx-s1-5974336/teen-pregnancy-prevention-unspent-funding — blocked by F-001 (`extract.ans.chunk_not_self_contained`)
- **F-012** · medium · 4 of 5 passages do not stand on their own — on /2026/09/24/nx-s1-5978798/your-mother-your-mother-your-mother-review — blocked by F-001 (`extract.ans.chunk_not_self_contained`)
- **F-013** · medium · 5 of 6 passages do not stand on their own — on /2026/09/25/g-s1-144948/pandemic-prevention-treaty-agreement-world-health-organization — blocked by F-001 (`extract.ans.chunk_not_self_contained`)
- **F-014** · medium · 7 of 8 passages do not stand on their own — on /2026/09/25/nx-s1-5976804/supreme-court-trump-save-noncitizen-voting — blocked by F-001 (`extract.ans.chunk_not_self_contained`)
- **F-015** · medium · 5 of 6 passages do not stand on their own — on /2026/09/25/nx-s1-5978096/republicans-trump-midterm-elections — blocked by F-001 (`extract.ans.chunk_not_self_contained`)
- **F-016** · medium · 1 of 3 passages do not stand on their own — on /2026/09/25/nx-s1-5978875/midterms-redistricting-trump-missouri — blocked by F-001 (`extract.ans.chunk_not_self_contained`)
- **F-017** · medium · 5 of 6 passages do not stand on their own — on /2026/09/25/nx-s1-5979852/israels-prime-minister-addresses-u-n-general-assembly — blocked by F-001 (`extract.ans.chunk_not_self_contained`)
- **F-018** · medium · 1 of 3 passages do not stand on their own — on /about-npr/178660742/public-radio-finances — blocked by F-001 (`extract.ans.chunk_not_self_contained`)
- **F-019** · medium · 9 of 36 passages do not stand on their own — on /about-npr/179878450/privacy-policy — blocked by F-001 (`extract.ans.chunk_not_self_contained`)
- **F-020** · medium · fact_coverage 3/5: 2 claim(s) cannot be quoted from this page — on /2021/01/11/955692434/procrastination-is-more-than-putting-things-off-heres-how-to-kick-the-habit — blocked by F-001 (`extract.ans.fact_coverage_gap`)
- **F-021** · medium · fact_coverage 5/6: 1 claim(s) cannot be quoted from this page — on /2026/09/25/nx-s1-5976939/primetime-review-robert-pattinson-to-catch-a-predator — blocked by F-001 (`extract.ans.fact_coverage_gap`)
- **F-022** · medium · fact_coverage 5/6: 1 claim(s) cannot be quoted from this page — on /lifekit — blocked by F-001 (`extract.ans.fact_coverage_gap`)
- **F-023** · medium · Nothing near the top of the page states plainly what Keisha "TK" Dutes is — on /2021/01/11/955692434/procrastination-is-more-than-putting-things-off-heres-how-to-kick-the-habit — blocked by F-001 (`extract.ans.no_direct_answer_block`)
- **F-024** · medium · Nothing near the top of the page states plainly what Andee Tagle is — on /2022/12/09/1141872654/build-a-healthy-relationship-with-your-in-laws — blocked by F-001 (`extract.ans.no_direct_answer_block`)
- **F-025** · medium · Nothing near the top of the page states plainly what Joseph Kim is — on /2026/09/24/nx-s1-5931971/trump-nih-science-funding-disruptions-charts — blocked by F-001 (`extract.ans.no_direct_answer_block`)
- **F-026** · medium · Nothing near the top of the page states plainly what Justin Chang is — on /2026/09/24/nx-s1-5978798/your-mother-your-mother-your-mother-review — blocked by F-001 (`extract.ans.no_direct_answer_block`)
- **F-027** · medium · Nothing near the top of the page states plainly what Josh Baker is — on /2026/09/24/nx-s1-5979058/where-is-austin-tice-a-meeting-in-muskat — blocked by F-001 (`extract.ans.no_direct_answer_block`)
- **F-028** · medium · Nothing near the top of the page states plainly what Holly J. Morris is — on /2026/09/25/g-s1-144665/trump-arch-fat-bear-media-ai-news-quiz — blocked by F-001 (`extract.ans.no_direct_answer_block`)
- **F-029** · medium · Nothing near the top of the page states plainly what Jonathan Lambert is — on /2026/09/25/g-s1-144948/pandemic-prevention-treaty-agreement-world-health-organization — blocked by F-001 (`extract.ans.no_direct_answer_block`)
- **F-030** · medium · Nothing near the top of the page states plainly what Glen Weldon is — on /2026/09/25/nx-s1-5976939/primetime-review-robert-pattinson-to-catch-a-predator — blocked by F-001 (`extract.ans.no_direct_answer_block`)
- **F-031** · medium · Nothing near the top of the page states plainly what Kat Lonsdorf is — on /2026/09/25/nx-s1-5979852/israels-prime-minister-addresses-u-n-general-assembly — blocked by F-001 (`extract.ans.no_direct_answer_block`)
- **F-032** · medium · Nothing near the top of the page states plainly what NPR is — on /about-npr/179876898/terms-of-use — blocked by F-001 (`extract.ans.no_direct_answer_block`)
- **F-033** · medium · Nothing near the top of the page states plainly what NPR is — on /about-npr/179878450/privacy-policy — blocked by F-001 (`extract.ans.no_direct_answer_block`)
- **F-034** · medium · Nothing near the top of the page states plainly what NPR is — on /lifekit — blocked by F-001 (`extract.ans.no_direct_answer_block`)
- **F-035** · medium · 4 page(s) state time-sensitive facts but have not been updated — blocked by F-001 (`trust.date.stale_volatile_facts`)
- **F-036** · medium · The name 'NPR' is ambiguous and nothing on the homepage distinguishes it — blocked by F-001 (`trust.entity.name_collision`)
- **F-037** · medium · The site states more than one address or phone number for itself — blocked by F-001 (`trust.entity.nap_inconsistent`)
- **F-038** · medium · Nothing connects this site to an independent record of the same entity — blocked by F-001 (`trust.entity.no_external_corroboration`)
- **F-043** · medium · 2 page(s) declare structured data of the wrong kind — blocked by F-001 (`extract.sd.expected_type_missing`)
- **F-045** · low · The heading outline does not divide this page usefully — on 24 of 25 crawled pages — blocked by F-001 (`extract.ans.heading_structure_unusable`)
- **F-046** · low · 11 article(s) name nobody as the author — blocked by F-001 (`trust.authorship.unattributed`)

</details>

## What this audit could not assess

- **site** — Edge and CDN reachability for named AI crawlers was not assessed, because --probe-bot-ua was not set. This is the highest-value check in this marketplace: a CDN or WAF rule that returns 403 to OAI-SearchBot, PerplexityBot or Claude-SearchBot removes a brand from those assistants entirely, and leaves no trace in robots.txt or in what a human sees. If you own this site, re-run the orchestrator with the --probe-bot-ua flag:
    orchestrate.py <url> --out ./audit-output --probe-bot-ua
That sends ONE request per crawler, to the homepage only, with an auditor token appended to the user-agent string so it is identifiable in your logs. It is off by default because sending named-crawler user-agents to a site you do not own is not something an audit should do without being asked.
  - Checks not run: reach.edge.bot_ua_blocked, reach.edge.bot_ua_challenged
- **audit environment** — 6 check(s) were not assessed in this run, because an optional capability was unavailable (such as a headless browser or an opt-in probe) or the page carried too little evidence to judge. These are limits on what this run could evaluate, not defects of the site: `act.perf.above_fold_weight`, `extract.ans.fact_coverage_gap`, `reach.edge.bot_ua_blocked`, `reach.edge.bot_ua_challenged`, `read.render.nav_links_js_only`, `read.render.raw_text_gap`

## Deliberately not reported

Findings other tools would raise that we suppressed, and why:

- `extract.ans.no_direct_answer_block` ×3 — suppressed by design
- `extract.ans.no_evidence_markers` ×2 — suppressed by threshold
- `extract.ans.thin_content_for_page_type` ×23 — suppressed by design
- `extract.sd.expected_type_missing` ×1 — suppressed by low classifier confidence
- `reach.agent.llms_txt_absent` ×1 — suppressed by design
- `sitewide_collapse` ×1 — extract.ans.heading_structure_unusable: 24 page-level findings collapsed into one site-wide finding covering 24 pages

---

*brand-ai-readiness-audit 1.0.0 · 21 of 66 checks ran · AI crawler list snapshot 2026-09-09 (commit 0e111dcc24cb) · recommend-only: nothing was written to the audited site.*
