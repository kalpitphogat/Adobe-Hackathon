# Bot taxonomy: why blocking a crawler is sometimes correct

## The problem with a flat list

Most AI-readiness tools carry a list of AI crawler user agents and report every
blocked one as a defect. That produces a confident, wrong finding on any site
that has made a deliberate content-licensing decision — which is a large and
growing share of the web, and increasingly the considered position rather than
the careless one.

The useful question is not "is this bot blocked" but **"what does blocking this
bot cost?"** Those are different questions with different answers per bot.

## Three categories

### retrieval — blocking costs visibility — CRITICAL

Fetches pages at answer time to ground or cite a response. Blocking one removes
the brand from that assistant's answers entirely. No amount of on-page quality
compensates, because the page is never fetched.

Examples: OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-User,
Claude-SearchBot, Googlebot, Bingbot, Applebot.

### training — blocking costs nothing at retrieval time — INFO

Collects content for model training corpora. Training-corpus collection and
answer-time retrieval are **separate pipelines with separate user-agent
tokens**. Blocking GPTBot does not remove a site from ChatGPT search results,
which use OAI-SearchBot. Blocking ClaudeBot does not affect retrieval in Claude,
which uses Claude-User and Claude-SearchBot.

Examples: GPTBot, ClaudeBot, CCBot, anthropic-ai, cohere-ai, Bytespider.

We report these at `info`, as an observation, and never escalate. It is a
content-licensing decision, and it belongs to the site owner. We surface it only
so it is visible alongside everything else — and, when a retrieval bot is also
blocked, so the reader can see which of the two is actually costing them
something.

### dual_purpose — contested — MEDIUM

The vendor documentation ties the token to more than one use, or the vendor has
changed its stated scope. Blocking may or may not cost retrieval visibility.

Examples: Google-Extended, Applebot-Extended, Meta-ExternalAgent, FacebookBot,
PetalBot.

Google-Extended is the clearest case. It is not a crawler in its own right: it
modifies how Googlebot-crawled content may be used, so blocking it does not
remove a site from Google Search, but it can affect AI-surface grounding. That
is a trade-off a site may have chosen deliberately. We report it at `medium`
with the contestedness stated **in the finding text**, so the reader can weigh
it rather than take our word for it.

## Crawl-delay

`Crawl-delay` is **not part of RFC 9309**. Bing and Yandex honour it, Google
documents that Googlebot ignores it and that crawl rate is managed in Search
Console instead, and the AI retrieval crawlers have largely not documented their
behaviour.

So a site that set `Crawl-delay` for Bingbot has made a supported, effective
choice and **has not made a mistake**. `reach.robots.crawl_delay_excessive`
therefore fires only when the directive reaches an agent we classify as
retrieval-relevant, and the finding text names which crawlers honour it.

## The snapshot

`ai-bots.json` carries a `snapshot_date` and the upstream commit of
`ai-robots-txt/ai.robots.txt` it was cross-checked against. Both are printed in
every report.

Bot names churn: vendors add tokens, rename them, and split one into two. A
dated list that says how old it is beats a confident list that does not. The
list is **never fetched at runtime** — an audit that reaches out to a
third-party list mid-run is neither deterministic nor self-contained, and the
handout requires the marketplace to resolve with no external service.

The three-way classification is **ours**, not upstream's. Upstream lists bots to
block; we need to know what blocking each one costs, which is a different
question and the reason a flat list produces bad findings.
