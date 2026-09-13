# Corroboration: what a single site can and cannot establish

## The premise

From the handout appendix, **"Why agreement across the web matters"**:

> Machines tend to treat a fact as more trustworthy when many independent places
> say the same thing. A claim that lives in only one spot is fragile; a claim
> repeated consistently across lots of unrelated sources is far more likely to
> be believed and repeated back. A related problem is mistaken identity: when
> several different things share a name, a system can mix them up unless there
> is something that clearly distinguishes one from the others.

Two distinct problems: **corroboration** (is this claim supported anywhere else)
and **identity** (is it clear which thing this is).

## The epistemic limit, and why confidence is capped

This audit reads **one site**. From one site we can observe:

- whether the site declares `sameAs` links to independent identity sources;
- whether it links outward to any sources at all;
- whether it names itself consistently across its own pages.

We **cannot** observe whether anybody else on the web mentions the brand.
Absence of corroboration is not observable from inside the thing being
corroborated.

Therefore `trust.entity.no_external_corroboration` is **capped at `likely`
confidence and can never reach `confirmed`**, dropping to `hypothesis` when the
optional Wikidata cross-check is unavailable. The finding text states explicitly
that it describes what was observed on this site, not what exists on the web.

This matters more than it might seem. A tool that reports "no external
corroboration" as a confirmed fact is claiming to have searched the web when it
has read one domain. The cap is the difference between a finding and a guess
wearing a finding's clothes.

## Why sameAs is the actionable proxy

`sameAs` is the one corroboration signal a site owner fully controls and that a
consumer can follow. It asserts that this site and an independent record
describe one entity, which lets a checker verify a claim here against a source
elsewhere instead of taking it on trust.

A `sameAs` target counts as authoritative when it points at an independent
identity source — Wikipedia, Wikidata, Companies House, SEC, OpenCorporates,
LinkedIn, GitHub, ORCID — rather than at self-published social presence, which
corroborates nothing because the same party wrote it.

Two or more resolving authoritative links suppress the finding entirely.

## Identity: why a footer address proves nothing

Name, address and phone consistency is checked because a site that disagrees
with itself gives a checker no version to settle on. But the comparison
normalises hard before reporting: phone numbers on digits alone, addresses on
collapsed whitespace. Punctuation, abbreviation and formatting differences are
not inconsistencies, and reporting them as such would be noise.

Separately, the mere presence of an address and phone number in a footer is
**not** evidence of anything. Every company site has one. It is used only for
consistency against the site's other mentions of itself, and never as a signal
that a business is local — a mistake that cost us a misclassification during
development and is now guarded in `site-profile-classifier`.

## Optional Wikidata

Off by default. When explicitly enabled it is a single read-only query, and any
failure degrades the check to `hypothesis` rather than failing the run. The
marketplace manifest resolves with no external service, and no finding depends
on a network call succeeding.
