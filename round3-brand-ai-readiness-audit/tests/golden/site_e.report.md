# AI-readiness audit — taxonomy-demo.test

*Audited 2026-05-28T20:26:40Z · status: **complete***

## What to do first

**F-001 · MEDIUM** — robots.txt blocks 2 crawler(s) whose role is contested

- **Do:** Decide deliberately whether the AI-surface exposure Applebot-Extended, Google-Extended controls is wanted.
- **Why it works:** These tokens modify how already-crawled content may be used on AI surfaces rather than whether the page can be fetched, so the cost is exposure, not access.
- **Effort:** low · **ICE:** 6.7
- **Verify:** `No mechanical check; this is a policy decision to record, not a defect to fix.`

**F-002 · MEDIUM** — fact_coverage 8/9: 1 claim(s) cannot be quoted from this page

- **Do:** State each key claim in a sentence that names the subject and stands on its own. Do NOT split the page into smaller blocks.
- **Why it works:** A passage that is quoted away from its page loses whatever its pronouns and back-references pointed at, so a claim that depends on them cannot be reproduced as an answer.
- **Effort:** low · **ICE:** 6.7
- **Verify:** `Copy any single paragraph out of the page and read it cold: does it still name what it is about, without the paragraphs around it?`

**F-003 · MEDIUM** — Nothing near the top of the page states plainly what Priya Raman is

- **Do:** Open with one sentence of the form "Priya Raman is a … that …".
- **Why it works:** A short definitional sentence is directly quotable as an answer; a reader that has to synthesise one from scattered prose usually picks a source that did the work.
- **Effort:** low · **ICE:** 6.7
- **Verify:** `Read the first two sentences of https://taxonomy-demo.test/blog/measuring-pipeline-latency: do they answer "what is this?" without further reading?`

**F-004 · MEDIUM** — Nothing near the top of the page states plainly what Northwind Analytics is

- **Do:** Open with one sentence of the form "Northwind Analytics is a … that …".
- **Why it works:** A short definitional sentence is directly quotable as an answer; a reader that has to synthesise one from scattered prose usually picks a source that did the work.
- **Effort:** low · **ICE:** 6.7
- **Verify:** `Read the first two sentences of https://taxonomy-demo.test/docs/getting-started: do they answer "what is this?" without further reading?`

**F-005 · MEDIUM** — Nothing near the top of the page states plainly what Northwind Analytics Team is

- **Do:** Open with one sentence of the form "Northwind Analytics Team is a … that …".
- **Why it works:** A short definitional sentence is directly quotable as an answer; a reader that has to synthesise one from scattered prose usually picks a source that did the work.
- **Effort:** low · **ICE:** 6.7
- **Verify:** `Read the first two sentences of https://taxonomy-demo.test/pricing: do they answer "what is this?" without further reading?`


## Summary

| Severity | Count |
|---|---|
| critical | 0 |
| high | 0 |
| medium | 7 |
| low | 0 |
| info | 1 |
| **total** | **8** |

Discoverability 7 · engagement 1.

## Reach — can a crawler get in?

### F-001 · MEDIUM · robots.txt blocks 2 crawler(s) whose role is contested

*confidence: likely · check: `reach.robots.dual_purpose_bot_blocked`*

**Evidence.** Blocked: Applebot-Extended, Google-Extended. These are genuinely contested rather than clearly training-only or clearly retrieval. Contested. Controls use of Applebot-crawled content for training Apple foundation models while leaving Applebot search indexing in place. Blocking is a licensing decision, not a visibility defect. Contested. Google documents this token as controlling whether content helps improve Gemini apps and grounded answers. It is not a crawler in its own right - it modifies how Googlebot-crawled content may be used - so blocking it does not remove the site from Google Search, but it can affect AI-surface grounding. Report as a trade-off the site may have chosen deliberately, never as an error. We report this as a trade-off the site may have chosen deliberately, not as an error. Snapshot 2026-09-09 (upstream commit 0e111dcc24cb).

**Fix.** Decide deliberately whether the AI-surface exposure Applebot-Extended, Google-Extended controls is wanted.

**Why this works.** These tokens modify how already-crawled content may be used on AI surfaces rather than whether the page can be fetched, so the cost is exposure, not access.

**Verify**

```
No mechanical check; this is a policy decision to record, not a defect to fix.
```

*Source: references/bot-taxonomy.md*

### F-008 · INFO · robots.txt blocks 2 training-only crawler(s) — recorded as an observation, not a defect

*confidence: confirmed · check: `reach.robots.ai_training_bot_blocked`*

**Evidence.** Blocked: CCBot, GPTBot. These collect content for model training corpora, not for answering questions at retrieval time. Blocking them does not reduce whether this brand is found or cited by AI assistants. The retrieval crawlers that do affect citation are allowed. Classification from a snapshot dated 2026-09-09 (upstream commit 0e111dcc24cb).

**Fix.** No change required. This is a content-licensing decision, and we report it only so it is visible.

**Why this works.** Training-corpus collection and answer-time retrieval are separate pipelines with separate user-agent tokens; blocking the former does not affect the latter.

**Verify**

```
No action to verify. Revisit only if the site's licensing stance changes.
```

*Source: references/bot-taxonomy.md*

## Extract — can it lift out the specific fact?

### F-002 · MEDIUM · fact_coverage 8/9: 1 claim(s) cannot be quoted from this page

*confidence: likely · check: `extract.ans.fact_coverage_gap`*

**Evidence.** https://taxonomy-demo.test/pricing: the page makes 9 derivable claims about 'Northwind Analytics Team'. Segmenting the 180 words a no-JS reader sees into 1 overlapping windows of about 300 tokens, 8 of 9 claims survive inside at least one window that still makes sense on its own. The misses: "Northwind Analytics pipeline monitoring" (from title) - no window contains the claim at all.

**Fix.** State each key claim in a sentence that names the subject and stands on its own. Do NOT split the page into smaller blocks.

**Why this works.** A passage that is quoted away from its page loses whatever its pronouns and back-references pointed at, so a claim that depends on them cannot be reproduced as an answer.

**Patch**

```
<!-- Make each claim self-contained IN PROSE. Do not split the page into
     smaller blocks: Google Search Central states there is no requirement
     to break content into tiny pieces for AI to understand it. -->

<!-- claim: Northwind Analytics pipeline monitoring  (no window contains the claim at all) -->
<p>Northwind Analytics Team __FILL_IN__:state_this_claim_in_one_sentence_that_names_the_subject.</p>
```

**Verify**

```
Copy any single paragraph out of the page and read it cold: does it still name what it is about, without the paragraphs around it?
```

*Source: Handout appendix, How assistants like ChatGPT use sources; Aggarwal et al., GEO: Generative Engine Optimization, KDD 2024 (arXiv:2311.09735)*

### F-003 · MEDIUM · Nothing near the top of the page states plainly what Priya Raman is

*confidence: likely · check: `extract.ans.no_direct_answer_block`*

**Evidence.** https://taxonomy-demo.test/blog/measuring-pipeline-latency: the first five sentences are "Home › Blog › Measuring pipeline latency Measuring pipeline latency without instrumenting every job " | "Pipeline latency is the time between a source system recording a fact and that fact becoming queryab" | "Most teams try to measure pipeline latency by adding timing code to every scheduled job, which is ac". None is a definitional statement of at most 50 words that names 'Priya Raman' and says what it is. A system answering "what is Priya Raman" has nothing short and quotable to lift.

**Fix.** Open with one sentence of the form "Priya Raman is a … that …".

**Why this works.** A short definitional sentence is directly quotable as an answer; a reader that has to synthesise one from scattered prose usually picks a source that did the work.

**Patch**

```
<p>Priya Raman is __FILL_IN__:category that __FILL_IN__:what_it_does_for_whom.</p>
```

**Verify**

```
Read the first two sentences of https://taxonomy-demo.test/blog/measuring-pipeline-latency: do they answer "what is this?" without further reading?
```

*Source: references/geo-methods.md*

### F-004 · MEDIUM · Nothing near the top of the page states plainly what Northwind Analytics is

*confidence: likely · check: `extract.ans.no_direct_answer_block`*

**Evidence.** https://taxonomy-demo.test/docs/getting-started: the first five sentences are "Home › Docs › Getting started Getting started with Northwind Analytics This guide connects a warehou" | "It takes about ten minutes and needs a read-only warehouse role." | "Step 1: create a read-only role Northwind Analytics reads table metadata only.". None is a definitional statement of at most 50 words that names 'Northwind Analytics' and says what it is. A system answering "what is Northwind Analytics" has nothing short and quotable to lift.

**Fix.** Open with one sentence of the form "Northwind Analytics is a … that …".

**Why this works.** A short definitional sentence is directly quotable as an answer; a reader that has to synthesise one from scattered prose usually picks a source that did the work.

**Patch**

```
<p>Northwind Analytics is __FILL_IN__:category that __FILL_IN__:what_it_does_for_whom.</p>
```

**Verify**

```
Read the first two sentences of https://taxonomy-demo.test/docs/getting-started: do they answer "what is this?" without further reading?
```

*Source: references/geo-methods.md*

### F-005 · MEDIUM · Nothing near the top of the page states plainly what Northwind Analytics Team is

*confidence: likely · check: `extract.ans.no_direct_answer_block`*

**Evidence.** https://taxonomy-demo.test/pricing: the first five sentences are "Home › Pricing Northwind Analytics pricing Northwind Analytics costs 49 USD per month on the Team pl" | "Both plans are billed monthly, include unlimited users, and start with a 14-day trial that does not " | "Team — 49 USD per month Up to 50 monitored tables, email and Slack alerts, 30 days of run history.". None is a definitional statement of at most 50 words that names 'Northwind Analytics Team' and says what it is. A system answering "what is Northwind Analytics Team" has nothing short and quotable to lift.

**Fix.** Open with one sentence of the form "Northwind Analytics Team is a … that …".

**Why this works.** A short definitional sentence is directly quotable as an answer; a reader that has to synthesise one from scattered prose usually picks a source that did the work.

**Patch**

```
<p>Northwind Analytics Team is __FILL_IN__:category that __FILL_IN__:what_it_does_for_whom.</p>
```

**Verify**

```
Read the first two sentences of https://taxonomy-demo.test/pricing: do they answer "what is this?" without further reading?
```

*Source: references/geo-methods.md*

### F-007 · MEDIUM · A article page carries only 277 words

*confidence: confirmed · check: `extract.ans.thin_content_for_page_type`*

**Evidence.** https://taxonomy-demo.test/blog/measuring-pipeline-latency has 277 words of main content against a floor of 300 for a article page on a saas-marketing site. Navigation, header and footer were excluded from the count. There is not enough here for a retrieval system to find an answer to anything specific.

**Fix.** Answer the questions a visitor arrives with, in specifics.

**Why this works.** A page with little text offers few facts to extract, so it is rarely the best available source for any question.

**Patch**

```
<h2>__FILL_IN__:question_visitors_actually_ask</h2>
<p>Priya Raman __FILL_IN__:specific_answer_with_a_number_or_name.</p>
```

**Verify**

```
curl -s https://taxonomy-demo.test/blog/measuring-pipeline-latency | sed -e 's/<[^>]*>//g' | wc -w
```

*Source: references/geo-methods.md*

## Act — does a visitor who arrives stay and act?

### F-006 · MEDIUM · A pricing page offers no evidence that anyone else has trusted this

*confidence: likely · check: `act.trust.no_social_proof`*

**Evidence.** https://taxonomy-demo.test/pricing (159 words) contains none of: review or rating language, a customer or user count, a case study reference, or an attributed quotation. A visitor deciding whether to act has only the brand's own claims to go on.

**Fix.** Add one specific, attributed piece of evidence near the primary action.

**Why this works.** An attributed third-party statement is evidence a visitor can weigh; a first-party claim is not, so it does not reduce the risk of acting.

**Patch**

```
<blockquote>
  <p>__FILL_IN__:specific_outcome_in_the_customers_words</p>
  <cite>__FILL_IN__:name, __FILL_IN__:role, __FILL_IN__:company</cite>
</blockquote>
```

**Verify**

```
Open https://taxonomy-demo.test/pricing: is there evidence from someone other than the brand?
```

*Source: references/cro-frameworks.md*

## Worth doing even though nothing is broken

### P-001 · Publish a comparison page for the alternatives buyers already weigh you against

Comparison questions are among the most common commercial queries, and a brand that has not written its own comparison is described using someone else's. This is a gap in coverage rather than a defect on any page, which is why it appears here and not as a finding.

## What this audit could not assess

- **site** — Edge and CDN reachability for named AI crawlers was not assessed, because --probe-bot-ua was not set. This is the highest-value check in this marketplace: a CDN or WAF rule that returns 403 to OAI-SearchBot, PerplexityBot or Claude-SearchBot removes a brand from those assistants entirely, and leaves no trace in robots.txt or in what a human sees. If you own this site, re-run the orchestrator with the --probe-bot-ua flag:
    orchestrate.py <url> --out ./audit-output --probe-bot-ua
That sends ONE request per crawler, to the homepage only, with an auditor token appended to the user-agent string so it is identifiable in your logs. It is off by default because sending named-crawler user-agents to a site you do not own is not something an audit should do without being asked.
  - Checks not run: reach.edge.bot_ua_blocked, reach.edge.bot_ua_challenged

## Deliberately not reported

Findings other tools would raise that we suppressed, and why:

- `act.trust.no_cost_signal` ×1 — suppressed by design
- `extract.ans.no_evidence_markers` ×4 — suppressed by threshold
- `extract.sd.absent_on_eligible_page` ×6 — suppressed by design
- `reach.agent.llms_txt_absent` ×1 — suppressed by design
- `reach.edge.bot_ua_blocked` ×1 — not assessed
- `reach.edge.bot_ua_challenged` ×1 — not assessed
- `trust.authorship.unattributed` ×1 — suppressed by design
- `trust.entity.no_external_corroboration` ×1 — suppressed by design

---

*brand-ai-readiness-audit 1.0.0 · 6 of 64 checks ran · AI crawler list snapshot 2026-09-09 (commit 0e111dcc24cb) · recommend-only: nothing was written to the audited site.*
