#!/usr/bin/env python3
"""
Render an audit report (the JSON emitted by run_audit.py) as a self-contained,
human-readable HTML page — so a non-expert can act on the findings without reading JSON.

  python render_report.py <report.json> [out.html]      # -> HTML file
  # or import render(report_dict) -> html string

No external dependencies; the page is a single inlined HTML file, light/dark aware.
"""
import html as _html
import json
import sys

SEV_COLOR = {"critical": "#b4232a", "high": "#c8791b", "medium": "#8a7d16", "low": "#5b6b7a"}
SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _esc(s):
    return _html.escape(str(s), quote=True)


def render(report):
    site = _esc(report.get("site", "?"))
    when = _esc(report.get("audited_at", "?"))
    scope = report.get("scope", {})
    s = report.get("summary", {})
    findings = sorted(report.get("findings", []),
                      key=lambda f: SEV_ORDER.get(f.get("severity"), 9))

    def chip(label, n, color):
        return (f'<span class="chip" style="--c:{color}">'
                f'<b>{n}</b> {label}</span>')

    chips = "".join([
        chip("critical", s.get("critical", 0), SEV_COLOR["critical"]),
        chip("high", s.get("high", 0), SEV_COLOR["high"]),
        chip("medium", s.get("medium", 0), SEV_COLOR["medium"]),
        chip("low", s.get("low", 0), SEV_COLOR["low"]),
    ])
    bydim = s.get("by_dimension", {})
    dim_line = ""
    if bydim:
        dim_line = (f'<div class="dims">Discoverability: '
                    f'<b>{bydim.get("discoverability", 0)}</b> &nbsp;·&nbsp; '
                    f'Engagement: <b>{bydim.get("engagement", 0)}</b></div>')

    rows = []
    for f in findings:
        sev = f.get("severity", "low")
        color = SEV_COLOR.get(sev, "#5b6b7a")
        checked = f.get("checked")
        checked_html = f'<span class="checked">inspected {checked}</span>' if checked is not None else ""
        act = f.get("suggested_action", {})
        rows.append(f"""
      <details class="finding" open>
        <summary>
          <span class="sev" style="--c:{color}">{_esc(sev)}</span>
          <span class="ftitle">{_esc(f.get('title',''))}</span>
          <span class="meta">{_esc(f.get('dimension',''))} · {_esc(f.get('skill',''))} · {_esc(f.get('id',''))}</span>
        </summary>
        <div class="body">
          <p class="evidence"><b>Evidence.</b> {_esc(f.get('evidence',''))} {checked_html}</p>
          <p class="action"><b>Fix ({_esc(act.get('priority',''))}).</b> {_esc(act.get('summary',''))}</p>
        </div>
      </details>""")

    if not rows:
        rows = ['<p class="none">No findings — the site passed every check in this audit.</p>']

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI-Readiness Audit — {site}</title>
<style>
  :root {{ --bg:#f7f7f5; --card:#fff; --fg:#1b1b1b; --muted:#6b6b6b; --line:#e3e3e0; }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{ --bg:#16171a; --card:#1e2024; --fg:#e9e9ea; --muted:#9aa0a6; --line:#2c2f34; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
         font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }}
  .wrap {{ max-width:860px; margin:0 auto; padding:32px 20px 64px; }}
  header h1 {{ font-size:22px; margin:0 0 4px; }}
  header .sub {{ color:var(--muted); font-size:13px; margin-bottom:18px; word-break:break-all; }}
  .summary {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
             padding:18px 20px; margin-bottom:8px; }}
  .total {{ font-size:15px; margin:0 0 12px; }}
  .chip {{ display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px;
          margin:0 8px 6px 0; color:#fff; background:var(--c); }}
  .dims {{ color:var(--muted); font-size:13px; margin-top:6px; }}
  .scope {{ color:var(--muted); font-size:12px; margin:6px 0 26px; }}
  .finding {{ background:var(--card); border:1px solid var(--line); border-left:4px solid var(--line);
             border-radius:10px; margin:10px 0; overflow:hidden; }}
  .finding summary {{ cursor:pointer; padding:12px 16px; list-style:none;
                     display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; }}
  .finding summary::-webkit-details-marker {{ display:none; }}
  .sev {{ background:var(--c); color:#fff; font-size:11px; text-transform:uppercase;
         letter-spacing:.03em; padding:3px 8px; border-radius:6px; font-weight:700; }}
  .ftitle {{ font-weight:600; flex:1 1 260px; }}
  .meta {{ color:var(--muted); font-size:12px; }}
  .body {{ padding:0 16px 14px 16px; }}
  .body p {{ margin:8px 0; }}
  .evidence {{ color:var(--fg); }}
  .action {{ color:var(--fg); background:rgba(127,127,127,.08); padding:8px 10px; border-radius:8px; }}
  .checked {{ color:var(--muted); font-size:12px; }}
  .none {{ color:var(--muted); }}
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
  <div class="scope">
    Pages crawled: {scope.get('pages_crawled','?')} ·
    Render used: {str(scope.get('render_used', False)).lower()} ·
    robots.txt respected: {str(scope.get('robots_respected', True)).lower()}
  </div>
  {''.join(rows)}
  <footer>Generated by the brand-ai-readiness-audit marketplace · recommend-only, read-only audit</footer>
</div></body></html>"""


def main():
    if len(sys.argv) < 2:
        print("usage: render_report.py <report.json> [out.html]", file=sys.stderr)
        return 2
    report = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2] if len(sys.argv) > 2 else None
    doc = render(report)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(doc)
        print(f"wrote {out}", file=sys.stderr)
    else:
        print(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
