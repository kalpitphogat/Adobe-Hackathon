# The chunking model, and the constraint on every fix derived from it

## The standing constraint — read this first

**No check in this skill may ever recommend chunking, fragmenting, or
restructuring content into smaller blocks.**

Google Search Central, *Optimizing your website for generative AI features*,
states:

> There's no requirement to break your content into tiny pieces for AI to better
> understand it.

The same page also states:

> You don't need to create new machine readable files, AI text files, markup, or
> Markdown to appear in Google Search (including its generative AI
> capabilities), as Google Search itself doesn't use them.

The segmentation model described below exists **only to locate where
self-containment breaks**. It is a diagnostic instrument, not a target state.
The remedy for a failed window is always to make the prose name its own subject.
It is never to chop the page up.

This constraint is load-bearing and is stated here rather than only in code
comments, because the failure mode it guards against is a later well-meaning
edit turning "your claims are not self-contained" into "split your page into
smaller sections", which would contradict primary guidance from the largest
consumer of web content in the world.

If you are editing `retrievability_sim.py` and find yourself writing a patch
that adds headings, splits paragraphs, or shortens sections **for the benefit of
a machine**, stop: that is the failure this file exists to prevent.

## What the handout does and does not say

The handout has one appendix. Its subsection **"How assistants like ChatGPT use
sources"** says:

> the pages that get picked as sources tend to be the ones a machine could
> easily reach, easily read, and easily quote a clear fact from. If nothing
> about a brand is easy to reach, read, and quote, it simply won't make it into
> the answer at all.

That supports the **quotability** premise: a page from which no clear fact can
be lifted is unlikely to be used. It says nothing whatever about chunking,
window sizes, or overlap. There is no "Appendix B".

So the segmentation model below is **our modelling choice**, drawn from ordinary
retrieval practice, and is presented as such. It is not attributed to the task.

## The model

- **Window size ~300 tokens.** Large enough to contain a complete claim with its
  supporting sentence, small enough that a claim spread across a long section
  fails, which is the case worth surfacing.
- **Overlap ~15%.** Prevents a claim that straddles a boundary from failing for
  a reason that is an artefact of where we happened to cut.
- **Sentence boundaries.** Windows never split mid-sentence, because a truncated
  sentence would fail self-containment for a reason the author cannot act on.

Both parameters come from `threshold-profiles.json` so they are visible and
adjustable rather than buried.

## The self-containment test

A window fails if any of these hold:

1. **Unresolved pronoun opener.** It begins with *it, this, that, they, these,
   those, he, she, there, such*. Whatever the pronoun referred to is outside the
   window and cannot be recovered.
2. **Backward reference.** It contains *as mentioned above*, *see above*, *the
   aforementioned*, *as we saw*, or similar. The referent is elsewhere.
3. **The subject is never named.** The entity the page is about does not appear
   inside the window.

Test 3 matches on a **distinctive token**, not the literal string. A schema name
such as "Northwind Analytics Team" never appears verbatim in prose that says
"Northwind Analytics"; requiring the full string made every window fail on a
perfectly self-contained page. This was a real bug, found by the healthy control
fixture, and `tests/test_regressions.py` R2 keeps it fixed.

## What `fact_coverage` means

`fact_coverage: 7/9` means the page makes nine claims about itself — derived
from its title, headings, meta description and schema property values — and
seven of them survive inside at least one self-contained window. The two misses
are named and quoted, with the specific reason each failed.

The claims are **derived, never hardcoded**. There is no list of facts to look
for anywhere in this skill, because such a list would work on the sites we
thought of and fail on the ones we did not, and the audit is graded on sites
nobody has seen.

## What this check cannot tell you

It does not model any specific retrieval system. No vendor publishes its
segmentation, and this deliberately does not pretend to reproduce one. What it
measures is a property of the writing that holds regardless of implementation:
**whether a passage still means something when separated from its page**. That
property is what "easy to quote" reduces to, and it is stable across whatever
the retrievers happen to be doing this year.

A page can score 9/9 here and still not be cited, for reasons this skill cannot
see — the crawler was blocked, the brand is not corroborated anywhere, or the
competition is simply better. That is why this is one stage of five and not a
verdict on its own.
