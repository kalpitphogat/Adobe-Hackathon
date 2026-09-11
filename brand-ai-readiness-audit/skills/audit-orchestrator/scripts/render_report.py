#!/usr/bin/env python3
"""
Render an audit report (the JSON emitted by run_audit.py) as a self-contained,
human-readable HTML page, so a non-expert can act on the findings without reading
JSON.

  python render_report.py <report.json> [out.html]      # -> HTML file
  # or import render(report_dict) -> html string

The page keeps the report's own distinctions visible rather than flattening them:
defects are separated from optional improvements, each finding shows what was
OBSERVED apart from what it may IMPLY, and the scope panel states exactly what
was and was not inspected.

No external dependencies; a single inlined HTML file, light/dark aware.
"""
import html as _html
import json
import sys

SEV_COLOR = {"critical": "#b4232a", "high": "#c8791b", "medium": "#8a7d16", "low": "#5b6b7a"}
SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _esc(s):
    return _html.escape(str(s), quote=True)


def _finding_card(f):
    sev = f.get("severity", "low")
    color = SEV_COLOR.get(sev, "#5b6b7a")
    det = f.get("evidence_detail") or {}
    obs = det.get("observation") or f.get("evidence", "")
    interp = det.get("interpretation", "")
    nv = det.get("not_verified", "")
    act = f.get("suggested_action", {})

    bits = []
    if f.get("page_role"):
        bits.append(f"page role: {f['page_role']}")
    if f.get("checked") is not None:
        bits.append(f"inspected {f['checked']} {f.get('checked_unit', 'items')}")
    if f.get("confidence"):
        bits.append(f"confidence: {f['confidence']}")
    if f.get("severity_capped_from"):
        bits.append(f"reduced from {f['severity_capped_from']} ({f['severity_cap_reason']})")
    meta_line = (f'<p class="tags">{_esc(" · ".join(bits))}</p>' if bits else "")

    interp_html = f'<p class="interp"><b>What it may mean.</b> {_esc(interp)}</p>' if interp else ""
    nv_html = (f'<p class="nv"><b>Not verified by this audit.</b> {_esc(nv)}</p>' if nv else "")

    return f"""
      <details class="finding" style="--c:{color}" open>
        <summary>
          <span class="sev" style="--c:{color}">{_esc(sev)}</span>
          <span class="ftitle">{_esc(f.get('title', ''))}</span>
          <span class="meta">{_esc(f.get('dimension', ''))} · {_esc(f.get('skill', ''))}
            · {_esc(f.get('id', ''))}</span>
        </summary>
        <div class="body">
          <p class="evidence"><b>Observed.</b> {_esc(obs)}</p>
          {interp_html}
          {nv_html}
          <p class="action"><b>Do this.</b> {_esc(act.get('summary', ''))}</p>
          {meta_line}
        </div>
      </details>"""


def render(report):
    site = _esc(report.get("site", "?"))
    when = _esc(report.get("audited_at", "?"))
    scope = report.get("scope", {}) or {}
    s = report.get("summary", {}) or {}
    findings = report.get("findings", []) or []

    if report.get("status") == "failed":
        fail = report.get("failure", {}) or {}
        body = (f'<div class="failed"><h2>No audit was produced</h2>'
                f'<p><b>{_esc(fail.get("reason", "unknown"))}</b></p>'
                f'<p>{_esc(fail.get("detail", ""))}</p></div>')
    else:
        defects = sorted([f for f in findings if f.get("finding_type", "defect") == "defect"],
                         key=lambda f: SEV_ORDER.get(f.get("severity"), 9))
        improvements = sorted([f for f in findings if f.get("finding_type") == "improvement"],
                              key=lambda f: SEV_ORDER.get(f.get("severity"), 9))
        sections = []
        if defects:
            sections.append('<h2>Defects <span class="hint">evidence of an existing '
                            'problem</span></h2>' + "".join(_finding_card(f) for f in defects))
        if improvements:
            sections.append('<h2>Improvements <span class="hint">optional, no problem '
                            'evidenced</span></h2>'
                            + "".join(_finding_card(f) for f in improvements))
        if not sections:
            sections.append('<p class="none">No finding met the evidence bar in this audit. '
                            'See the scope panel for what was inspected.</p>')
        body = "".join(sections)

    def chip(label, n, color):
        return f'<span class="chip" style="--c:{color}"><b>{n}</b> {label}</span>'

    chips = "".join(chip(k, s.get(k, 0), SEV_COLOR[k])
                    for k in ("critical", "high", "medium", "low"))
    bytype = s.get("by_type", {}) or {}
    bydim = s.get("by_dimension", {}) or {}
    lines = []
    if bytype:
        lines.append(f'Defects: <b>{bytype.get("defects", 0)}</b> &nbsp;·&nbsp; '
                     f'Improvements: <b>{bytype.get("improvements", 0)}</b>')
    if bydim:
        lines.append(f'Discoverability: <b>{bydim.get("discoverability", 0)}</b> &nbsp;·&nbsp; '
                     f'Engagement: <b>{bydim.get("engagement", 0)}</b>')
    dim_line = "".join(f'<div class="dims">{ln}</div>' for ln in lines)

    roles = scope.get("page_roles") or {}
    kinds = scope.get("resource_kinds") or {}
    skipped = scope.get("checks_skipped") or []
    skipped_html = ""
    if skipped:
        items = "".join(f"<li><b>{_esc(c.get('check', ''))}</b> — {_esc(c.get('reason', ''))}</li>"
                        for c in skipped)
        skipped_html = (f'<details class="skipped"><summary>{len(skipped)} check(s) did not '
                        f'run, and why</summary><ul>{items}</ul></details>')
    merged = scope.get("findings_merged") or []
    merged_html = ""
    if merged:
        items = "".join(f"<li>{_esc(m.get('title', ''))} — merged into "
                        f"{_esc(m.get('merged_into', ''))}</li>" for m in merged)
        merged_html = (f'<details class="skipped"><summary>{len(merged)} finding(s) merged as '
                       f'duplicates</summary><ul>{items}</ul></details>')

    scope_html = f"""
  <div class="scope">
    <div><b>{scope.get('html_pages_analyzed', 0)}</b> HTML pages analysed of
      <b>{scope.get('pages_crawled', 0)}</b> resources crawled
      ({scope.get('non_html_resources', 0)} non-HTML).
      Crawl status: {_esc(scope.get('crawl_status', 'n/a'))}.
      Rendering used: {str(scope.get('render_used', False)).lower()}.
      robots.txt respected: {str(scope.get('robots_respected', True)).lower()}.</div>
    {f'<div>Resource kinds: {_esc(", ".join(f"{k} {v}" for k, v in kinds.items()))}</div>' if kinds else ''}
    {f'<div>Page roles: {_esc(", ".join(f"{k} {v}" for k, v in roles.items()))}</div>' if roles else ''}
    <div class="note">{_esc(scope.get('note', ''))}</div>
    {skipped_html}
    {merged_html}
  </div>"""

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI-Readiness Audit — {site}</title>
<style>
  :root {{ --bg:#f7f7f5; --card:#fff; --fg:#1b1b1b; --muted:#6b6b6b; --line:#e3e3e0; }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{ --bg:#16171a; --card:#1e2024; --fg:#e9e9ea;
      --muted:#9aa0a6; --line:#2c2f34; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
         font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }}
  .wrap {{ max-width:880px; margin:0 auto; padding-block:32px 64px; padding-left:20px;
          padding-right:20px; }}
  header h1 {{ font-size:22px; margin:0 0 4px; }}
  header .sub {{ color:var(--muted); font-size:13px; margin-bottom:18px; word-break:break-all; }}
  h2 {{ font-size:16px; margin:28px 0 6px; }}
  h2 .hint {{ font-weight:400; font-size:12px; color:var(--muted); }}
  .summary {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
             padding:18px 20px; margin-bottom:8px; }}
  .total {{ font-size:15px; margin:0 0 12px; }}
  .chip {{ display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px;
          margin:0 8px 6px 0; color:#fff; background:var(--c); }}
  .dims {{ color:var(--muted); font-size:13px; margin-top:4px; }}
  .scope {{ color:var(--muted); font-size:12px; margin:8px 0 8px; background:var(--card);
           border:1px solid var(--line); border-radius:10px; padding:12px 14px; }}
  .scope div {{ margin:3px 0; }}
  .scope .note {{ font-style:italic; }}
  .skipped {{ margin-top:8px; }}
  .skipped summary {{ cursor:pointer; }}
  .skipped ul {{ margin:6px 0 0; padding-left:18px; }}
  .finding {{ background:var(--card); border:1px solid var(--line);
             border-left:4px solid var(--c); border-radius:10px; margin:10px 0;
             overflow:hidden; }}
  .finding summary {{ cursor:pointer; padding:12px 16px; list-style:none;
                     display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; }}
  .finding summary::-webkit-details-marker {{ display:none; }}
  .sev {{ background:var(--c); color:#fff; font-size:11px; text-transform:uppercase;
         letter-spacing:.03em; padding:3px 8px; border-radius:6px; font-weight:700; }}
  .ftitle {{ font-weight:600; flex:1 1 260px; }}
  .meta {{ color:var(--muted); font-size:12px; }}
  .body {{ padding:0 16px 14px 16px; }}
  .body p {{ margin:8px 0; }}
  .interp, .nv {{ color:var(--muted); }}
  .action {{ background:rgba(127,127,127,.08); padding:8px 10px; border-radius:8px; }}
  .tags {{ color:var(--muted); font-size:12px; }}
  .none, .failed {{ color:var(--muted); }}
  footer {{ margin-top:28px; color:var(--muted); font-size:12px; text-align:center; }}
</style></head>
<body><div class="wrap">
  <header>
    <h1>Brand AI-Readiness Audit</h1>
    <div class="sub">{site} · audited {when}</div>
  </header>
  <div class="summary">
    <p class="total"><b>{s.get('total_findings', 0)}</b> findings</p>
    {chips}
    {dim_line}
  </div>
  {scope_html}
  {body}
  <footer>Generated by the brand-ai-readiness-audit marketplace · read-only,
    recommend-only. No score is reported because no scoring formula is implemented.</footer>
</div></body></html>"""


def main():
    if len(sys.argv) < 2:
        print("usage: render_report.py <report.json> [out.html]", file=sys.stderr)
        return 2
    with open(sys.argv[1], encoding="utf-8") as f:
        report = json.load(f)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    doc = render(report)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(doc)
        print(f"wrote {out}", file=sys.stderr)
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
