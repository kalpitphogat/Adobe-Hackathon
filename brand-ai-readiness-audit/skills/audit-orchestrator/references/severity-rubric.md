# Severity rubric and gates (shared across all sub-audits)

Severity is computed from evidence, then **gated** by `auditlib.calibrate()`, which no
check can bypass. The gates exist because a check that "fires" is not the same as a
problem that matters.

## The five bands

| Band | Meaning | Requirement |
|------|---------|-------------|
| **critical** | A directly evidenced, material blocker affecting important public content or a core function. | `confidence: high` **and** `material: true` |
| **high** | A significant, evidence-backed problem that materially reduces discoverability or task completion. | `confidence: high` **and** `material: true` |
| **medium** | A meaningful weakness with plausible impact, but not a blocker. | `confidence: high` or `medium` |
| **low** | A minor issue, or a quality point. | any confidence |
| **improvement** | An optional, proactive recommendation. Not a defect. | carried as `finding_type: "improvement"`, severity capped at `low` |

`improvement` is expressed as a separate axis (`finding_type`) rather than a fifth
severity value, so `summary` keeps the four counts the report schema requires while the
defect/improvement split stays visible in `summary.by_type` and on every finding.

## The gates, in order

1. **Improvement cap.** `finding_type: "improvement"` can never exceed `low`. An
   optional recommendation is not permitted to compete with a real defect for attention.
2. **Confidence cap.** `confidence: "medium"` caps at `medium`; `confidence: "low"` caps
   at `low`. Confidence describes how firmly the *observation* supports the conclusion,
   not how common the pattern is.
3. **Materiality gate.** `critical` and `high` additionally require `material: true`. A
   check may only set it after establishing all five of:
   1. the affected resource is relevant (an HTML page the brand wants found, not a
      sitemap, an API response, or a login screen),
   2. the problem is real and was measured, not inferred from an absent convention,
   3. the impact is material to reaching, reading, extracting from, or using the page,
   4. the evidence recorded in the finding actually supports the conclusion drawn,
   5. the condition is not simply intentional design (an editorial robots.txt policy, a
      deliberately noindexed staging path, a tool with no marketing copy).

Every cap is recorded on the finding as `severity_capped_from` and `severity_cap_reason`,
so a reader can see that a rule fired and why it was not allowed to shout.

## What must NOT escalate severity

- A best practice is missing.
- A convention (llms.txt, Open Graph, FAQ markup, canonical, sameAs) is absent.
- A heuristic matched once.
- A page is unusual, or does not match a marketing-site template.
- A rule was written and is not satisfied.

## Defect versus improvement

- **Defect**: there is evidence of a meaningful existing problem. A noindex on a public
  product page; a 500 response; an unparseable JSON-LD block; a page with no viewport.
- **Improvement**: the current implementation may be entirely fine, and there is a
  proactive way to strengthen it. Adding llms.txt; adding sameAs; adding Open Graph;
  marking up an existing FAQ.

"Absence of best practice" is never relabelled as a defect without evidence of impact.

## Scope discipline

Every finding states what was inspected: `9/10 sampled HTML pages`, not `the website`.
`checked` carries the denominator, and `scope.sample_based` on the report says whether
the crawl hit its page cap. No finding generalises from the sample to the whole site
unless it says it is doing so.

## Audit limitations are not findings

If rendering was not run, if a probe was inconclusive, or if a role could not be
classified, that is recorded in `scope.checks_skipped` with a reason. It never becomes a
finding about the website.

## Dimension tagging

The orchestrator tags each finding `dimension: discoverability | engagement` from its
`category`, so both halves of the problem are summarised independently.
