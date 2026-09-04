# Report format & sub-audit contract

## Sub-audit envelope
Every non-entrypoint skill's script prints exactly one JSON object to stdout:

```json
{
  "skill": "<skill-id>",
  "findings": [
    {
      "title": "short human title",
      "severity": "critical | high | medium | low",
      "category": "crawl-access | render-extraction | structured-data | freshness | corroboration | answerability | engagement",
      "evidence": "concrete, machine-derived evidence (counts, URLs, measured values)",
      "suggested_action": { "summary": "what to change and how", "priority": "critical|high|medium|low" },
      "checked": 12
    }
  ]
}
```
`checked` (optional) is how many pages/items were inspected for that finding —
it makes evidence auditable and keeps "0/12"-style statements honest.

## Final report (emitted by the orchestrator)
The orchestrator merges all envelopes and emits the fixed-schema report. Required floor
fields: `site`, `audited_at`, `summary` (counts by severity), and per finding `id`,
`title`, `severity`, `evidence`, `suggested_action`. Additive fields this marketplace
includes:

- Top level: `url`, `auditor`, `scope` (`pages_crawled`, `render_used`, `robots_respected`),
  `summary.total_findings`, `summary.by_dimension`.
- Per finding: `dimension`, `skill`, `checked`.

Findings are sorted by severity (critical→low) and given stable `F-001…` ids in that
order, so the most important problems lead the report.

## Helper
`auditlib.finding(...)` builds a conformant finding; `auditlib.emit(skill_id, findings)`
prints the envelope. Sub-audits should always go through these to stay in contract.
