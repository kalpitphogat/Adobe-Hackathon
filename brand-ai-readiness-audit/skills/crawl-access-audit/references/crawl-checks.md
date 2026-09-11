# Crawl & access check catalog

This skill owns mechanism 1: **can the machine reach the content?** Nothing here judges
content quality.

| # | Check | Trigger | Band | Material when |
|---|-------|---------|------|---------------|
| 1 | robots.txt present | `/robots.txt` != 200 | low (improvement) | never — absence slows discovery, it blocks nothing |
| 2 | AI crawlers disallowed | a tested AI user-agent cannot fetch the site root | see the two-group rule below | at least half the citation fetchers are blocked at the root |
| 3 | XML sitemap | no `Sitemap:` line and `/sitemap.xml` is not a urlset | low (improvement) | never |
| 4 | noindex | meta robots or `X-Robots-Tag` on an **HTML page** | critical on homepage, high on content roles, low on utility/auth | a homepage or content-bearing role is affected |
| 5 | robots-disallowed URLs | a Disallow rule matched a sampled URL | medium, confidence medium | never — contents unknown by design |
| 6 | HTTP errors | a sampled URL returns 4xx/5xx | high if any 5xx, else medium | a 5xx is present |
| 7 | canonical | no `rel=canonical` on any successful page | medium defect if parameterised URLs were observed, else low improvement | URL ambiguity was actually observed |
| 8 | HTTPS | base URL is `http://` | high | always |
| 9 | broken internal links | HEAD-then-GET sweep of up to 15 homepage links returns 4xx/5xx | medium | always |
| 10 | insecure sub-resources | `http://` in a `src`/`link href` on an https page | medium | always |
| 11 | edge/CDN AI-bot refusal | homepage serves a browser UA but returns a refusal **status** to the GPTBot UA, on a retried request | critical | always |
| 12 | llms.txt | no `/llms.txt` | low (improvement) | never |

## noindex applies to HTML pages only

An XML sitemap, a JSON feed or an API response carrying `X-Robots-Tag: noindex` is
entirely normal and says nothing about whether the site's pages are indexable. Those
resources are excluded from the check and the exclusion is recorded in `skipped_checks`.
Within HTML pages, the role matters too: an authentication or utility page is routinely
and correctly noindexed, so it does not reach `high`.

## AI crawler restriction, and why the agent matters

Blocking AI crawlers is frequently a deliberate content-licensing decision, and the
finding says so in its own evidence. Two things then decide how loudly it is reported.

**First, the site root must be disallowed**, so a `Disallow: /search` rule cannot produce
a high-severity finding.

**Second, which agents.** The tested user-agents are not interchangeable:

| Group | Agents | What blocking costs |
|-------|--------|---------------------|
| **Citation fetchers** | GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-Web, anthropic-ai, PerplexityBot, Google-Extended, Applebot-Extended | These are documented as fetching pages so an assistant can answer or cite. Blocking them is what removes a site from those answers. |
| **Bulk corpus crawlers** | CCBot, Bytespider | These gather corpora rather than serving a live query. Blocking them is a licensing position with no effect on being cited at query time. |

Severity therefore follows what is lost:

- at least half the citation fetchers blocked at the root → **high defect**
- some citation fetchers blocked → **medium defect**
- only bulk corpus crawlers blocked → **low improvement**, and the action says plainly
  that no change is needed for citation

Without that split, a site blocking only Bytespider was reported identically to one
blocking every assistant — which the live benchmark showed happening on github.com.

Membership of either list is not a claim that a given assistant uses a given agent; it is
how the operators document them, and the finding says so. Each agent is evaluated against
the site's own rules, so custom `User-agent` blocks are honoured exactly as a real crawler
would honour them.

## The robots.txt parser

Rules are matched against the URL's **path and query**, per RFC 9309, with `*` and `$`
supported and the longest match winning (Allow breaking a tie). The standard library's
`urllib.robotparser` discards the query component, so the very common `Disallow: /?` —
used by google.com, wikipedia.org and many large sites to keep crawlers off parameterised
URLs — collapses into `Disallow: /` and appears to forbid the entire site. On the live
benchmark that produced an empty crawl of google.com and would have reported every AI
crawler as blocked on any site using that pattern.

## Why the edge/CDN check exists

robots.txt is only a request. A CDN or WAF can refuse an AI crawler's User-Agent at the
edge with a 403 even when robots.txt explicitly allows it, so the page is unreachable
regardless. The probe therefore compares two user-agents against the same URL. Crucially,
it requires an actual refusal **status** on a retried request: a network error alone is
recorded as inconclusive in `skipped_checks`, because one transient timeout must never
manufacture a critical finding.

## Mixed content means sub-resources

Only `src` on script/img/iframe/source/track/embed/audio/video and `href` on `<link>` are
counted. An `<a href="http://...">` pointing at another site is an ordinary outbound
link, not mixed content, and counting it was a false-positive source removed in v2.

## False-positive guards

- noindex is read from the parsed `<meta name="robots">` content attribute and the
  response header, never from a raw-string window that can span into unrelated markup.
- The canonical finding fires only when **no** successful page declares one, and is a
  defect only where duplicate/parameterised URLs were actually observed.
- Broken-link findings count only real 4xx/5xx. Links that produced no response at all
  are reported as an inconclusive skipped check, because a timeout is not a broken link.
- A robots-disallowed URL is recorded as blocked and never fetched, and the finding says
  explicitly that the audit therefore cannot judge what those URLs contain.
