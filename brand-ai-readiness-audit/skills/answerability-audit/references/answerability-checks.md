# Answerability check catalog

Mechanism 4: **are the facts clear enough to identify and extract?** Reachable and
readable is necessary but not sufficient — the fact has to be locatable.

## The rule this catalog exists to state

The test is whether **important facts are hard to identify**, not whether a page contains
enough lists and tables. Legal pages, documentation, editorial prose, essays and other
text-first page types are legitimately paragraph-heavy. Paragraph-heavy is not a defect,
and "walls of text" is not a check in this skill.

## Checks

| # | Check | Applies to | Trigger | Band |
|---|-------|-----------|---------|------|
| 1 | Unmarked Q&A content | any page | ≥3 question-style headings or ≥4 full question sentences on a page, and no FAQ schema anywhere in the sample | low (improvement) |
| 2 | Thin information pages | homepage, article, product, documentation, generic, contact — role confidence ≥ medium | <500 chars of body text on ≥ half the candidates | medium (defect, confidence medium) |
| 3 | Homepage self-description | homepage | opening 800 chars carry no descriptive phrasing and <2 sentence marks | medium (defect, confidence medium) |
| 4 | Reference page as unbroken prose | **product and documentation only** | ≥1200 chars, no list, no table, ≤1 heading | low (improvement) |
| 5 | Contact route as text | pages classified as contact | no mailto:, no tel:, no email text, no form | medium (defect) |

## Why check 4 is narrow

Product and documentation pages hold discrete look-up facts: specifications, parameters,
options, prices. When such a page has no headings and no list structure, each fact has to
be located inside continuous prose. That is a real extraction cost, specific to those
roles. Articles, legal text, generic content and unclassified pages are excluded **by
name**, and the exclusion is recorded in `skipped_checks` so a reader sees it was a
decision.

## Why check 3 was lowered from high

The v1 version counted bag-of-words signals including `"we "` and `"for "` and emitted
`high`. That fired on plenty of perfectly clear homepages. It now requires genuine
absence of both descriptive phrasing and sentence structure, is capped at medium, and on
a client-rendered page states that what a visitor actually sees was not assessed.

## What "answerable" means

- **Self-contained**: "The Widget Pro 3000 is rated for 10,000 cycles" beats "It's rated
  for that many cycles" two paragraphs away from the subject.
- **Explicit, not implied**: stated in text, not inferable only from a chart or an image.
- **Locatable**: a specific fact can be lifted without the surrounding paragraph.

None of those require a list. They require the sentence to exist and to stand alone.

## False-positive guards

- The FAQ check needs several **full question sentences** or question-style headings, not
  a count of question marks. A stray `?` in marketing copy does not qualify. And absence
  of FAQ content is never a finding at all — only unmarked, genuinely existing Q&A is.
- Thin-content and contact checks run only for roles whose purpose implies the content
  they are looking for, so a login screen, a tool or a listing is never penalised.
- Every check that measures the server HTML says so wherever text added by JavaScript
  would change the answer.
