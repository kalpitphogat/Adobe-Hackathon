# Content-integrity check catalog

Consumers weigh *trust*, not just reachability. Content built to steer the machine rather
than serve the human can get a page distrusted or refused as a citation.

## Checks

| # | Check | Trigger | Band |
|---|-------|---------|------|
| 1 | Text addressed to an AI reader | a directive-phrased match in the raw HTML, including inside comments | critical (defect, material) |
| 2 | Hidden non-UI text | see the gate below | medium (defect, confidence medium) |
| 3 | Invisible / bidi Unicode | ≥5 zero-width or bidi-control code points in the extracted text | medium (defect, material) |

## The hidden-text gate

The presence of `display:none` is **never** on its own treated as cloaking. Hiding
elements is how ordinary interfaces work.

**Step 1 — classify every hidden container.** The parser tracks element nesting, so it
knows which text sits inside a hidden element. Each hidden container's `class`, `id`,
`role` and `aria-hidden` are checked for UI markers: menu, nav, drawer, dropdown, modal,
dialog, popover, tooltip, accordion, collapse, tab / tabpanel, carousel, slide, overlay,
offcanvas, sr-only, screen-reader, visually-hidden, skip-link, a11y, aria, toggle, close,
backdrop, cookie, consent, banner, search, filter, lazy, placeholder, spinner, loader,
template, print-only, noscript. Text inside those is counted separately and **never
reported**.

**Step 2 — require substance.** What remains must satisfy the ratio gate — at least 25%
as much hidden text as visible text — **and** one of:
- 150+ hidden characters, or
- 100+ hidden characters spread across 3+ separate hidden non-UI blocks (a repeated
  structure is a pattern, not an accident), or
- 2000+ hidden characters outright, at any ratio.

The ratio gate does most of the work: a small hidden template string on a large page is
suppressed by it, while a page whose invisible text rivals its visible text is noticed at
any size.

**Step 3 — say what was not established.** The audit executes no CSS and no JavaScript,
so an element may still become visible through an external stylesheet rule or an
interaction. The finding states this and asks the owner to confirm, rather than asserting
cloaking.

Where every hidden block on a site turned out to be legitimate UI, that outcome is
recorded in `skipped_checks` with the character count — visible reasoning, not a silent
drop.

## Patterns

**Quoted and code-formatted content is excluded.** The search runs against the page with
`<code>`, `<pre>`, `<blockquote>`, `<samp>` and `<kbd>` regions removed, so only text the
page asserts in its own voice can raise the finding. An article that quotes an
AI-directed note, or shows one as a code sample, is writing *about* the technique rather
than using it; that outcome is recorded in `skipped_checks` instead. This was a real
false positive found during the live generalisation run, on a blog post quoting another
project's security policy.

**Injection phrasing** (narrow on purpose): `ignore (all) previous/prior/above
instructions`; `disregard the above/previous/earlier instructions|prompt|text`; `as an ai
language model`; `you are chatgpt/claude/gemini/an ai assistant/a large language model`;
`do/don't mention|reveal|disclose this`; `instructions|note|message to|for the
ai|assistant|llm|chatbot|model`; comment openers `<!-- ai:`, `<!-- llm`, `<!-- assistant`,
`<!-- gpt`. Matched against the raw HTML so comments and hidden nodes are included. The
bare terms "system prompt" and "prompt injection" were removed from the pattern set in
v2: an article *about* prompt injection is not an attack, and matching them produced
false positives on security writing.

**Hidden styles**: inline `display:none`, `visibility:hidden`, `opacity:0`,
`font-size:0`, `text-indent:-9999px`, `left`/`top:-9999px`, and the `hidden` attribute.

**Invisible Unicode**: U+200B/200C/200D (zero-width space and joiners), U+2060 (word
joiner), U+FEFF (BOM), U+202A–202E and U+2066–2069 (bidi override and isolate controls).

## Why each matters

- **Injection**: a page that addresses the assistant is a safety signal; assistants
  increasingly filter such pages rather than repeat them. This is the one check here whose
  intent is unambiguous, which is why it is the only critical one.
- **Hidden text**: a divergence between what humans and machines see means the fact a
  machine extracts may be one no reader can verify on the page.
- **Invisible Unicode**: these ride along into whatever a machine extracts, where they can
  split words for a matcher or reorder displayed text. The finding notes they are
  frequently a copy-paste or CMS artefact rather than deliberate — the fix is the same
  either way, but the accusation is not.

## False-positive guards

- Injection phrasing is directive-specific, so ordinary prose about AI ("we use AI to…")
  does not match.
- Hidden text passes the three-step gate above before anything is reported.
- Zero-width requires a run of five, not a single stray character.
- Every finding quotes the matched snippet or the measured counts, so a reviewer can
  confirm or dismiss it without re-running the audit.
