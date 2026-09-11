---
name: site-evidence-collector
description: Fetch and render a website exactly once and write a shared evidence bundle that every other audit skill reads. Handles robots.txt compliance, sitemap discovery, stratified crawling capped at 25 pages, per-host politeness, crawler-trap avoidance, soft-404 probing, optional headless rendering, and graceful handling of seeds that do not resolve, return errors, serve non-HTML, redirect off-domain, or forbid crawling entirely. Use as the first step of any site audit, or standalone to capture a reproducible snapshot of what a site serves. This is the only skill in the marketplace that touches the network.
license: MIT
compatibility: Python 3.9+ standard library only for crawling. Playwright is optional and enables rendered-DOM capture; without it the bundle records a degraded capability and downstream checks lower their confidence rather than skipping silently.
allowed-tools: Bash(python:*) Read Write WebFetch
---

# site-evidence-collector

**One question: what does this site actually serve?**

Every other skill reads the bundle this writes and performs no I/O of its own.
That is what stops six audit skills disagreeing about what the site served, and
what keeps the whole audit inside the runtime budget: one crawl, many readers.

## When to use

First, before any audit skill. Or standalone, to capture a snapshot you can
re-audit later without re-fetching.

## Inputs

```bash
python scripts/collect.py https://example.com --out ./evidence
python scripts/collect.py https://example.com --out ./evidence --probe-bot-ua
python scripts/collect.py --offline-root tests/fixtures/site_a --out ./evidence
```

`--max-pages` 25 · `--workers` 5 · `--delay` 0.4 · `--render` 6 ·
`--no-render` · `--time-budget` · `--dry-run` · `--probe-bot-ua` (off by default)

## Procedure

1. **Preflight the seed.** Handle the degenerate cases explicitly rather than
   crashing: a domain that does not resolve, a 404 or 500, a non-HTML
   content-type, and an off-domain redirect, which re-anchors the origin to the
   final host and records that it did. Each of these still writes a valid bundle.
2. **Fetch robots.txt** and parse it with the RFC 9309 matcher in
   `scripts/politeness.py`. From this point a disallowed path is never fetched;
   it is recorded in `urls_skipped_by_robots` instead.
3. **Discover** URLs from the sitemap and the homepage link graph.
4. **Filter traps** before fetching: repeating path segments, deep pagination,
   facet and filter parameters, feeds, wp-json and wp-admin, cart and checkout
   endpoints, authenticated areas, non-HTML extensions, and malformed hrefs such
   as a postal address or a bare email pasted into an href. Malformed hrefs are
   reported separately rather than turned into phantom URLs.
5. **Sample.** Stratify by provisional page type when at least three types are
   present, so a 400-post blog does not produce an audit of 25 blog posts.
   Otherwise sample by crawl depth and inbound link prominence, because a share
   cap cannot bind on a single-archetype site and stratifying there would add
   nondeterminism for no gain.
6. **Crawl** the sample: 5 workers, 0.4s per-host delay, `Retry-After` honoured,
   exponential backoff on 429 and 5xx.
7. **Render** a representative subset, prioritising the page types that carry
   the most auditable signal. If no renderer is available, record a degraded
   capability so downstream checks downgrade rather than skip silently.
8. **Probe** for soft 404s with deterministic URLs that cannot exist, sample a
   real 404 for comparison, check `/llms.txt` and Markdown negotiation, and run
   bot user-agent probes only if opted in.
9. **Write the bundle**, every collection sorted, every write atomic.

## Output

```
evidence/
  meta.json          audited_at, resolved_origin, status, tool_versions,
                     crawl stats, degraded_capabilities[], notes[]
  robots.txt         verbatim bytes
  headers/           per-URL status, hops, headers, TLS result, TTFB
  pages.jsonl        one sorted row per URL: status, title, wordcount,
                     main_text, headings, links, anchors, images, forms,
                     markup, dates, canonical, page_type, SPA signals
  render_pairs/      {slug}.raw.html and {slug}.rendered.html
  sitemap.json       fetched sitemaps, entries, coverage
  probes.json        soft-404 probes, real-404 sample, llms.txt, markdown
                     negotiation, bot reachability, TTFB samples
```

`status` is `complete`, `partial`, or `no_content_available`. Exit 0 whenever a
bundle was written, whatever it contains; 2 unusable output path; 3 bad
arguments; 1 internal error.

## Checks

This skill emits **no findings**. It is infrastructure. Counting it among the
check-bearing skills would misrepresent what it does.

## Guardrails

- **GET and HEAD only.** The method is validated against an allowlist, so no
  code path here can POST, PUT, PATCH or DELETE. Nothing is ever written to the
  audited site.
- **No cookies, no credentials, no authentication.** The opener is built with no
  cookie processor and no auth handler, so it cannot carry session state.
- **robots.txt is a hard constraint on our own crawling**, not advice. We do not
  fetch what it forbids; the report says we could not look.
- **Bot user-agent probing is opt-in and off by default.** With `--probe-bot-ua`,
  one request per bot, homepage only, with our auditor token appended to the
  user-agent string, so a site owner reading their logs can tell it was an audit
  rather than the real crawler. We do not silently impersonate.
- Response bodies are capped and redirects are bounded, so a hostile server can
  neither hang the crawler nor exhaust it.
- Output is refused on cloud-synced paths and inside `skills/`, and every write
  is atomic, so a full disk cannot leave a truncated bundle behind.
