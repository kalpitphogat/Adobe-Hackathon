# Attributions

No code in this marketplace was copied from any source. Where an **idea** was
worth porting, it was reimplemented from scratch against this project's own
interfaces, and the origin is credited below.

Everything here is MIT-licensed, as is this marketplace.

---

## Ideas reimplemented

### Crawler-trap guards, per-host politeness, soft-404 probing, and the JS-vs-noJS diff

**Origin:** [puneetindersingh/open-seo-crawler](https://github.com/puneetindersingh/open-seo-crawler) — MIT
**Used in:** `site-evidence-collector/scripts/traps.py`, `politeness.py`, `render.py`

Four ideas, reimplemented:

- **Refusing bad links before they corrupt a report.** Repeating path segments,
  page-builder pagination, and facet parameters generate unbounded URL space
  that all renders roughly the same page. Filtering them *before* fetching,
  rather than deduplicating afterwards, is the useful insight.
- **Malformed hrefs are a finding, not a URL.** A street address or bare email
  pasted into an `href` becomes a phantom page that inflates every count. We
  classify and report these separately.
- **Post-crawl soft-404 probes.** Requesting a URL that cannot exist and
  checking for a 200 detects servers with no bottom.
- **Per-host politeness with adaptive back-off**, and crawling in both rendered
  and raw modes to expose what a non-JS reader cannot see.

Our implementations differ substantially: the trap rules, the probe-URL
derivation (hashed from the origin so probes are deterministic across runs), the
stratified sampling with its prominence fallback, and the RFC 9309 matcher are
all our own.

### The Evidence / Impact / Fix / Severity / Confidence finding rubric

**Origin:** [Bhanunamikaze/Agentic-SEO-Skill](https://github.com/Bhanunamikaze/Agentic-SEO-Skill) — MIT
**Used in:** the finding shape in `references/skill-cli-contract.md`, enforced in
`orchestrate.py :: validate_finding`

The idea worth taking is that a finding without all five parts is not a finding.
We enforce it: the orchestrator **rejects** a finding missing evidence,
confidence or mechanism, records the rejection in `limitations[]`, and does not
silently drop it.

We extended the rubric with `stage`, `blocked_by`, `patch` and `verification`,
which is what the gate cascade and the paste-ready fixes are built on.

### Page-type calibration and ICE scoring

**Origin:** [Ads-insights/landingpage-cro-audit-kit](https://github.com/Ads-insights/landingpage-cro-audit-kit) — MIT
**Used in:** `site-profile-classifier/`, `engagement-audit/references/ice-model.md`

The premise we took: a B2C product page and a B2B service page need different
lenses, so calibration by page type and business model beats one generic
standard. That premise is the whole reason `site-profile-classifier` exists as a
separate skill.

We diverged on ICE. Ours makes the Confidence term a **deterministic map from
the finding's confidence enum** rather than a separate judgement, so the same
finding always scores the same and confidence is not counted twice. Reasoning in
`ice-model.md`.

### The AI crawler user-agent list

**Origin:** [ai-robots-txt/ai.robots.txt](https://github.com/ai-robots-txt/ai.robots.txt) — MIT
**Used in:** `crawl-access-audit/references/ai-bots.json`
**Snapshot:** dated `2026-09-09`, cross-checked against upstream commit
`0e111dcc24cbcdf4e609edde70f9f9184eac8b02` (2026-09-08)

Bundled as a **dated snapshot** and never fetched at runtime: an audit that
reaches out to a third-party list mid-run is neither deterministic nor
self-contained. Both the snapshot date and the upstream commit are printed in
every report, because bot names churn and a list that says how old it is beats
one that does not.

**The three-way classification is ours, not upstream's.** Upstream lists bots to
block. We needed to know what blocking each one *costs* — retrieval, training,
or contested — which is a different question, and the reason a flat list
produces bad findings. That classification, and the judgement in every `note`
field, is our own work and is not asserted by upstream.

---

## Primary sources cited in findings

These are cited *to the reader* inside findings, so they can check our reasoning
rather than trust it.

- **Aggarwal, Murahari, Rajpurohit, Kalyan, Narasimhan, Deshpande. "GEO:
  Generative Engine Optimization." KDD 2024. arXiv:2311.09735.** Cited by
  `extract.ans.no_evidence_markers`. What it supports and what it does not is
  set out in `answerability-audit/references/geo-methods.md`.
- **Google Search Central, *Optimizing your website for generative AI features*.**
  Quoted directly by `reach.agent.llms_txt_absent`, and the source of the
  standing constraint in `chunking-model.md` that no fix may recommend chunking.
- **SE Ranking, llms.txt study of nearly 300,000 domains (November 2025).**
  Cited by `reach.agent.llms_txt_absent` for the 10.13% adoption figure.
- **RFC 9309, Robots Exclusion Protocol.** The specification our matcher
  implements, and the source of the 71 conformance assertions in
  `tests/test_politeness.py`.
- **Scrapy robotstxt documentation**, and **CPython issue #138907, "Support RFC
  9309 in robotparser"**, for the documented limitations of
  `urllib.robotparser` that are the reason we do not use it.
- **WCAG 2.2**, success criteria 1.1.1, 1.4.4, 1.4.10 and 3.3.2, cited by the
  three checks with an accessibility basis.
- **sitemaps.org protocol 0.9**, **RFC 9110**, **RFC 6596**, **schema.org**, and
  **JSON-LD 1.1 (W3C)**, cited by the checks that implement them.

### The rule these citations follow

Every number in a finding must be traceable to a named primary source that was
actually read, or it is replaced by the mechanism with no number at all.

Three claims were removed under this rule during development, recorded here
because a removal list that is empty means nobody checked:

1. A publication month attributed to a study published in a different one. The
   figure was verified and kept; the date was wrong and was dropped.
2. A model-accuracy claim attributed to a study, which could not be located
   anywhere in the cited article. Dropped entirely.
3. A paraphrase of Google guidance taken from a blog summary. Replaced with a
   direct quotation from the primary Search Central page.

A citation that cannot be checked is worse than no citation, because it looks
like evidence.

---

## Deliberate duplication, and why it is not an oversight

`bundle.py` appears in six skill folders. The self-containment predicate appears
in both `answerability-audit/scripts/retrievability_sim.py` and
`engagement-audit/scripts/context_retention.py`. The atomic-write helper appears
in both `collect.py` and `emit_report.py`.

None of this is accidental. The handout requires every skill folder to
independently satisfy the agentskills.io spec, and a folder that cannot be
lifted out of this marketplace and run alone does not satisfy that. A `shared/`
package at the root would break that property and would add a tenth top-level
component to a marketplace already being judged for padding.

A copied ninety-line reader is the cheaper trade, and it is enforced rather than
trusted: `tests/validate_marketplace.py :: portability.no_cross_skill_imports`
walks the AST of every script and fails the build on any cross-skill import,
including a `sys.path` manipulation that reaches into a sibling folder.
`tests/test_regressions.py` R1 additionally asserts that a fix landing in one
copy lands in all six.

---

## Fixtures

All five fixture sites under `tests/fixtures/` are **hand-authored** for this
submission. No third-party HTML is redistributed here. Each exists to prove one
specific claim, and they are kept deliberately separate so that a change to one
mechanism cannot silently alter the proof of another.

The organisations they depict — Northwind Analytics, Harborview Clinic, Vantage
— are invented, and their domains use the reserved `.test` TLD so they can never
resolve to a real site.
