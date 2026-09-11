# Brand AI-Readiness Audit

**Adobe University Hackathon 2026 — Round 3, Build the Agent Skill Marketplace**

Submitted by: `Lakshya Jain`
Team: `Lakshya, Tanmay, Kalpit`

---

Point this at a website. It tells you why AI assistants do not find, cite or
correctly describe the brand, and why visitors who do arrive leave without
acting — with evidence for every claim, a paste-ready fix, and an order to do
them in.

```bash
python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://example.com --out ./audit-output
```

Outputs `audit-report.json` and a `report.md` written for someone who is not an
engineer.

> ### Auditing your own site? Add `--probe-bot-ua`
>
> ```bash
> python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://your-site.com \
>     --out ./audit-output --probe-bot-ua
> ```
>
> This is the **single highest-value check in the marketplace**, and it is off by
> default. It detects whether your CDN or WAF returns 403 to AI crawlers — a rule
> that removes your brand from those assistants entirely while leaving **no trace
> in robots.txt and nothing visible to anyone browsing the site**. Bot-protection
> defaults do this routinely, to sites whose owners have no idea.
>
> It sends **one request per crawler, homepage only**, with an auditor token
> appended to the user-agent so your logs show it was an audit. It is off by
> default because sending named-crawler user-agents at a site you do not own is
> not something an audit should do unless asked. Without it, those two checks
> report *not assessed* — a blind spot, not a pass.

---

## The one idea this is built around

The Round-2 appendix, under *"How search visibility works (the basics)"*, says
three things must succeed **in order** for a page to be visible to a machine:
the crawler has to be let in, it has to be able to read the page, and it has to
be able to pick out the specific fact.

**In order** is the whole design.

A flat checklist ignores that and fires forty findings at any URL. Point it at a
site whose CDN refuses AI crawlers and it reports fifteen criticals, fourteen of
which are real defects that currently change nothing — because nothing is
reaching the page to be affected by them.

This marketplace encodes the ordering as a **gate cascade**. Every finding
carries a stage: `reach`, `read`, `extract`, `trust`, `act`. When an upstream
stage fails, downstream findings are still recorded, but capped and tagged with
the id of the one finding blocking them.

On the checked-in `site_b` fixture that is the difference between:

> 15 criticals, no indication where to start

and

> **1 critical**, plus *"13 findings are moot until F-001 is fixed"*, plus
> **8 engagement findings entirely unaffected** — because a visitor arriving
> from an ad does not care whether a crawler was let in.

That last clause is the part most implementations get wrong, and it has its own
rule.

### Rule 0b, the distinction worth reading

Engagement is **not causally** downstream of reach. But engagement **is
evidentially** downstream of read.

If a page serves an empty JavaScript shell and no rendered DOM was captured, we
never observed what the visitor sees. Engagement checks there are not "probably
wrong" — they are **unevidenced**. So they are **suppressed entirely**, not
downgraded, and one consolidated note says which checks could not run and why.

Capping asserts a weaker claim. Suppression asserts none. None is what we have.

Full statement in
[`gate-rules.md`](skills/ai-readiness-orchestrator/references/gate-rules.md).

---

## What is in the marketplace

Nine skills. One entrypoint.

| skill | question it answers | stage |
|---|---|---|
| **ai-readiness-orchestrator** | What matters most, and why? | — (entrypoint) |
| site-evidence-collector | What does the site actually serve? | — |
| site-profile-classifier | What kind of site and page is this? | — |
| crawl-access-audit | Can an AI crawler get in? | reach |
| render-gap-audit | Can it read the page without running JavaScript? | read |
| structured-data-audit | Is the fact machine-typed? | extract |
| answerability-audit | Is the fact quotable? | extract |
| trust-freshness-audit | Would a machine believe it, and is the page honest? | trust |
| engagement-audit | Does the visitor stay and act? | act |

### Why two of these are not checks

`site-evidence-collector` and `site-profile-classifier` emit no findings, and
that is deliberate rather than padding.

The **collector** is why six audit skills cannot disagree about what the site
served, and why the run fits the time budget: one crawl, one render pass, many
readers. It is the only component that touches the network.

The **classifier** is where generalisation lives. It is the only component that
turns "a site nobody has seen" into "known thresholds". No check anywhere
hardcodes a number; every one asks the profile. Remove it and every threshold
becomes a guess baked into a different file.

Neither performs a check. Both are load-bearing.

### How the entrypoint composes them

By **subprocess**, never by import:

```
orchestrate.py
  → collect.py           writes the evidence bundle          (network, once)
  → profile.py           archetype + page types + thresholds
  → 6 × run.py           each reads the bundle, prints one JSON object
  → gate cascade         cap, tag blocked_by, suppress per Rule 0b
  → dedupe, score, rank  severity → ICE → stage → check_id
  → emit                 audit-report.json + report.md + fix_patches/
```

No script imports from a sibling skill folder, so **any skill folder can be
lifted out of this marketplace and run alone**. Where two skills genuinely need
the same predicate it is duplicated, and the duplication is documented as a
portability decision. A test walks the AST of every script and fails the build
on a cross-skill import — including the `sys.path` dodge.

The contract is normative and was written before the audit skills:
[`skill-cli-contract.md`](skills/ai-readiness-orchestrator/references/skill-cli-contract.md).

---

## Checks

<!-- INVENTORY:AUTO -->
**64 checks** across six audit skills (47 discoverability, 17 engagement).

- Dependency tier: **61 CORE** (Python standard library only), **3 ENRICHMENT** (cannot fire without an optional dependency).
- By stage: reach 18, read 5, extract 14, trust 10, act 17.
- By skill: answerability-audit 8, crawl-access-audit 18, engagement-audit 17, render-gap-audit 5, structured-data-audit 6, trust-freshness-audit 10.
- Engagement checks suppressed entirely under gate Rule 0b when a page has no observed rendered content: **13** of 17.
<!-- /INVENTORY:AUTO -->

That block is **generated from the code**, not maintained by hand. Every check
declares itself in a `CHECKS` registry, and `tests/validate_marketplace.py`
parses those registries out of the source, compares them against
`tests/expected_inventory.json`, and fails the build if this README disagrees.
No count in any document here is hand-written.

The `trust` stage also covers **content integrity** — whether a page tries to
manipulate the machine reading it rather than serve the human. `trust-freshness-audit`
flags prompt-injection and LLM-directive text (often buried in HTML comments or
hidden nodes), large amounts of visually-hidden / cloaked text, and invisible
zero-width or bidi-control Unicode. Detection is deliberately conservative — narrow
injection phrasing, a multi-element threshold for cloaking, a run-length threshold
for invisible characters — so an ordinary page that merely mentions AI never trips it.

### Not firing is a feature

The rubric rewards few false positives, so suppression is enforced in code,
documented per check, tested, and **reported**: `summary.suppressed_by_rule`
tells the reader what we deliberately did not raise.

The rules other tools get wrong:

- **Missing `llms.txt` is LOW**, and only surfaced on documentation and
  developer-platform sites. Google Search Central states machine-readable AI
  text files are not used by Google Search and neither help nor harm visibility;
  no major provider has publicly committed to consuming it at answer time; SE
  Ranking measured 10.13% adoption across nearly 300,000 domains with no
  correlation to AI citations. Most tools fire this as high severity. Ours puts
  the reasoning in the finding so you can check it.
- **Blocking GPTBot is INFO, not a defect.** Training-corpus collection and
  answer-time retrieval are separate pipelines with separate user-agent tokens.
  Blocking GPTBot does not remove a site from ChatGPT search results.
  Google-Extended is reported separately as *contested*, because it is.
- **Multiple `<h1>` never fires as an error.** Valid in HTML5 sectioning.
- **Missing meta description is not a check at all** — it is a snippet input,
  not a retrieval input.
- **Slow response needs three samples** and reports the median, never the max.
- **Missing structured data is suppressed on utility pages** and short pages.

One check was **cut on evidence** during the build: `act.orient.h1_cta_mismatch`
fired on seven of eight pages of the healthy control fixture, including a
homepage where H1 *"Pipeline monitoring for data engineering teams"* and CTA
*"Start a 14-day trial"* is a **correct** pairing. Token overlap does not
measure whether an action follows from a promise. It could not earn a negative
fixture, so it does not ship. The reasoning is recorded in
`tests/expected_inventory.json` under `cut_checks`.

---

## Guardrails

- **Recommend-only.** No skill modifies a live site. There is no apply mode, and
  the HTTP layer validates its method against a `{GET, HEAD}` allowlist, so no
  code path can POST or DELETE.
- **robots.txt is a hard constraint on our own crawling**, not advice. On the
  `site_c` fixture, which disallows everything, the auditor fetches **zero**
  pages and reports that it could not look.
- **No authenticated areas, no cookies, no credentials.** The HTTP opener is
  built with no cookie processor and no auth handler.
- **Bot user-agent probing is opt-in and off by default.** With
  `--probe-bot-ua`: one request per bot, homepage only, our auditor token
  appended to the user-agent so a site owner can tell from their logs that it
  was an audit. We do not silently impersonate. Without the flag those checks
  report *not assessed* rather than passing quietly.
- **Politeness:** 5 workers, 0.4s per-host delay, `Retry-After` honoured,
  exponential backoff on 429 and 5xx, crawler-trap guards, 25-page cap.
- **No hosted API, key or account.** The optional Wikidata lookup is off by
  default, degrades to `hypothesis`, and never blocks a run.
- **Exit codes never encode what was found.** Exit 0 whenever a schema-valid
  report was written. A domain that does not resolve still produces a report and
  still exits 0; the outcome lives in `audit_status`.
- Output is refused inside `skills/` and on cloud-synced paths, and every write
  is atomic, so a full disk cannot leave a truncated report behind.

---

## Running the tests

```bash
python tests/validate_marketplace.py      # structure, spec compliance, doc drift
python tests/test_politeness.py           # RFC 9309 conformance
python tests/test_traps.py                # crawler traps and sampling
python tests/test_profile.py              # classifier, incl. 3 misclassification regressions
python tests/test_collector.py            # bundle contract + 5 hostile seeds
python tests/test_regressions.py          # every false positive found and fixed
python tests/test_suppression.py          # one case per documented SUPPRESS WHEN
python tests/test_gate_cascade.py         # the cascade, Rule 0b, the control
```

Five fixture sites, five separable claims, kept apart so a change to one
mechanism cannot silently alter the proof of another:

| fixture | proves |
|---|---|
| `site_a` | a well-built site produces **zero** high or critical findings |
| `site_b` | the gate cascade: one critical, downstream capped, engagement untouched |
| `site_c` | a blanket `Disallow: /` fetches nothing and reports one critical |
| `site_d` | an all-shell site produces **zero** engagement findings site-wide |
| `site_e` | the bot taxonomy: training INFO, dual-purpose MEDIUM, no cascade |

---

## Dependencies

**CORE — Python 3.9+ standard library only.** 61 of 64 checks, including every
`reach` check and every `act` check.

Note that `urllib.robotparser` is **not** used: it implements the 1996 draft
with no `*` wildcards, no `$` anchor, and no longest-match precedence, so it
disagrees with the crawlers we audit for. An RFC 9309 matcher is implemented on
the standard library and has 71 conformance assertions against the RFC's own
worked examples.

**ENRICHMENT — optional, declared per skill.** Playwright (rendered DOM),
Protego, extruct, trafilatura, htmldate. When absent, the affected check either
lowers its confidence and says why, or reports *not assessed* in `limitations[]`.
It never quietly passes.

The one place the zero-install guarantee bends, stated plainly:
`read.render.raw_text_gap` is `critical` and genuinely needs a renderer. CORE
ships `read.render.empty_spa_shell` as the zero-install path to a render-stage
finding, at high/likely instead of critical/confirmed. A zero-install run still
detects and reports the render gap; it cannot quantify it.

---

## Coverage of the Round-2 background concepts

| appendix subsection | where it is covered |
|---|---|
| How search visibility works | the gate cascade itself |
| How assistants use sources | `answerability-audit`, the retrievability simulation |
| How machines read a page | `render-gap-audit` |
| Why agreement across the web matters | `trust-freshness-audit` |
| Personalization and prior context | `act.context.*` — copy that assumes a session the visitor never had |
| Why machines drop content from emails | see below |

The email subsection describes a mechanism, not a medium: substance carried in a
form a reader cannot parse, and important lines buried in low-value filler. That
mechanism is exactly what `read.nontext.*` and
`extract.ans.boilerplate_dominant` detect. **We cover the mechanism in the
medium the task specifies** — the entrypoint takes a URL, so it audits websites,
not mailboxes.

---

## Known limitations, and how we found them

Most submissions claim their checks work. Here is one that did not, what it took
to notice, and what remains imperfect. If nothing in this section surprises you,
we did not test hard enough.

### The shell detector had zero recall on real sites

`read.render.empty_spa_shell` is the check the entire read stage depends on. It
passed every fixture. Then we pointed the audit at five live sites and it fired
**zero times** — including on a documentation site serving **16 words of body
text**, which is about as unambiguous a client-rendered shell as exists.

It required a mount point with a *known id* **and** a bundle script whose
filename matched a Next.js or Create-React-App shape. The site used
`<div class="_app">` and `/assets/application-<hash>.js`. Both discriminating
signals missed.

**The check had been tuned to a synthetic Next.js fixture, and the fixture gave
us false confidence in exactly the check we could least afford to be wrong
about.** A fixture proves a check does what you wrote; it cannot prove you wrote
the right thing, because you built both.

Rewritten against a signal that does not require recognising anyone's bundler:
no text **+** scripts present **+** (an empty mount point **or** a `<noscript>`
telling the visitor to enable JavaScript). That last signal is what a
client-rendered page says when it cannot render, in every framework. It now
fires correctly, and gate Rule 0b engages behind it.

### Navigation without `<nav>`

Chrome detection was tag-based, so a site whose menu is a `<table>` — normal for
anything built before HTML5 — had its own navigation treated as the opening
sentence of every page. On one static site this corrupted four checks at once
and produced 100 findings.

Now fixed with link-density block scoring: a block whose text is mostly anchor
text is navigation whatever tag it uses. `tests/fixtures/legacy_table_nav.html`
locks it in. That one change took the site from 100 findings to 32.

### What is still imperfect

- **No renderer in the default install.** Playwright is optional, so
  `read.render.raw_text_gap` cannot run and `empty_spa_shell` reports at
  high/likely rather than critical/confirmed. Reported in `limitations[]`, never
  passed over silently.
- **Corroboration is single-site by construction.** We can see that a site
  declares no `sameAs` links. We cannot see whether anyone else mentions it.
  Confidence is capped at `likely` for that reason and can never be `confirmed`.
- **Edge reachability is off by default.** See `--probe-bot-ua` above.
- **Main-content extraction is a heuristic.** trafilatura does it better and
  replaces ours when installed.

### How the checks were actually tested

Five hand-authored fixtures for behaviour that must be exact, then five live
sites chosen for **architectural variance** rather than convenience: a static
documentation site, a client-rendered documentation browser, a Shopify
storefront, a WordPress publisher, and a JavaScript-heavy SaaS marketing site.

That run produced **365 findings**, which was itself the finding. Twelve false
positives were identified and named before any threshold was touched — including
`aria-expanded="false"` on navigation dropdowns being counted as hidden content
(22 findings on one site), file sizes being reported as inconsistent phone
numbers, and a free open-source download page being asked for a price. Tuning
brought the same five sites to **205**, a 44% reduction, with the false negative
above fixed in the same pass.

Three doubts were investigated and **deliberately not acted on**, because the
findings turned out to be correct: a static site really does lack an `<h1>`, a
median time-to-first-byte really was near a second, and none of the five sites
declares `sameAs` on its homepage.

## Licence and attribution

MIT. See [`LICENSE`](LICENSE) and
[`ATTRIBUTIONS.md`](ATTRIBUTIONS.md) for borrowed ideas, their origins, and
their licences. No code was copied from any source; the ideas were reimplemented.
