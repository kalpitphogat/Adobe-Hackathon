# Answerability check catalog

Round-2 appendix B/C: assistants build answers from pages they can most easily **quote a
clear fact from**. Reachable + readable is necessary but not sufficient — the fact must
be stated plainly and self-containedly.

## Checks
| # | Check | Signal | Severity |
|---|-------|--------|----------|
| 1 | FAQ/Q&A markup | no FAQPage/Question schema anywhere | medium |
| 2 | Thin pages | body text <500 chars | medium if majority, else low |
| 3 | Unclear homepage | first ~600 chars don't say what/who-for | high |
| 3b | Unstructured content | substantial pages (>=800 chars) with no lists, tables, or question headings | medium |
| 4 | Contact as text | no email/phone as extractable text | low |

## Chunkability / answer-formatting (check 3b)
Assistants extract and quote discrete *chunks* — a bulleted list item, a table row, a
question heading and its answer — far more readily than a long paragraph. A substantial
page that is a wall of prose, with no lists, tables, or question-style (`…?`) headings,
gives them little to lift cleanly. The fix is structural, not more words: turn key content
into question-led H2/H3 sections, bullets, and comparison tables.

## What "answerable" means
- **Self-contained**: each key sentence stands alone — "The Widget Pro 3000 is rated for
  10,000 cycles" beats "It's rated for that many cycles" two paragraphs from the subject.
- **Explicit, not implied**: state the fact in plain text; don't make the reader (or
  machine) infer it from a chart, image, or tone.
- **Structured for extraction**: FAQ pairs, short declarative sentences, labeled specs.
  FAQPage markup is the highest-yield format because each Q→A is a ready-made quote.

## The homepage sentence
The single most-quoted fact about a brand is the one-liner describing what it is and who
it serves. If the first screen doesn't state it plainly, assistants either skip the brand
or invent a description. Fix: lead with one plain sentence — *what it is, who it's for,
core value.*

## False-positive guards
- Homepage-clarity check requires both low text volume **and** few descriptive signals
  before firing, to avoid flagging concise-but-clear hero copy.
- Contact check scans several pages' combined text before concluding contact facts are
  absent.
