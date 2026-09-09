---
name: engagement-audit
description: Determine whether a visitor who arrives on a page can orient, act and continue. Checks whether the first screen says who the page is for and what it does, whether a deep page offers a path back, whether there is a clear single call to action and whether its label names an outcome, how much a form demands before giving anything back, whether the page dead-ends or assumes context a first-time visitor cannot have, and whether interstitials, missing mobile viewports, collapsed content, page weight, absent social proof, missing contact and policy paths or absent cost signals stop a willing visitor. Use when traffic arrives but does not convert, when bounce rate is high, or as the act stage of a full AI-readiness audit.
license: MIT
compatibility: Python 3.9+ standard library only. One check needs a rendered DOM to establish the fold and reports as not assessed without one. Never requires network access.
allowed-tools: Bash(python:*) Read
---

# engagement-audit — stage: act

**One question: does a visitor who arrives stay and act?**

This is the second half of the problem, and it is not downstream of the first.

## When to use

When a site gets traffic that does not convert, or as the act stage of a full
audit. Useful independently of any discoverability question.

## Inputs

```bash
python scripts/run.py --bundle ./evidence --profile ./profile.json
```

## Gate Rule 0b — read this before adding a check here

Engagement is **not causally** downstream of reach. A visitor arriving from an
ad, an email or a social link does not care whether a crawler was let in, so a
robots.txt block must never touch a finding in this skill.

Engagement **is evidentially** downstream of read. If a page serves an empty
application shell and no rendered DOM was captured, we never observed what the
visitor sees. A check that reasons over visible content is then not "probably
wrong" — it is **unevidenced**. Such checks are **suppressed entirely**, not
downgraded, because capping asserts a weaker claim while suppression asserts
none, and none is what we have.

Two scopes, and the second is easy to get wrong:

- **Per page** — a visible-content check is suppressed on any page we did not
  observe.
- **Site-wide** — `act.trust.no_policy_or_contact_path` is normally exempt,
  because it can be evidenced from *other* pages. On a site where every page is
  an unobserved shell there are no other pages, so it is suppressed too.
  Without that guard it fires falsely on every all-SPA site.

Suppression produces **one consolidated `limitations[]` entry naming every check
that could not run**, never one entry per page. `scripts/gating.py` implements
this, and the orchestrator repeats the enforcement as a safety net: a skill run
standalone must be as honest as one run under the orchestrator.

## Deliberate duplication

`scripts/context_retention.py` carries its **own** copy of the self-containment
predicate that `answerability-audit` also uses. It is copied, not imported,
because no script in this marketplace may import from a sibling skill folder:
the handout requires every skill folder to independently satisfy the
agentskills.io spec, and a folder that cannot be lifted out and run alone does
not. A small amount of duplicated logic is cheaper than a dependency that makes
every folder non-portable. Enforced by
`tests/validate_marketplace.py :: portability.no_cross_skill_imports`.

The two copies answer the same question about different subjects: there, whether
a passage makes sense lifted out of its page; here, whether a page makes sense
lifted out of a session.

## Checks

| check_id | detects | default severity |
|---|---|---|
| `act.orient.no_value_proposition` | the first screen never says who this is for | high |
| `act.orient.no_wayfinding` | a deep page with no path back to its parent | medium |
| `act.cta.absent_for_page_type` | a page that exists to produce an action, offering none | high |
| `act.cta.ambiguous_primary_label` | a primary action labelled with a verb and no object | medium |
| `act.cta.competing_primaries` | more equally-weighted actions than the profile allows | medium |
| `act.form.field_count_excessive` | more fields than the page type warrants | medium |
| `act.form.high_friction_required_fields` | personal detail demanded before anything is given | medium |
| `act.form.unlabelled_inputs` | fields with no programmatic label | medium |
| `act.context.no_onward_path` | a content page that dead-ends | medium |
| `act.context.assumes_prior_context` | copy presuming state a first-time visitor lacks | medium |
| `act.blocker.load_time_interstitial` | an overlay configured to interrupt on arrival | medium |
| `act.blocker.not_mobile_ready` | no mobile viewport, or zoom disabled | high |
| `act.blocker.content_gated_by_interaction` | key content behind a click | medium |
| `act.perf.above_fold_weight` | page weight beyond the budget | medium |
| `act.trust.no_social_proof` | a conversion page with no third-party evidence | medium |
| `act.trust.no_policy_or_contact_path` | no contact, privacy or terms path anywhere | medium |
| `act.trust.no_cost_signal` | a commercial page with no price and no path to one | medium |

### SUPPRESS WHEN

- `act.orient.no_value_proposition` — the page type is utility, article, docs,
  category, contact, about or **pricing**. An About page describes the company, a
  Contact page gives contact details, and a pricing page states cost. The
  audience-and-outcome sentence is a homepage and product-page idiom, and
  testing for it elsewhere produced false positives on a well-built control site.
- `act.orient.no_wayfinding` — the page is fewer than two levels deep, a
  `BreadcrumbList` or breadcrumb landmark exists, or any internal link points to
  an ancestor path.
- `act.cta.absent_for_page_type` — the page type is article, docs, utility or
  404, or a form with fields serves as the action.
- `act.cta.ambiguous_primary_label` — the label carries a noun object, or it is
  a consent control whose wording is fixed by law or convention.
- `act.cta.competing_primaries` — at or below the profile threshold. Repeats of
  one label are counted once, and navigation and footer chrome are excluded,
  because chrome repeats on every page and is not this page's call to action.
- `act.form.field_count_excessive` — the page type is checkout, where the fields
  are logistically necessary; or the form is multi-step, so the total overstates
  what the visitor faces at once.
- `act.form.high_friction_required_fields` — the page type is checkout,
  application or contact, where the field is necessary for the stated purpose.
- `act.form.unlabelled_inputs` — reported at **low** rather than medium when
  every unlabelled field carries a placeholder, since a placeholder is a weak
  label rather than none. Hidden and submit inputs are excluded.
- `act.context.no_onward_path` — the page type uses global navigation as its
  onward path. Only article, docs, product and other pages qualify; a homepage
  or pricing page does not.
- `act.context.assumes_prior_context` — the phrasing is ordinary second-person
  instruction. "Up to your plan limit" is standard documentation voice; only
  phrasings that presume a **prior session** qualify, such as "continue where
  you left off" or "as we discussed earlier".
- `act.blocker.load_time_interstitial` — the overlay is a cookie or consent
  banner, which is frequently a legal requirement rather than a marketing
  interruption.
- `act.blocker.not_mobile_ready` — a responsive viewport meta exists and does
  not disable zoom.
- `act.blocker.content_gated_by_interaction` — fewer than three collapsed
  regions, or under 150 words of main content. Progressive disclosure of a few
  sections, such as an FAQ whose questions are all visible, is a design choice.
- `act.perf.above_fold_weight` — no rendered DOM, so the fold cannot be
  established; or **fewer than three timing samples**. This check never fires on
  a single measurement and reports the median, never the maximum.
- `act.trust.no_social_proof` — the page type is informational. About and
  Contact pages were removed after firing on a well-built control site: they are
  informational, and social proof there is not what carries the decision.
- `act.trust.no_policy_or_contact_path` — any contact, privacy, terms, legal or
  support path is reachable; **or no page in the crawl has usable content**, in
  which case there is nothing to evidence it from (see Rule 0b above).
- `act.trust.no_cost_signal` — a price, a price range, an explicit
  contact-for-pricing phrase, or a link to a pricing page exists.

## Output

One JSON object on stdout. Exit 0 ran, 3 precondition unmet, 1 internal error.

## Guardrails

Read-only, no network. All observations come from the bundle. This skill never
submits a form, follows a call to action, or interacts with the audited site in
any way; it reads captured markup.
