# Severity rubric (shared across all sub-audits)

Severity is **computed from evidence**, not hardcoded per rule, so the audit
generalizes to unseen sites. Each finding picks a level by impact + scope:

| Severity | Meaning | Typical triggers |
|----------|---------|------------------|
| **critical** | The page/brand is effectively invisible or unreadable to AI systems. | Homepage `noindex`; major AI crawlers blocked in robots.txt; primary content missing from raw HTML (client-only render). |
| **high** | A core discoverability/engagement mechanism is broken across the site. | No structured data anywhere; homepage has no Organization identity; large static-vs-rendered fact gap; missing `<title>`; served over HTTP; sitewide missing viewport; homepage doesn't say what the brand is. |
| **medium** | A real defect on some pages, or a meaningful improvement gap. | Partial schema coverage; no sitemap; stale dates; no meta descriptions; no CTA on most pages; heavy/slow pages; no FAQ markup. |
| **low** | Minor or best-practice gap; fix strengthens but isn't blocking. | No canonical tags; no Open Graph; sparse navigation; unattributed superlatives; missing contact text. |

## Scope escalation rule
A defect on the **homepage** or affecting **all** sampled pages escalates one level
versus the same defect on a single deep page. Example: `noindex` on the homepage =
critical; `noindex` on one page = high.

## Dimension tagging
Every finding is tagged `dimension: discoverability | engagement` by the orchestrator
from its `category`, so the report summarizes both halves of the Round-2 problem
independently (`summary.by_dimension`).

## Avoiding false positives
- Findings fire only with concrete evidence (counts, URLs, measured gaps), never on a
  single ambiguous signal.
- "Absence" findings that require sitewide certainty (e.g. *no* meta descriptions) fire
  only when the condition holds across **all** successfully-fetched pages, not a subset.
- Heuristic checks (intrusive interstitial, superlatives) stay at `low` severity because
  they infer intent from markup.
