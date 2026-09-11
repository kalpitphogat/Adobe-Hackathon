# AI-readiness audit — harborview-clinic.test

*Audited 2026-05-28T20:26:40Z · status: **complete***

## What to do first

**F-001 · CRITICAL** — robots.txt blocks 3 AI retrieval crawler(s) that cite sources at answer time

- **Do:** Allow Claude-SearchBot, OAI-SearchBot, PerplexityBot in robots.txt, keeping any training-bot policy separate.
- **Why it works:** Retrieval crawlers fetch the page at the moment a user asks a question; if they are refused, the brand cannot appear as a source no matter how good the page is.
- **Effort:** low · **ICE:** 9.3
- **Verify:** `curl -s https://harborview-clinic.test/robots.txt and confirm each of Claude-SearchBot, OAI-SearchBot, PerplexityBot has an Allow rule that is at least as specific as any Disallow`

**F-002 · HIGH** — The first screen never says who this is for or what it does

- **Do:** Open with one sentence naming the audience and the outcome.
- **Why it works:** A visitor decides whether to stay from the first screen; without a sentence that names them, they have to do the work of inferring relevance, and most leave instead.
- **Effort:** low · **ICE:** 7.7
- **Verify:** `Open https://harborview-clinic.test/ and read only the first screen: can a stranger say who it is for and what it does?`

**F-003 · HIGH** — The first screen never says who this is for or what it does

- **Do:** Open with one sentence naming the audience and the outcome.
- **Why it works:** A visitor decides whether to stay from the first screen; without a sentence that names them, they have to do the work of inferring relevance, and most leave instead.
- **Effort:** low · **ICE:** 7.7
- **Verify:** `Open https://harborview-clinic.test/services and read only the first screen: can a stranger say who it is for and what it does?`

**F-009 · MEDIUM** — The main action is labelled 'Learn more', which names no outcome

- **Do:** Relabel with a verb and its object.
- **Why it works:** A label that names the outcome lets the visitor evaluate the click before making it, which removes the hesitation a bare verb creates.
- **Effort:** low · **ICE:** 7.7
- **Verify:** `Read the label alone, out of context: is it clear what happens next?`

**F-010 · MEDIUM** — The main action is labelled 'Submit', which names no outcome

- **Do:** Relabel with a verb and its object.
- **Why it works:** A label that names the outcome lets the visitor evaluate the click before making it, which removes the hesitation a bare verb creates.
- **Effort:** low · **ICE:** 7.7
- **Verify:** `Read the label alone, out of context: is it clear what happens next?`


## Summary

| Severity | Count |
|---|---|
| critical | 1 |
| high | 2 |
| medium | 16 |
| low | 2 |
| info | 0 |
| **total** | **21** |

Discoverability 13 · engagement 8.

## Fix these first — everything else is waiting on them

- 12 finding(s) are recorded but capped at medium because F-001 (robots.txt blocks 3 AI retrieval crawler(s) that cite sources at answer time) blocks them. They become relevant the moment F-001 is fixed.

## Reach — can a crawler get in?

### F-001 · CRITICAL · robots.txt blocks 3 AI retrieval crawler(s) that cite sources at answer time

*confidence: confirmed · check: `reach.robots.ai_search_bot_blocked`*

**Evidence.** Claude-SearchBot blocked by "Disallow: /" (line 12); OAI-SearchBot blocked by "Disallow: /" (line 6); PerplexityBot blocked by "Disallow: /" (line 9). Each of these fetches pages at answer time to ground or cite a response, so blocking them removes this brand from those assistants' answers entirely. 4 of 4 discovered paths are disallowed for these agents. Bot classification from a snapshot dated 2026-09-09 (upstream commit 0e111dcc24cb).

**Fix.** Allow Claude-SearchBot, OAI-SearchBot, PerplexityBot in robots.txt, keeping any training-bot policy separate.

**Why this works.** Retrieval crawlers fetch the page at the moment a user asks a question; if they are refused, the brand cannot appear as a source no matter how good the page is.

**Patch**

```
User-agent: Claude-SearchBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

```

**Verify**

```
curl -s https://harborview-clinic.test/robots.txt and confirm each of Claude-SearchBot, OAI-SearchBot, PerplexityBot has an Allow rule that is at least as specific as any Disallow
```

*Source: RFC 9309 section 2.2.2; vendor crawler documentation per references/ai-bots.json*

## Act — does a visitor who arrives stay and act?

### F-002 · HIGH · The first screen never says who this is for or what it does

*confidence: likely · check: `act.orient.no_value_proposition`*

**Evidence.** https://harborview-clinic.test/ (page type home). H1 is 'Welcome'. The first 400 characters of observed content read: "Welcome We are proud to serve the community with care and compassion." | "Our doors have been open for many years and we continue that tradition every single day." | "It has always been our belief that patients deserve better.". None of these names an audience or an outcome - no phrase of the form "for <who>", "helps <who> <do what>", or "<product> is a <category>" appears. A first-time visitor has to infer what this is.

**Fix.** Open with one sentence naming the audience and the outcome.

**Why this works.** A visitor decides whether to stay from the first screen; without a sentence that names them, they have to do the work of inferring relevance, and most leave instead.

**Patch**

```
<h1>Welcome</h1>
<p>__FILL_IN__:product_name is __FILL_IN__:category for __FILL_IN__:audience. It __FILL_IN__:primary_outcome.</p>
```

**Verify**

```
Open https://harborview-clinic.test/ and read only the first screen: can a stranger say who it is for and what it does?
```

*Source: references/cro-frameworks.md*

### F-003 · HIGH · The first screen never says who this is for or what it does

*confidence: likely · check: `act.orient.no_value_proposition`*

**Evidence.** https://harborview-clinic.test/services (page type other). H1 is 'Our Services'. The first 400 characters of observed content read: "Our Services We offer a comprehensive range of services designed around you." | "Each one is delivered by experienced practitioners in a comfortable setting." | "It is tailored to your needs.". None of these names an audience or an outcome - no phrase of the form "for <who>", "helps <who> <do what>", or "<product> is a <category>" appears. A first-time visitor has to infer what this is.

**Fix.** Open with one sentence naming the audience and the outcome.

**Why this works.** A visitor decides whether to stay from the first screen; without a sentence that names them, they have to do the work of inferring relevance, and most leave instead.

**Patch**

```
<h1>Our Services</h1>
<p>__FILL_IN__:product_name is __FILL_IN__:category for __FILL_IN__:audience. It __FILL_IN__:primary_outcome.</p>
```

**Verify**

```
Open https://harborview-clinic.test/services and read only the first screen: can a stranger say who it is for and what it does?
```

*Source: references/cro-frameworks.md*

### F-009 · MEDIUM · The main action is labelled 'Learn more', which names no outcome

*confidence: confirmed · check: `act.cta.ambiguous_primary_label`*

**Evidence.** https://harborview-clinic.test/: the most prominent action is 'Learn more' pointing at '/contact'. The label carries a verb but no object, so it does not say what the visitor gets by clicking. Other actions on the page: 'Contact'.

**Fix.** Relabel with a verb and its object.

**Why this works.** A label that names the outcome lets the visitor evaluate the click before making it, which removes the hesitation a bare verb creates.

**Patch**

```
<!-- was: <a href="/contact">Learn more</a> -->
<a href="/contact">__FILL_IN__:verb_plus_what_they_get</a>
```

**Verify**

```
Read the label alone, out of context: is it clear what happens next?
```

*Source: references/cro-frameworks.md*

### F-010 · MEDIUM · The main action is labelled 'Submit', which names no outcome

*confidence: confirmed · check: `act.cta.ambiguous_primary_label`*

**Evidence.** https://harborview-clinic.test/services: the most prominent action is 'Submit' pointing at '/contact'. The label carries a verb but no object, so it does not say what the visitor gets by clicking. Other actions on the page: 'Contact'.

**Fix.** Relabel with a verb and its object.

**Why this works.** A label that names the outcome lets the visitor evaluate the click before making it, which removes the hesitation a bare verb creates.

**Patch**

```
<!-- was: <a href="/contact">Submit</a> -->
<a href="/contact">__FILL_IN__:verb_plus_what_they_get</a>
```

**Verify**

```
Read the label alone, out of context: is it clear what happens next?
```

*Source: references/cro-frameworks.md*

### F-011 · MEDIUM · A top-of-funnel form requires 6 high-friction field(s)

*confidence: confirmed · check: `act.form.high_friction_required_fields`*

**Evidence.** https://harborview-clinic.test/contact (page type contact) marks these as required: phone, company, job_title, dob, address1, postcode. A visitor at this stage has not yet been given anything, so personal or organisational detail is being demanded before any value is delivered. On a checkout or application page these same fields would be necessary and this check does not fire there.

**Fix.** Make phone, company, job_title, dob, address1, postcode optional, or move them to a later step.

**Why this works.** Fields that feel invasive relative to what is being offered cause abandonment at the field itself, not at submission.

**Patch**

```
<input name="phone" type="tel">  <!-- required attribute removed -->
<input name="company" type="text">  <!-- required attribute removed -->
<input name="job_title" type="text">  <!-- required attribute removed -->
<input name="dob" type="date">  <!-- required attribute removed -->
<input name="address1" type="text">  <!-- required attribute removed -->
<input name="postcode" type="text">  <!-- required attribute removed -->
```

**Verify**

```
curl -s https://harborview-clinic.test/contact | grep -E 'name="(phone|company|job_title|dob|address1|postcode)"'
```

*Source: references/cro-frameworks.md*

### F-014 · MEDIUM · 1 passage(s) assume context a first-time visitor does not have

*confidence: likely · check: `act.context.assumes_prior_context`*

**Evidence.** https://harborview-clinic.test/services: "Physiotherapy As mentioned above, this is delivered by our experienced team." (assumes an earlier conversation via 'As mentioned above'). Most visitors arrive on a deep page from search or a shared link with no prior session, so copy written for someone mid-journey reads as though they have missed something.

**Fix.** Rewrite these passages so they stand on their own for a first-time reader.

**Why this works.** A reference to state the visitor does not hold cannot be resolved, so the sentence carries no information and signals the page was not meant for them.

**Patch**

```
<!-- was: Physiotherapy As mentioned above, this is delivered by our experienced team. -->
<p>__FILL_IN__:restate_without_assuming_prior_context</p>
```

**Verify**

```
Read each passage cold, as a stranger: does it depend on something you were never told?
```

*Source: Handout appendix, Personalization and prior context*

### F-019 · MEDIUM · A 13-field form stands between the visitor and the action

*confidence: confirmed · check: `act.form.field_count_excessive`*

**Evidence.** https://harborview-clinic.test/contact (page type contact) posts to /send with 13 visible fields against a threshold of 8 for this site type. Fields, with * marking required: first_name:text*, last_name:text*, email:email*, phone:tel*, company:text*, job_title:text*, dob:date*, address1:text*, address2:text, city:text*, postcode:text*, referrer:text, message:text. Hidden and submit inputs were excluded from the count.

**Fix.** Ask only for what is needed to deliver the next step; collect the rest later.

**Why this works.** Every field is a separate decision and a separate chance to abandon; fields that are not needed to fulfil the request cost completions without returning anything.

**Patch**

```
<form action="/send" method="post">
  <label for="email">__FILL_IN__:label_text</label>
  <input id="email" name="email" type="email" required>
  <button type="submit">__FILL_IN__:verb_plus_object</button>
</form>
<!-- Collect the remaining detail after the visitor has received something. -->
```

**Verify**

```
curl -s https://harborview-clinic.test/contact | grep -cE '<(input|select|textarea)'
```

*Source: references/cro-frameworks.md*

### F-021 · LOW · 13 form field(s) have no programmatic label

*confidence: confirmed · check: `act.form.unlabelled_inputs`*

**Evidence.** https://harborview-clinic.test/contact: 13 of 13 fields have no <label>, aria-label or aria-labelledby: first_name, last_name, email, phone, company, job_title, dob, address1. All of them do carry a placeholder, which disappears on focus and is not exposed as a label, so this is reported at low severity.

**Fix.** Give every field a visible, associated label.

**Why this works.** A placeholder vanishes as soon as the field is focused, so a visitor who pauses mid-form loses the only description of what the field wanted.

**Patch**

```
<label for="first_name">First name</label>
<input id="first_name" name="first_name" type="text">
<label for="last_name">Last name</label>
<input id="last_name" name="last_name" type="text">
<label for="email">Email</label>
<input id="email" name="email" type="email">
<label for="phone">Phone</label>
<input id="phone" name="phone" type="tel">
```

**Verify**

```
curl -s https://harborview-clinic.test/contact | grep -c '<label'
```

*Source: WCAG 2.2 Success Criterion 3.3.2 Labels or Instructions*

<details>
<summary>12 finding(s) are moot until the blockers above are fixed</summary>

- **F-004** · medium · The page title is 'Home', which does not say what the page is about — blocked by F-001 (`extract.ans.title_not_entity_bearing`)
- **F-005** · medium · The page title is 'Contact', which does not say what the page is about — blocked by F-001 (`extract.ans.title_not_entity_bearing`)
- **F-006** · medium · The page title is 'Services', which does not say what the page is about — blocked by F-001 (`extract.ans.title_not_entity_bearing`)
- **F-007** · medium · The page title is 'Team', which does not say what the page is about — blocked by F-001 (`extract.ans.title_not_entity_bearing`)
- **F-008** · medium · The site does not clearly state who publishes it — blocked by F-001 (`extract.sd.identity_graph_weak`)
- **F-012** · medium · The name 'Home' is ambiguous and nothing on the homepage distinguishes it — blocked by F-001 (`trust.entity.name_collision`)
- **F-013** · medium · Nothing connects this site to an independent record of the same entity — blocked by F-001 (`trust.entity.no_external_corroboration`)
- **F-015** · medium · A home page carries only 48 words — blocked by F-001 (`extract.ans.thin_content_for_page_type`)
- **F-016** · medium · A contact page carries only 17 words — blocked by F-001 (`extract.ans.thin_content_for_page_type`)
- **F-017** · medium · A other page carries only 70 words — blocked by F-001 (`extract.ans.thin_content_for_page_type`)
- **F-018** · medium · A about page carries only 8 words — blocked by F-001 (`extract.ans.thin_content_for_page_type`)
- **F-020** · low · The heading outline does not divide this page usefully — blocked by F-001 (`extract.ans.heading_structure_unusable`)

</details>

## What this audit could not assess

- **site** — Edge and CDN reachability for named AI crawlers was not assessed, because --probe-bot-ua was not set. This is the highest-value check in this marketplace: a CDN or WAF rule that returns 403 to OAI-SearchBot, PerplexityBot or Claude-SearchBot removes a brand from those assistants entirely, and leaves no trace in robots.txt or in what a human sees. If you own this site, re-run the orchestrator with the --probe-bot-ua flag:
    orchestrate.py <url> --out ./audit-output --probe-bot-ua
That sends ONE request per crawler, to the homepage only, with an auditor token appended to the user-agent string so it is identifiable in your logs. It is off by default because sending named-crawler user-agents to a site you do not own is not something an audit should do without being asked.
  - Checks not run: reach.edge.bot_ua_blocked, reach.edge.bot_ua_challenged

## Deliberately not reported

Findings other tools would raise that we suppressed, and why:

- `extract.ans.fact_coverage_gap` ×4 — not assessed
- `extract.ans.no_evidence_markers` ×2 — suppressed by threshold
- `extract.sd.absent_on_eligible_page` ×4 — suppressed by design
- `reach.agent.llms_txt_absent` ×1 — suppressed by design
- `reach.edge.bot_ua_blocked` ×1 — not assessed
- `reach.edge.bot_ua_challenged` ×1 — not assessed
- `reach.sitemap.absent_or_invalid` ×1 — suppressed by threshold

---

*brand-ai-readiness-audit 1.0.0 · 13 of 64 checks ran · AI crawler list snapshot 2026-09-09 (commit 0e111dcc24cb) · recommend-only: nothing was written to the audited site.*
