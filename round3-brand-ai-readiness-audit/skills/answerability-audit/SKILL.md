---
name: answerability-audit
description: Determine whether a retrieval system could lift a specific fact off a page and quote it. Simulates retrieval by segmenting the page as a no-JavaScript crawler sees it into overlapping windows, deriving the claims the page makes about itself from its title, headings, hero copy and schema property values, then testing whether each claim survives inside at least one self-contained window - one with no unresolved pronoun, no backward reference, and the subject named inside it. Also checks for a direct answer near the top, an entity-bearing title, a usable heading outline, boilerplate dominance, thin content, and the evidence markers that make a passage quotable. Use when a brand is crawlable and marked up correctly but still never cited, or as the extract stage of a full AI-readiness audit.
license: MIT
compatibility: Python 3.9+ standard library only. trafilatura, when installed, improves main-content boundary detection; without it a text-density heuristic is used and confidence on one check is lowered accordingly.
allowed-tools: Bash(python:*) Read
---

# answerability-audit — stage: extract

**One question: can a retriever lift a fact off this page and quote it?**

The third of the three steps. A page can be perfectly crawlable and perfectly
marked up and still never be cited, because nothing on it can be quoted without
the surrounding page.

## When to use

When a site is technically healthy but absent from AI answers, or as part of the
extract stage.

## Inputs

```bash
python scripts/run.py --bundle ./evidence --profile ./profile.json
```

## Procedure — the retrievability simulation

1. Take the page as a **no-JavaScript crawler** sees it: raw main content,
   unless a rendered DOM was captured.
2. Segment into overlapping windows of about 300 tokens with 15% overlap, on
   sentence boundaries.
3. **Derive the page's claimed key facts** from title, H1, H2s, meta description
   and schema property values. Derived, never hardcoded, so this generalises to
   sites nobody has seen.
4. For each claim, find windows that carry it, then test **self-containment**:
   does the window still make sense lifted out? It fails if it opens with an
   unresolved pronoun, refers backwards to text outside itself, or never names
   the subject.
5. Report `fact_coverage: N/M` with each miss quoted and the reason it failed.

### What this is, and what it is not

This operationalises the handout appendix observation that the pages chosen as
sources are the ones a machine could *easily quote a clear fact from*. The
handout says nothing about chunking; the segmentation model is standard
retrieval practice and is our modelling choice, stated as such.

**The fix is never to chunk the page.** Google Search Central states there is no
requirement to break content into tiny pieces for AI to understand it. This
check models how a retriever might segment text in order to find where
self-containment breaks; the remedy is always to make the prose self-contained,
never to fragment it. See `references/chunking-model.md`, which carries the quote
so a later edit cannot quietly reintroduce chunking advice.

## Checks

| check_id | detects | default severity |
|---|---|---|
| `extract.ans.fact_coverage_gap` | claims that survive in no self-contained window | high |
| `extract.ans.chunk_not_self_contained` | passages that do not stand on their own | medium |
| `extract.ans.no_direct_answer_block` | nothing near the top states plainly what this is | medium |
| `extract.ans.title_not_entity_bearing` | a generic, templated or empty title | medium |
| `extract.ans.heading_structure_unusable` | missing H1, skipped levels, or a long page with no H2 | low |
| `extract.ans.boilerplate_dominant` | navigation and chrome dominate the page text | medium |
| `extract.ans.no_evidence_markers` | no statistic, quotation or source behind the claims | low |
| `extract.ans.thin_content_for_page_type` | wordcount below the profile floor for this page type | medium |

### SUPPRESS WHEN

- `extract.ans.fact_coverage_gap` — fewer than two derivable claims, or no
  windows, in which case the page is too sparse to judge without inventing a
  standard; or the page type is utility.
- `extract.ans.chunk_not_self_contained` — under 20% of windows fail, or there
  are fewer than three windows. When it fires alongside `fact_coverage_gap` on
  the same URL the orchestrator **dedupes it into that finding**, because they
  describe one defect and reporting both double-counts it.
- `extract.ans.no_direct_answer_block` — a definitional sentence exists near the
  top, or the meta description supplies one, in which case the fact is
  machine-available. A definitional sentence does **not** require an article:
  "X is monitoring software for data teams" defines X as well as "X is a tool".
- `extract.ans.title_not_entity_bearing` — the title is at least 15 characters
  and is not a generic template value; or the page type is utility.
- `extract.ans.heading_structure_unusable` — **multiple H1 elements alone never
  fire this.** Multiple H1s are valid in HTML5 sectioning contexts and are
  recorded as an observation, never as an error.
- `extract.ans.boilerplate_dominant` — the page is under 300 words, so there is
  nothing to dilute; or it is a category or listing page, where chrome-heavy
  markup is the idiom.
- `extract.ans.no_evidence_markers` — the page is below the archetype word
  floor, or the page type is product, contact, utility, category or home, where
  citations and statistics are not idiomatic. Fires at **low** because the
  supporting research measures a relative visibility improvement, not a defect:
  a page can be excellent without statistics.
- `extract.ans.thin_content_for_page_type` — the page is a category, listing or
  paginated archive; or it is a hub whose value is its links, carrying at least
  15 in-content internal links.

## Output

One JSON object on stdout, with `fact_coverage` stated as N/M and every missed
claim quoted with the reason it failed. Exit 0 ran, 3 precondition unmet,
1 internal error.

## Agent mode

Steps 3 to 5 can be done by hand: list what the page claims about itself, then
read each paragraph in isolation and ask whether it still names its subject.
**The segmentation is not faithfully reproducible by hand**; in agent mode
report `fact_coverage_gap` at `hypothesis` confidence and say so.

## Reference material

- `references/geo-methods.md` — Aggarwal et al., GEO, KDD 2024, and precisely
  what it does and does not support.
- `references/chunking-model.md` — the segmentation model, and the standing
  constraint that the fix is prose, never fragmentation.

## Guardrails

Read-only, no network. All observations come from the bundle.
