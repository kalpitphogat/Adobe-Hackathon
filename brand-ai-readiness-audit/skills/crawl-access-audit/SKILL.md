---
name: crawl-access-audit
description: >-
  Audit whether an automated crawler — especially the AI-assistant fetchers such as
  GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot and Google-Extended — can reach
  and index a site. Checks robots.txt presence and per-user-agent allow/deny rules
  with the paths they cover, XML sitemap discovery, per-URL HTTP status, meta-robots
  and X-Robots-Tag noindex on HTML pages only, robots Disallow coverage, canonical
  hygiene weighed against observed URL ambiguity, HTTPS, insecure sub-resources, and
  whether a CDN or WAF refuses an AI user-agent that robots.txt permits. Never
  treats an AI-crawler restriction as automatically critical, and never reports
  noindex on a sitemap or API response as a page defect. Use in the
  brand-ai-readiness-audit marketplace to explain why a brand is never crawled.
license: MIT
allowed-tools: [Bash, Read]
---

# Crawl & Access Audit

## When to use
Mechanism 1 of the chain: **can the machine reach the content?** If access fails, the
page does not exist for that system no matter how good it is.

## Inputs
The shared cache directory: `meta.json` robots policy, per-bot status, sitemap
discovery, edge-reachability probe, link sweep, and per-resource records.

## Procedure
Run `scripts/check_access.py <cache_dir>`.

1. **robots.txt present** — absence slows discovery; it blocks nothing. Improvement.
2. **AI crawlers disallowed** — reports exactly which user-agents are refused, split into
   the agents documented as *fetching pages to answer or cite* and the *bulk corpus
   crawlers*, because blocking those costs different things. At least half the citation
   fetchers blocked at the root is a high defect; some is medium; only bulk crawlers is a
   low improvement whose action says no change is needed for citation. The site **root**
   must be disallowed either way, so a `/search` rule cannot produce a high-severity
   finding. Never automatically critical, and the evidence never claims every assistant
   uses every listed agent.
   robots.txt is parsed per RFC 9309 against path **and** query, because the standard
   library parser drops the query and turns the common `Disallow: /?` into `Disallow: /`.
3. **XML sitemap** — improvement, and the evidence notes one may exist at a path this
   audit did not try.
4. **noindex** — applied to **HTML pages only**. Critical when it covers the homepage,
   high when it covers content-bearing roles, low for utility and authentication pages
   that are routinely and correctly noindexed. A sitemap or API response carrying
   `X-Robots-Tag: noindex` is recorded in `skipped_checks` as normal, never as a defect.
5. **robots-disallowed URLs** — reported with the explicit note that the audit respected
   the directive and therefore cannot judge what those URLs contain.
6. **4xx/5xx** — high only when a 5xx is present, since that indicates a failing origin
   rather than a retired URL.
7. **canonical** — an improvement unless parameterised URLs were actually observed in the
   sample, in which case there is real ambiguity for a canonical to resolve.
8. **HTTPS**, **insecure sub-resources** — sub-resources only; an outbound
   `<a href="http://">` is an ordinary link, not mixed content.
9. **Edge/CDN refusal** — compares a GPTBot-UA probe against a browser-UA probe.
   Requires an actual refusal **status** on a retried request; a network error alone is
   recorded as inconclusive in `skipped_checks` rather than becoming a critical finding.
10. **llms.txt** — an improvement only, explicitly labelled as an emerging, non-universal
    convention whose absence blocks nothing.

## Output
Envelope `{ "skill": "crawl-access-audit", "findings": [...], "skipped_checks": [...] }`.

## Guardrails
Read-only, GET/HEAD only. A URL disallowed by robots.txt is recorded as blocked and
**never requested** — the audit does not read what it is told not to read, and says so
in the finding rather than pretending to know.
