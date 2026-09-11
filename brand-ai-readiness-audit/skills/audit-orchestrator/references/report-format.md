# Report format and the sub-audit contract

## Sub-audit envelope

Every non-entrypoint skill's script prints exactly one JSON object to stdout, on a
UTF-8 stream (`auditlib.emit` wraps stdout, so a cp1252 console cannot corrupt it):

```json
{
  "skill": "<skill-id>",
  "findings": [ ... ],
  "skipped_checks": [
    { "check": "raw-vs-rendered fact gap", "reason": "no rendered snapshot in cache" }
  ]
}
```

`skipped_checks` is how a skill says a check did not run and why. A limitation of the
audit is reported there; it never becomes a finding about the website.

## One finding

Built by `auditlib.finding(...)`, which enforces the evidence split:

```json
{
  "title": "HTML pages carry a noindex directive",
  "severity": "critical",
  "category": "crawl-access",
  "finding_type": "defect",
  "confidence": "high",
  "material": true,
  "mechanism": "reach",
  "page_role": "homepage",
  "checked": 10,
  "checked_unit": "sampled HTML pages",
  "dedup_key": "crawl-access:noindex-html",
  "evidence": "<observation> <interpretation> [Not verified by this audit: ...]",
  "evidence_detail": {
    "observation": "what was directly measured, with its scope. No inference.",
    "interpretation": "what that may imply, in cautious language.",
    "not_verified": "what the audit did NOT establish."
  },
  "suggested_action": { "summary": "...", "priority": "critical" }
}
```

The rule the whole marketplace turns on: **`observation` may only contain what the
program measured.** Anything inferred belongs in `interpretation`, and anything a reader
might wrongly assume was established belongs in `not_verified`. `evidence` is composed
from the three, so the string a grader reads can never claim more than the observation
supports.

`category` is one of: `crawl-access`, `render-extraction`, `structured-data`,
`freshness`, `corroboration`, `answerability`, `integrity`, `engagement`.
`mechanism` is one of: `reach`, `read-content`, `identify-facts`, `freshness`,
`corroborate`, `clarity-of-facts`, `trust`, `visitor-task`, `visitor-usability`.

## What the orchestrator does with them

1. **Normalise** — tag `skill` and `dimension`.
2. **Annotate root causes** — when a page's server HTML is sparse, findings marked
   `thin_html_sensitive` say so rather than being reported as independent problems.
3. **Validate evidence** — a finding with no observation, `checked: 0`, no action, or an
   invalid severity is dropped and listed in `scope.findings_rejected_for_weak_evidence`.
4. **Deduplicate** — findings sharing a `dedup_key`, or belonging to a known same-root-
   cause group, are merged. Merges are listed in `scope.findings_merged`.
5. **Calibrate severity** — `auditlib.calibrate` applies the gates in
   `severity-rubric.md`.
6. **Prioritise** — defects before improvements, then by severity, then deterministically
   by skill and title. Stable `F-001…` ids are assigned in that final order.

The orchestrator invents nothing: no facts, no evidence, no counts, and **no score** —
no scoring formula is implemented, so none is reported.

## Final report

Required floor: `site`, `audited_at`, `summary` (`total_findings`, `critical`, `high`,
`medium`, `low`), and per finding `id`, `title`, `severity`, `evidence`,
`suggested_action` (with `summary` and `priority`). Additive fields:

- Top level: `url`, `auditor`, `status` (`ok` | `partial` | `failed`), `scope`,
  `summary.by_dimension`, `summary.by_type`.
- `scope`: `pages_crawled`, `html_pages_analyzed`, `non_html_resources`,
  `resource_kinds`, `page_roles`, `max_pages_requested`, `sample_based`,
  `crawl_status`, `render_used`, `robots_respected`, `robots_blocked_urls`,
  `fetch_errors`, `skills_run`, `skills_errored`, `checks_skipped`, `findings_merged`,
  `findings_rejected_for_weak_evidence`, `note`.
- Per finding: `dimension`, `category`, `skill`, `finding_type`, `confidence`,
  `evidence_detail`, `mechanism`, `page_role`, `checked` with its `checked_unit`, and
  when a gate applied, `severity_capped_from` and `severity_cap_reason`.

`checked_unit` exists because a bare count is ambiguous: a finding that inspected 11
user-agents must not read as one that inspected 11 pages. It defaults to
`"sampled HTML pages"`.

## Failure

A crawl that reaches nothing produces `status: "failed"` with a `failure` object
(`reason`, `detail`), an empty `findings` array, zeroed counts, and a non-zero exit
code. A hollow report that could be mistaken for a clean site is never emitted.
