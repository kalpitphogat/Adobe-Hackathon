# GEO: what the research supports, and what it does not

## The paper

Pranjal Aggarwal, Vishvak Murahari, Tanmay Rajpurohit, Ashwin Kalyan, Karthik
Narasimhan, Ameet Deshpande. **"GEO: Generative Engine Optimization."** KDD 2024.
arXiv:2311.09735.

The paper formalises optimisation for generative engines, builds GEO-bench over
10,000 queries across 25 domains, and evaluates nine content rewrites.

## What it found

Three rewrites reliably increased how prominently a page was used in a
synthesised answer: **citing sources, adding statistics, and adding
quotations** — reported as up to a 40% relative improvement in visibility in
their setup. Keyword stuffing, the classic SEO reflex, did not help. The paper
also notes that efficacy varies by domain, so a single universal recipe is not
what it establishes.

## How this marketplace uses it

`extract.ans.no_evidence_markers` fires when a page carries **none** of the
three markers, and it fires at **low** severity.

Low, deliberately. The paper measures a *relative visibility improvement in a
benchmark*, not a defect in a page. A page with no statistics is not broken. A
tool that reports "no statistics" as a high-severity failure is asserting more
than the research supports, and our finding text says so explicitly.

The finding also does not claim the 40% figure applies to the audited site. It
cites what was measured and in whose benchmark, and leaves the reader to judge
the transfer.

## What we do not claim

- We do not claim any specific assistant implements what the paper measured.
- We do not claim a causal effect on any particular brand's citation rate.
- We do not extrapolate the 40% figure beyond the benchmark it came from.

## The numbers policy this file exists to enforce

Every number in a finding must be traceable to a named primary source that was
actually read, or it is replaced by the mechanism with no number at all.

Three claims were removed under this rule during development, and they are
recorded here so the rule stays visible:

1. A specific month attributed to a study that was published in a different one.
   The figure was verified and kept; the date was wrong and was dropped.
2. An accuracy claim attributed to a study that could not be located anywhere in
   the cited article. Dropped entirely.
3. A paraphrase of Google guidance sourced from a blog summary. Replaced with a
   direct quotation from the primary Search Central page.

A citation that cannot be checked is worse than no citation, because it looks
like evidence.
