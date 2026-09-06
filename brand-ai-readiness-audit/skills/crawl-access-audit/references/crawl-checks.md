# Crawl & access check catalog

The three gates (Round-2 appendix A): a crawler must be **let in**, able to **read**
the page, and able to **pick out the fact**. This skill owns gate 1.

| # | Check | Signal | Severity logic |
|---|-------|--------|----------------|
| 1 | robots.txt present | GET `/robots.txt` != 200 | low (slows discovery, not fatal) |
| 2 | AI crawlers allowed | `Disallow: /` for GPTBot/OAI-SearchBot/ClaudeBot/PerplexityBot/Google-Extended/etc. | critical if a major citation bot is blocked, else high |
| 3 | XML sitemap | no `Sitemap:` line and `/sitemap.xml` not a valid urlset | medium |
| 4 | noindex | meta robots or `X-Robots-Tag` contains `noindex` | critical on homepage, else high |
| 5 | Disallowed public pages | robots.txt Disallow matches a sampled URL | high |
| 6 | HTTP errors | sampled URL returns 4xx/5xx | high |
| 7 | canonical | no `rel=canonical` on any successful page | low |
| 8 | HTTPS | base URL is `http://` | high |
| 9 | broken internal links | HEAD/GET sweep of up to 15 homepage links returns 4xx/5xx/none | medium |
| 10 | mixed content | http:// sub-resources referenced from an https page | medium |
| 11 | edge/CDN AI-bot block | homepage serves a browser UA (200) but refuses the GPTBot UA (403/challenge) | critical |
| 12 | llms.txt | no `/llms.txt` guidance file (proactive AI-guidance signal) | low |

## Why the edge/CDN check matters (beyond robots.txt)
robots.txt is only a *request*. A CDN or WAF (Cloudflare, Akamai, Vercel bot-management)
can refuse an AI crawler's User-Agent at the edge with a 403 or a JS challenge even when
robots.txt explicitly allows it — so the page is unreachable to the assistant regardless.
This skill probes the homepage twice, once as a normal browser and once as `GPTBot`, and
flags a block that only the bot UA hits. This is a common, invisible cause of "we allow
the bot but it still never cites us."

## AI crawler user-agents checked
GPTBot, OAI-SearchBot, ChatGPT-User (OpenAI); ClaudeBot, Claude-Web, anthropic-ai
(Anthropic); PerplexityBot; Google-Extended (Gemini/Vertex grounding); Applebot-Extended;
CCBot (Common Crawl, a training/discovery feeder); Bytespider.

Each bot is evaluated against the site's own robots.txt rules using a standard robots
parser, so custom `User-agent` blocks are honored exactly as a real crawler would.

## Why these matter
robots and noindex are absolute gates: a blocked or noindexed page is excluded outright,
regardless of content quality. Sitemaps and canonicals are about *efficient, unambiguous*
discovery — they raise the odds every page is found and that duplicates consolidate onto
one authoritative URL. HTTPS is a baseline trust signal.

## False-positive guards
- Bot-block finding lists the exact disallowed agents as evidence.
- noindex is confirmed from the actual `<meta name="robots">` content or response header,
  not inferred.
- canonical finding fires only when **no** successful page declares one (sitewide), to
  avoid flagging intentional cross-canonical setups on a single page.
