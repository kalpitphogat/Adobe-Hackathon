# Content-integrity check catalog

Assistants weight *trust*, not just reachability. Content built to manipulate the machine
— rather than serve the human — is increasingly detected and penalized, and can get a page
distrusted, down-ranked, or refused as a citation.

## Checks
| # | Check | Signal | Severity |
|---|-------|--------|----------|
| 1 | Prompt-injection / LLM directives | text phrased as an instruction to an AI reader, incl. inside `<!-- -->` comments or hidden nodes | critical |
| 2 | Visually-hidden text (cloaking) | >=3 elements hidden via `display:none` / `visibility:hidden` / off-screen / `font-size:0` | medium |
| 3 | Invisible / zero-width Unicode | >=5 zero-width or bidi-control code points in extracted text | medium |

## Patterns

**Injection phrasing** (narrow on purpose): `ignore (all) previous/prior/above
instructions`, `disregard the above/previous`, `as an ai language model`, `you are
chatgpt/claude/gemini/an ai`, `system prompt`, `prompt injection`, `do/don't
mention/reveal/disclose this`, `instructions/note/message to the ai/assistant/llm`, and
comment openers like `<!-- ai:` / `<!-- assistant`. Matched against the **raw HTML** so
comments and hidden nodes are included.

**Hidden text**: inline `style` declarations that remove an element from view —
`display:none`, `visibility:hidden`, `opacity:0`, `font-size:0`, `text-indent:-9999px`,
or `left/top:-9999px` off-screen positioning.

**Invisible Unicode**: U+200B/200C/200D (zero-width space/joiners), U+2060 (word joiner),
U+FEFF (BOM), U+202A–202E and U+2066–2069 (bidi override / isolate controls).

## Why it matters
- **Injection**: pages that address or try to steer the assistant are a safety red flag;
  modern assistants filter them out rather than repeat them.
- **Cloaking**: divergence between what humans and machines see is a classic spam signal;
  it also means the "fact" a machine extracts may not be one a human can verify on the page.
- **Zero-width/bidi**: invisible characters ride along into the machine's text and can
  break extraction or hide content that a human reviewer would never see.

## False-positive guards
- Injection phrasing is specific enough that ordinary prose about AI ("we use AI to…")
  does not match; the trigger is *directive* phrasing.
- Cloaking requires several hidden elements (a lone `display:none` menu is normal).
- Zero-width requires a run (>=5), not a single stray character.
- All findings quote the offending snippet / counts as evidence, so a reviewer can confirm.
