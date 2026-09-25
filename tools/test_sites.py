"""Build and serve five small test sites that isolate how the browser pass behaves.

  python tools/test_sites.py OUT_DIR          # writes the sites, serves them on 127.0.0.1:8601-8605

  8601 tiny_links    3 pages under 50 words, 2 internal + 4 social links (the false-positive case)
  8602 tiny_nolinks  1 page under 50 words, no links
  8603 spa           empty <div id="root">; JavaScript adds 8 internal links and ~320 words
  8604 normal        6 server-rendered pages, 6 internal nav links, 4 social links
  8605 partial_js    server-rendered text with 1 internal link; JavaScript adds 9 nav links

Audit them with --allow-private-hosts (an existing engine flag for sites you host yourself).
Used by SITE_MATRIX.md, with tools/site_matrix.py.
"""
import functools
import http.server
import sys
import threading
from pathlib import Path

TEXT = ("Harbor Tools has made durable hand tools in Leeds since 1987. Every hammer, chisel and "
        "plane is forged from recycled steel and carries a ten year warranty. We sell to trade "
        "customers in twelve countries and publish our test results for each product line. ")
SOCIAL = ('<footer><a href="https://twitter.com/x">Twitter</a> <a href="https://github.com/x">GitHub</a> '
          '<a href="https://www.linkedin.com/x">LinkedIn</a> <a href="https://www.youtube.com/x">YouTube</a></footer>')


def para(words: int = 320) -> str:
    out = []
    while len(" ".join(out).split()) < words:
        out.append(TEXT)
    return f"<p>{' '.join(out)}</p>"


def page(title: str, body: str) -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title>'
            f'<meta name="description" content="{title} - Harbor Tools"></head><body>{body}</body></html>')


def sites() -> dict:
    s = {}
    s["tiny_links"] = {
        "index.html": page("Harbor Tools", '<main><h1>Harbor Tools</h1><p>Hand tools from Leeds. Ten year warranty.</p>'
                           '<a href="/about.html">About</a> <a href="/contact.html">Contact</a></main>' + SOCIAL),
        "about.html": page("About Harbor Tools", '<main><h1>About</h1><p>Family firm since 1987.</p><a href="/">Home</a></main>' + SOCIAL),
        "contact.html": page("Contact Harbor Tools", '<main><h1>Contact</h1><p>Call 0113 000 0000.</p><a href="/">Home</a></main>' + SOCIAL),
    }
    s["tiny_nolinks"] = {"index.html": page("Harbor Tools", "<main><h1>Harbor Tools</h1><p>Hand tools from Leeds. "
                                            "Ten year warranty. Coming soon.</p></main>")}
    routes = {"/": "Home", "/products": "Products", "/about": "About", "/pricing": "Pricing",
              "/contact": "Contact", "/blog": "Blog", "/careers": "Careers", "/faq": "FAQ"}
    nav = " ".join(f'<a href="{h}">{t}</a>' for h, t in routes.items())
    app_js = ("document.getElementById('root').innerHTML=" +
              repr(f"<header><nav>{nav}</nav></header><main><h1>Harbor Tools</h1>{para()}</main>") + ";")
    shell = page("Harbor Tools", '<div id="root"></div><script src="/app.js"></script>')
    s["spa"] = {"index.html": shell, "app.js": app_js,
                **{f"{r.strip('/')}/index.html": shell for r in routes if r != "/"}}
    ssr_nav = ('<header><nav><a href="/">Home</a> <a href="/products.html">Products</a> <a href="/about.html">About</a> '
               '<a href="/pricing.html">Pricing</a> <a href="/contact.html">Contact</a> <a href="/faq.html">FAQ</a></nav></header>')
    s["normal"] = {f"{n}.html": page(f"{n.title()} - Harbor Tools", f"{ssr_nav}<main><h1>{n.title()}</h1>{para()}</main>{SOCIAL}")
                   for n in ["index", "products", "about", "pricing", "contact", "faq"]}
    js_nav = ('document.querySelector("header").innerHTML="<nav>"+["/","/products.html","/about.html","/pricing.html",'
              '"/contact.html","/faq.html","/blog.html","/careers.html","/support.html"]'
              '.map(h=>`<a href=\\"${h}\\">${h}</a>`).join(" ")+"</nav>";')
    names = ["index", "products", "about", "pricing", "contact", "faq", "blog", "careers", "support"]
    s["partial_js"] = {f"{n}.html": page(f"{n.title()} - Harbor Tools", f'<header></header><main><h1>{n.title()}</h1>{para()}'
                                         f'<a href="/products.html">Products</a></main><script src="/nav.js"></script>')
                       for n in names}
    s["partial_js"]["nav.js"] = js_nav
    return s


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1]).resolve()
    servers = []
    for port, (name, files) in enumerate(sites().items(), start=8601):
        for rel, body in files.items():
            path = root / name / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        (root / name / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root / name))
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        print(f"{name:<13} http://127.0.0.1:{port}/")
    print("serving; Ctrl+C to stop")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
