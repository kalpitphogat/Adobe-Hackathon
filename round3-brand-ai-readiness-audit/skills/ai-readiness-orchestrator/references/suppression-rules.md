# Suppression rules

Every rule that stops a check from firing, in one place. Each is also stated in
the SKILL.md of the skill that owns it, and each has a case registered in
`tests/test_suppression.py`. A SUPPRESS WHEN clause documented in a SKILL.md
with no registered case fails the build; see
`tests/validate_marketplace.py :: docs.suppress_clauses_tested`.

## Why suppression is a first-class feature

The rubric rewards few false positives. A check that fires on a correct
implementation does more damage than a check that does not exist, because it
teaches the reader to distrust everything else in the report.

So suppression is not an afterthought here. It is enforced in code, documented
in prose, tested, and **reported**: `summary.suppressed_by_rule` tells the
reader what we deliberately did not raise and why. A tool that silently declines
to fire is indistinguishable from one that failed to look.

## The rules most tools get wrong

**llms.txt.** Reported at LOW, and only on documentation and developer-platform
sites. Google Search Central states plainly that machine-readable AI text files
are not used by Google Search and neither help nor harm visibility; no major
assistant provider has publicly committed to consuming llms.txt at answer time;
SE Ranking measured 10.13% adoption across nearly 300,000 domains with no
correlation to AI citations. Most tools fire this as high severity. The finding
carries the reasoning so the reader can check it rather than trust us.

**Blocked training crawlers.** INFO, never escalated. Training-corpus collection
and answer-time retrieval are separate pipelines with separate user-agent
tokens. Blocking GPTBot does not remove a site from ChatGPT search results.

**Missing structured data on utility pages.** Suppressed entirely. A missing
`Product` node on a 404 page is the most common structured-data false positive
there is.

**Multiple H1 elements.** Never fires as an error. Valid in HTML5 sectioning
contexts; recorded as an observation.

**Missing meta description.** Not a check at all in this marketplace. It is a
snippet input, not a ranking or retrieval input, so it does not warrant a
finding. It is used as *evidence* elsewhere — a meta description carrying a
definitional sentence suppresses `no_direct_answer_block`.

**Slow response.** Requires at least three samples and reports the **median**,
never the maximum. One slow response is weather.

**Thin content on listing pages.** Suppressed on category, listing and paginated
archives, and on hubs whose value is their links.

**Render gap.** Only fires when there is a rendered DOM to compare against.
Without one it reports as *not assessed* rather than passing.

## Categories of suppressor

- **by design** — the check does not apply to this page or site type.
- **by threshold** — below a floor that would make the finding noise.
- **not assessed** — a capability was unavailable; this is a blind spot, not a
  pass, and it appears in `limitations[]`.
- **deduped** — another finding reports the same defect with better evidence.
- **suppressed entirely** — gate Rule 0b: we never observed the page, so there
  is no evidence to report at any confidence.

## The rule behind the rules

A check ships only if it has a positive fixture, a negative fixture, and both
suppression assertions. One check was cut during development under this rule:
`act.orient.h1_cta_mismatch` fired on seven of eight pages of the healthy
control, including a homepage where the pairing was correct. It could not earn a
negative fixture, so it does not ship. The reasoning is recorded in
`tests/expected_inventory.json` under `cut_checks`.
