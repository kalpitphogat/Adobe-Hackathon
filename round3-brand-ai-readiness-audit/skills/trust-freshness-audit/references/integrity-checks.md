# Content-integrity checks (trust stage)

Reachable, readable, well-marked-up content can still be untrustworthy. Three patterns
address the *machine* rather than the human and are increasingly detected and penalised by
assistants. They are trust findings: they do not stop a page being fetched or parsed, but
they change whether an assistant will repeat what it found.

| check_id | signal | severity | confidence |
|----------|--------|----------|------------|
| `trust.integrity.prompt_injection` | text phrased as an instruction to an AI reader (`ignore previous instructions`, `as an AI language model`, directives inside `<!-- -->` comments or hidden nodes) | critical | confirmed |
| `trust.integrity.cloaked_text` | ≥3 elements hidden via `display:none` / `visibility:hidden` / off-screen / `font-size:0` while still in the served HTML | medium | likely |
| `trust.integrity.invisible_unicode` | ≥5 zero-width or bidi-control code points (U+200B/200C/200D/FEFF, U+202A–202E, U+2066–2069) in the extracted text | medium | confirmed |

## Why each matters
- **Prompt injection**: retrieval assistants run injected-instruction detectors over fetched
  pages; a page that tries to steer the model is filtered out of answers rather than
  rewarded, so the directive removes the page from citations instead of shaping them.
- **Cloaking**: divergence between what a human sees and what a machine reads is a classic
  spam signal; it also means a fact a machine extracts may not be verifiable on the page.
- **Invisible Unicode**: extractors read the raw code points, so an invisible character
  inside a word breaks tokenisation and string matching even though the page looks correct.

## Detection is deliberately conservative
A false accusation of manipulation is worse than a miss, so: injection phrasing is narrow
(ordinary prose that merely mentions AI does not match — the trigger is *directive*
phrasing); cloaking requires several hidden elements (a lone `display:none` menu is normal);
and invisible-Unicode requires a run (≥5), not a single stray character. Every finding
quotes the offending snippet or count as evidence.

## Inputs
Raw served HTML per page (`raw_html_path` in the evidence bundle) for injection and
cloaking; the observed main text for invisible-Unicode. No network I/O; read-only.
