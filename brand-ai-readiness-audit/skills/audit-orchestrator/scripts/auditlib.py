#!/usr/bin/env python3
"""
Shared, dependency-light crawl + cache library for the brand-ai-readiness-audit
marketplace.

The orchestrator crawls the target site ONCE and writes a cache directory. Every
sub-audit then reads that cache instead of re-fetching, which keeps the whole
audit deterministic, polite (one crawl), and well under the 5-minute budget.

Standard-library only for fetching/parsing (urllib + html.parser) so each skill
stays portable. Rendering (render-extraction-audit) optionally uses Playwright if
present, and degrades gracefully to a heuristic if it is not.

Cache layout:
  cache/
    meta.json            # crawl summary: site, robots, sitemap, per-page records
    pages/<slug>.html    # raw (pre-JS) HTML as fetched
    pages/<slug>.txt     # visible text extracted from raw HTML
    pages/<slug>.rendered.txt   # visible text after JS render (if available)
"""
import json
import os
import re
import sys
import time
import hashlib
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser

DEFAULT_UA = "brand-ai-readiness-audit/1.0 (+read-only auditor; respects robots.txt)"
TIMEOUT = 15
MAX_BYTES = 3_000_000  # never pull more than ~3MB per page


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #
def fetch(url, ua=DEFAULT_UA, method="GET"):
    """Fetch a URL. Returns dict(status, headers, body, final_url, error, elapsed_ms)."""
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read(MAX_BYTES)
            return {
                "status": r.status,
                "headers": {k.lower(): v for k, v in r.headers.items()},
                "body": raw.decode(r.headers.get_content_charset() or "utf-8", "replace"),
                "bytes": len(raw),
                "final_url": r.geturl(),
                "error": None,
                "elapsed_ms": int((time.time() - t0) * 1000),
            }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "headers": {k.lower(): v for k, v in (e.headers or {}).items()},
                "body": "", "bytes": 0, "final_url": url, "error": f"HTTP {e.code}",
                "elapsed_ms": int((time.time() - t0) * 1000)}
    except Exception as e:  # noqa: BLE001 - network errors are expected and reported
        return {"status": None, "headers": {}, "body": "", "bytes": 0,
                "final_url": url, "error": str(e), "elapsed_ms": int((time.time() - t0) * 1000)}


# --------------------------------------------------------------------------- #
# Minimal HTML parsing (stdlib)
# --------------------------------------------------------------------------- #
_SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}


class _Extractor(HTMLParser):
    """Pull visible text, links, headings, meta tags, JSON-LD blocks, img alts."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self._in_ldjson = False
        self._in_title = False
        self.text_parts = []
        self.links = []
        self.headings = []          # (level, text)
        self.metas = []             # dict of attrs
        self.ldjson = []            # raw string blocks
        self.imgs = []              # dict(src, alt)
        self.title = ""
        self.html_lang = None
        self.has_viewport = False
        self.canonical = None
        self.link_rels = []         # (rel, href)
        self._cur_heading = None
        self._cur_heading_buf = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in _SKIP_TEXT_TAGS:
            self._skip += 1
            if tag == "script" and a.get("type", "").lower() == "application/ld+json":
                self._in_ldjson = True
                self._skip -= 1  # we DO want the text inside ld+json
        if tag == "html" and a.get("lang"):
            self.html_lang = a.get("lang")
        if tag == "title":
            self._in_title = True
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag == "img":
            self.imgs.append({"src": a.get("src", ""), "alt": a.get("alt")})
        if tag == "meta":
            self.metas.append(a)
            if a.get("name", "").lower() == "viewport":
                self.has_viewport = True
        if tag == "link":
            rel = a.get("rel", "")
            self.link_rels.append((rel, a.get("href", "")))
            if "canonical" in rel.lower():
                self.canonical = a.get("href")
        m = re.fullmatch(r"h([1-6])", tag)
        if m:
            self._cur_heading = int(m.group(1))
            self._cur_heading_buf = []

    def handle_endtag(self, tag):
        if tag in _SKIP_TEXT_TAGS:
            if tag == "script" and self._in_ldjson:
                self._in_ldjson = False
            elif self._skip > 0:
                self._skip -= 1
        if tag == "title":
            self._in_title = False
        m = re.fullmatch(r"h([1-6])", tag)
        if m and self._cur_heading is not None:
            txt = " ".join("".join(self._cur_heading_buf).split())
            if txt:
                self.headings.append((self._cur_heading, txt))
            self._cur_heading = None
            self._cur_heading_buf = []

    def handle_data(self, data):
        if self._in_ldjson:
            self.ldjson.append(data)
            return
        if self._in_title:
            self.title += data
        if self._skip == 0:
            s = data.strip()
            if s:
                self.text_parts.append(s)
                if self._cur_heading is not None:
                    self._cur_heading_buf.append(data)

    @property
    def visible_text(self):
        return " ".join(self.text_parts)


def parse_html(html):
    p = _Extractor()
    try:
        p.feed(html)
    except Exception:  # noqa: BLE001 - tolerate malformed markup
        pass
    return p


# --------------------------------------------------------------------------- #
# URL helpers
# --------------------------------------------------------------------------- #
def normalize_site(site):
    if not re.match(r"^https?://", site):
        site = "https://" + site
    return site.rstrip("/")


def same_host(base, url):
    try:
        b, u = urllib.parse.urlparse(base), urllib.parse.urlparse(url)
        return (u.netloc or b.netloc).split(":")[0].lstrip("www.") == b.netloc.split(":")[0].lstrip("www.")
    except Exception:
        return False


def absolutize(base, href):
    return urllib.parse.urljoin(base, href)


def slug(url):
    return hashlib.sha1(url.encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Cache access (used by sub-audits)
# --------------------------------------------------------------------------- #
def load_meta(cache_dir):
    with open(os.path.join(cache_dir, "meta.json"), encoding="utf-8") as f:
        return json.load(f)


def read_page(cache_dir, page, kind="html"):
    ext = {"html": ".html", "text": ".txt", "rendered": ".rendered.txt"}[kind]
    path = os.path.join(cache_dir, "pages", page["slug"] + ext)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


# --------------------------------------------------------------------------- #
# Resource classification — every sub-audit should filter on these
# --------------------------------------------------------------------------- #
def is_html_page(page):
    """True if the crawled resource is an actual HTML document.

    Returns False for XML sitemaps, JSON feeds, images, PDFs, and other
    non-HTML resources that should not be evaluated by HTML-specific checks
    (viewport, H1, navigation, structured data, etc.).
    """
    if page.get("status") != 200:
        return False
    ct = page.get("content_type", "").lower()
    url = page.get("url", "").lower()
    # Explicit content-type exclusions
    if any(t in ct for t in ("xml", "/json", "image/", "/pdf")):
        return False
    # URL-based heuristic for missing or generic content-types
    if any(url.endswith(ext) for ext in (".xml", ".json", ".pdf", ".png", ".jpg", ".svg", ".gif")):
        return False
    if "sitemap" in url:
        return False
    return True


def classify_page_role(page, is_first=False):
    """Infer the page's functional role from URL patterns and content signals.

    Returns one of: homepage, article, product, documentation, about, contact,
    legal, utility, sitemap, non-html, content (default for unclassified HTML).
    """
    if not is_html_page(page):
        url = page.get("url", "").lower()
        if "sitemap" in url or "xml" in page.get("content_type", ""):
            return "sitemap"
        return "non-html"
    if is_first:
        return "homepage"
    url = page.get("url", "").lower()
    path = url.split("?")[0].split("#")[0]  # strip query/fragment
    for pattern, role in [
        ("/login", "utility"), ("/signin", "utility"), ("/signup", "utility"),
        ("/auth", "utility"), ("/register", "utility"), ("/account", "utility"),
        ("/privacy", "legal"), ("/terms", "legal"), ("/legal", "legal"),
        ("/cookie", "legal"), ("/policy", "legal"), ("/gdpr", "legal"),
        ("/about", "about"), ("/team", "about"), ("/company", "about"),
        ("/contact", "contact"), ("/support", "contact"),
        ("/blog", "article"), ("/news", "article"), ("/post", "article"),
        ("/article", "article"), ("/story", "article"),
        ("/product", "product"), ("/pricing", "product"), ("/plan", "product"),
        ("/shop", "product"), ("/store", "product"),
        ("/docs", "documentation"), ("/help", "documentation"),
        ("/faq", "documentation"), ("/guide", "documentation"),
    ]:
        if pattern in path:
            return role
    return "content"


def html_pages(meta):
    """Return only the HTML pages with status 200 from a meta.json structure.

    This is the standard page-selection filter every sub-audit should use
    instead of the raw meta["pages"] list.
    """
    return [p for p in meta.get("pages", []) if is_html_page(p)]


# --------------------------------------------------------------------------- #
# Finding helper — every sub-audit emits findings in this shape
# --------------------------------------------------------------------------- #
def finding(title, severity, evidence, action_summary, priority, category,
            checked=None, finding_type="defect", thin_html_sensitive=False):
    """severity/priority in {critical, high, medium, low}.
    finding_type: 'defect' (something is wrong) or 'improvement' (could be stronger).
    thin_html_sensitive: True if this finding may be a symptom of client-rendered content.
    `checked` = pages/items inspected."""
    f = {
        "title": title,
        "severity": severity,
        "category": category,
        "evidence": evidence,
        "suggested_action": {"summary": action_summary, "priority": priority},
        "finding_type": finding_type,
    }
    if checked is not None:
        f["checked"] = checked
    if thin_html_sensitive:
        f["_thin_html_sensitive"] = True
    return f


def emit(skill_id, findings):
    """Print the standard sub-audit envelope to stdout."""
    import io
    payload = json.dumps({"skill": skill_id, "findings": findings}, ensure_ascii=False, indent=2)
    # On Windows the default console encoding (cp1252) can't encode all Unicode characters
    # that appear in finding text (e.g. →, –). Write directly to a UTF-8 stdout wrapper.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(payload)
