# The gate cascade

Implemented in `scripts/gate_model.py`, and partly in `engagement-audit/scripts/gating.py`.

## Why this exists

The Round-2 appendix, under **"How search visibility works (the basics)"**,
states:

> For a page to be visible at all, three things have to succeed in order — the
> crawler has to be let in, it has to be able to read what's on the page, and it
> has to be able to pick out the specific fact someone is looking for. If any
> one of those steps fails, the page effectively doesn't exist for that system —
> plainly visible to a human, yet invisible to the machine.

**In order** is the operative phrase. A flat checklist ignores it and reports
every symptom at full severity, so a site that blocks retrieval crawlers gets
fifteen criticals and no indication which one to fix first. Fourteen of them are
real defects that currently change nothing.

Encoding the ordering turns a list of symptoms into a diagnosis.

Note on citation: the handout has **one** appendix, "Appendix — Background
Concepts (from Round 2)", with unnumbered subsections. There is no "Appendix A"
or "Appendix B". Subsections are cited here by their real titles.

## Rule 0 — causal scope

Gates apply **only to findings with `category: "discoverability"`**.

`act` is never causally gated. A visitor arriving from an advertisement, an
email or a shared link does not care whether a crawler was let in. Treating
engagement as downstream of crawlability would be a causal error, and would
suppress real, actionable engagement findings on exactly the sites that most
need them.

## Rule 0b — evidential scope

> Engagement is **not causally** downstream of `reach`. Engagement **is
> evidentially** downstream of `read`.
>
> A blocked crawler tells us nothing about what a human visitor experiences, so
> a `reach` failure must never touch an `act` finding. But a page whose raw HTML
> is an empty mount point tells us we **never observed the page the visitor
> sees**. Any `act` check that reasons over visible content is then not
> "probably wrong" — it is **unevidenced**. Reporting it at reduced severity
> would assert something we did not observe.
>
> **Therefore:** when `read.render.empty_spa_shell` fires for a URL **and** no
> rendered DOM exists for that URL, every visible-content `act` check for that
> URL is **suppressed entirely** — not downgraded, not capped, not emitted. A
> `limitations[]` entry names the URL and every check that could not run.
>
> In one line: **`reach` failures cap discoverability findings because the
> defect is real but moot; `read` failures suppress engagement findings because
> the evidence is absent.** Capping asserts a weaker claim. Suppression asserts
> none. None is what we have.

Thirteen of the seventeen `act` checks are visible-content checks and are
subject to this. Four are exempt because they read the raw `<head>` or response
metadata, which is valid whether or not the body hydrated:
`act.blocker.not_mobile_ready`, `act.blocker.load_time_interstitial`,
`act.perf.above_fold_weight` (already gated by its own renderer precondition),
and `act.trust.no_policy_or_contact_path`.

**The site-wide case.** `act.trust.no_policy_or_contact_path` is exempt from the
per-page rule on the reasoning that it can be evidenced from *other* pages. On a
site where every page is an unobserved shell, there are no other pages either.
It is therefore suppressed **site-wide** when no page in the crawl has usable
content. Without that guard it fires falsely on every all-SPA site. Proved by
fixture `site_d`.

Suppression produces **one consolidated limitation**, never one per page.

## Rule 1 — gate closure

A gate closes when a finding at that stage has post-suppression severity
`critical`, or when two or more `high` findings at that stage affect the same
scope.

**Exception:** a check with a severity ceiling below `high` can never close a
gate. `reach.agent.llms_txt_absent` is capped at `low`, so Rule 1 already
prevents it from closing the reach gate; it is also listed explicitly in
`NEVER_CLOSES_GATE` so the guarantee does not depend on nobody ever raising its
severity. It sits in the `reach` stage because it is an access-surface file
served at the origin root, but it is an agent-orientation observation, not a
crawler-access defect.

## Rule 2 — scope of closure

- **Site scope:** `reach.robots.blanket_disallow`,
  `reach.robots.ai_search_bot_blocked`, `reach.edge.bot_ua_blocked`.
- **URL scope:** `reach.index.noindex_on_content`,
  `read.render.raw_text_gap`, `read.render.empty_spa_shell`.

A downstream finding is blocked when its URL set intersects a closed gate's
scope.

## Rule 3 — cap, never delete

A blocked discoverability finding stays in `findings[]`, with:

- `severity` capped at `medium` — capping only ever lowers, so a `low` finding
  stays `low`;
- `blocked_by` set to the blocking finding's id;
- `confidence` downgraded one notch **only if** the blocked evidence was itself
  collected through the blocked path. Evidence gathered independently keeps its
  confidence, because the block does not make it less true.

It is kept because it is a real defect that will matter the moment the blocker
is fixed. It is capped because right now it changes nothing.

## Rule 4 — no double-blocking

`blocked_by` names exactly one finding: the most upstream one. The report points
at a root cause, not a chain. `reach` outranks `read`.

## Rule 5 — reporting

`summary.blocked_findings` counts capped findings. `summary.suppressed_by_rule`
records what was deliberately not reported and why. `report.md` renders blocked
findings in a collapsed section headed *"N findings are moot until the blockers
above are fixed"*. Severity counts reflect **post-cap** values, so the headline
number is the honest one.

## Rule 6 — never gated

`limitations[]` and `proactive_recommendations[]` are not findings and are never
capped or suppressed.

## Worked examples, both checked in as goldens

**`site_b` — the cascade.** robots.txt disallows `OAI-SearchBot`,
`PerplexityBot` and `Claude-SearchBot` on `/`. A flat tool reports every
downstream defect at full severity. Output: **one critical**, 13 discoverability
findings capped at medium and all tagged `blocked_by: F-001`, and **8
engagement findings entirely unaffected, including two highs** — Rule 0 holding.

**`site_d` — Rule 0b site-wide.** Every page an unhydrated shell, no renderer.
Output: **zero `act` findings site-wide**, one consolidated `limitations[]` entry
naming all fourteen suppressed checks including the site-scoped one, and
`read.render.empty_spa_shell` reported at high/likely rather than
critical/confirmed because without a renderer we can see the signature but
cannot measure what the visitor lost.

The two fixtures are deliberately kept separate from `site_e`, which proves the
bot taxonomy, so that a change to one mechanism cannot silently alter the proof
of another.
