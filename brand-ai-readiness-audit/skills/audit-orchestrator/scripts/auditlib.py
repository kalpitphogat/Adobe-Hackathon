#!/usr/bin/env python3
"""
Shared crawl + classification + evidence library for the brand-ai-readiness-audit
marketplace.

The orchestrator crawls the target site ONCE and writes a cache directory. Every
sub-audit then reads that cache instead of re-fetching, which keeps the whole
audit deterministic, polite (one crawl), and well under the 5-minute budget.

Standard-library only for fetching/parsing (urllib + html.parser) so each skill
stays portable. Rendering (render-extraction-audit) optionally uses Playwright if
present, and degrades gracefully to a documented audit limitation if it is not.

This module owns the three things every sub-audit must agree on:

  1. RESOURCE CLASSIFICATION - what kind of thing did we actually fetch?
     HTML-specific checks must never run against XML sitemaps, JSON APIs,
     images, or PDFs. See `classify_resource`.
  2. PAGE-ROLE CLASSIFICATION - what is this HTML page for? Role decides which
     checks are even relevant. "unknown" is a valid, preferred answer when the
     evidence is weak. See `classify_page_role`.
  3. EVIDENCE DISCIPLINE - every finding separates what was directly OBSERVED
     from what that observation may IMPLY and why it is a CONCLUSION for this
     page. Severity is then capped by confidence and materiality. See `finding`
     and `calibrate`.

Cache layout:
  cache/
    meta.json            # crawl summary: site, robots, sitemap, per-resource records
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
import urllib.error
from html.parser import HTMLParser

DEFAULT_UA = "brand-ai-readiness-audit/2.0 (+read-only auditor; respects robots.txt)"
TIMEOUT = 15
MAX_BYTES = 3_000_000   # never pull more than ~3MB from a single response
MIN_DELAY_S = 0.25      # politeness floor between requests to the same host


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #
_last_request_at = [0.0]


def _throttle(delay):
    """Sleep so consecutive requests are at least `delay` seconds apart."""
    wait = (_last_request_at[0] + max(delay, 0.0)) - time.time()
    if wait > 0:
        time.sleep(wait)
    _last_request_at[0] = time.time()


def fetch(url, ua=DEFAULT_UA, method="GET", delay=MIN_DELAY_S, timeout=TIMEOUT):
    """Fetch a URL politely.

    Returns dict(status, headers, body, bytes, final_url, error, elapsed_ms,
    truncated). Never raises: network problems come back as `error` so one bad
    resource cannot terminate a crawl or an audit run.
    """
    _throttle(delay)
    t0 = time.time()
    try:
        # Request() itself raises on a malformed URL (a site can publish one in a
        # robots.txt Sitemap: line or a link), so it is constructed inside the try.
        req = urllib.request.Request(url, method=method, headers={
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(MAX_BYTES)
            charset = None
            try:
                charset = r.headers.get_content_charset()
            except Exception:
                pass
            return {
                "status": r.status,
                "headers": {k.lower(): v for k, v in r.headers.items()},
                "body": raw.decode(charset or "utf-8", "replace"),
                "bytes": len(raw),
                "truncated": len(raw) >= MAX_BYTES,
                "final_url": r.geturl(),
                "error": None,
                "elapsed_ms": int((time.time() - t0) * 1000),
            }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read(MAX_BYTES).decode("utf-8", "replace")
        except Exception:
            pass
        return {"status": e.code,
                "headers": {k.lower(): v for k, v in (e.headers or {}).items()},
                "body": body, "bytes": len(body), "truncated": False,
                "final_url": url, "error": f"HTTP {e.code}",
                "elapsed_ms": int((time.time() - t0) * 1000)}
    except Exception as e:  # noqa: BLE001 - network errors are expected and reported
        return {"status": None, "headers": {}, "body": "", "bytes": 0, "truncated": False,
                "final_url": url, "error": str(e),
                "elapsed_ms": int((time.time() - t0) * 1000)}


# --------------------------------------------------------------------------- #
# Minimal HTML parsing (stdlib)
# --------------------------------------------------------------------------- #
_SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}
_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
              "meta", "param", "source", "track", "wbr"}
_LANDMARK_TAGS = {"nav", "header", "footer", "aside"}

# Inline styles that remove an element from human view.
_HIDE_STYLE = re.compile(
    r"(?:display\s*:\s*none"
    r"|visibility\s*:\s*hidden"
    r"|opacity\s*:\s*0(?:\.0+)?(?!\d)"
    r"|font-size\s*:\s*0"
    r"|text-indent\s*:\s*-\s*\d{3,}"
    r"|(?:left|top)\s*:\s*-\s*\d{4,})", re.I)

# Class/id/role markers that mean "legitimate UI that is hidden by default":
# menus, dialogs, accessibility helpers, carousels, tab panels, template states.
_UI_HIDDEN_MARKER = re.compile(
    r"(?:menu|nav|drawer|dropdown|modal|dialog|popover|tooltip|accordion|collaps"
    r"|tab-|tabpanel|carousel|slide|overlay|offcanvas|sr-only|screen-?reader"
    r"|visually-?hidden|skip-link|a11y|aria|toggle|hidden-|is-hidden|close|backdrop"
    r"|cookie|consent|banner|search|filter|lazy|placeholder|spinner|loader|tmpl"
    r"|template|print-only|noscript)", re.I)


class _Extractor(HTMLParser):
    """Pull the structural evidence every sub-audit reasons over.

    Deliberately conservative: this records *what is in the markup* and leaves
    every judgement about what that means to the audits.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self._in_ldjson = False
        self._in_title = False
        self._stack = []            # [(tag, hidden_here, ui_marked, landmark)]
        self._hidden_depth = 0
        self._ui_hidden_depth = 0
        self._landmark_depth = 0

        self.text_parts = []
        self.links = []             # raw href strings
        self.link_pairs = []        # (href, anchor text)
        self.headings = []          # (level, text)
        self.metas = []
        self.ldjson = []
        self.imgs = []
        self.title = ""
        self.html_lang = None
        self.has_viewport = False
        self.canonical = None
        self.link_rels = []
        self.meta_description = ""
        self.meta_robots = ""
        self.og_keys = []
        self.n_forms = 0
        self.n_inputs = 0
        self.n_password_inputs = 0
        self.n_buttons = 0
        self.n_selects = 0
        self.n_mailto = 0
        self.n_tel = 0
        self.n_time_elements = 0
        self.time_datetimes = []
        self.n_code_blocks = 0
        self.has_header = False
        self.has_footer = False
        self.has_nav = False
        self.has_main = False
        self.n_lists_content = 0    # <ul>/<ol> outside nav/header/footer/aside
        self.n_lists_total = 0
        self.n_tables = 0
        self.n_iframes = 0
        self.media = []             # dict(tag, autoplay, muted, controls, loop)
        self.hidden_text_len = 0        # text inside hidden, NOT-UI containers
        self.hidden_ui_text_len = 0     # text inside hidden containers marked as UI
        self.n_hidden_blocks = 0
        self.n_hidden_ui_blocks = 0
        self.nav_link_count = 0
        self.link_text_len = 0
        self._cur_heading = None
        self._cur_heading_buf = []
        self._cur_link_buf = None

    @staticmethod
    def _is_ui(a):
        blob = " ".join(str(a.get(k, "")) for k in ("class", "id", "role", "aria-hidden",
                                                    "data-testid"))
        return bool(_UI_HIDDEN_MARKER.search(blob)) or a.get("aria-hidden") == "true"

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}

        hidden_here = bool(_HIDE_STYLE.search(a.get("style", ""))) or ("hidden" in a)
        ui_marked = self._is_ui(a)
        if tag not in _VOID_TAGS and tag not in _SKIP_TEXT_TAGS:
            self._stack.append((tag, hidden_here, ui_marked, tag in _LANDMARK_TAGS))
            if hidden_here:
                self._hidden_depth += 1
                if ui_marked:
                    self._ui_hidden_depth += 1
                    self.n_hidden_ui_blocks += 1
                else:
                    self.n_hidden_blocks += 1
            if tag in _LANDMARK_TAGS:
                self._landmark_depth += 1

        if tag in _SKIP_TEXT_TAGS:
            self._skip += 1
            if tag == "script" and a.get("type", "").lower().strip() == "application/ld+json":
                self._in_ldjson = True
                self._skip -= 1  # we DO want the text inside ld+json

        if tag == "html" and a.get("lang"):
            self.html_lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "a":
            href = a.get("href", "")
            if href:
                self.links.append(href)
                self._cur_link_buf = [href, []]
                low = href.lower()
                if low.startswith("mailto:"):
                    self.n_mailto += 1
                elif low.startswith("tel:"):
                    self.n_tel += 1
                if self._landmark_depth:
                    self.nav_link_count += 1
        elif tag == "img":
            def _num(v):
                m = re.match(r"\s*(\d+)", str(v or ""))
                return int(m.group(1)) if m else None
            self.imgs.append({
                "src": a.get("src", ""), "alt": a.get("alt"),
                "w": _num(a.get("width")), "h": _num(a.get("height")),
                "in_content": self._landmark_depth == 0,
                "role_presentation": a.get("role", "") in ("presentation", "none"),
            })
        elif tag == "meta":
            self.metas.append(a)
            name = (a.get("name") or "").lower().strip()
            prop = (a.get("property") or "").lower().strip()
            if name == "viewport":
                self.has_viewport = True
            elif name == "description":
                self.meta_description = (a.get("content") or "").strip()
            elif name in ("robots", "googlebot"):
                self.meta_robots = ((self.meta_robots + " ") if self.meta_robots else "") \
                    + (a.get("content") or "").strip().lower()
            if prop.startswith("og:"):
                self.og_keys.append(prop)
        elif tag == "link":
            rel = a.get("rel", "")
            self.link_rels.append((rel, a.get("href", "")))
            if "canonical" in rel.lower():
                self.canonical = a.get("href")
        elif tag == "form":
            self.n_forms += 1
        elif tag == "input":
            self.n_inputs += 1
            if (a.get("type", "") or "").lower() == "password":
                self.n_password_inputs += 1
        elif tag == "button":
            self.n_buttons += 1
        elif tag == "select":
            self.n_selects += 1
        elif tag == "time":
            self.n_time_elements += 1
            if a.get("datetime"):
                self.time_datetimes.append(a["datetime"])
        elif tag in ("pre", "code"):
            self.n_code_blocks += 1
        elif tag in ("ul", "ol"):
            self.n_lists_total += 1
            if self._landmark_depth == 0:
                self.n_lists_content += 1
        elif tag == "table":
            self.n_tables += 1
        elif tag == "iframe":
            self.n_iframes += 1
        elif tag in ("video", "audio"):
            self.media.append({"tag": tag, "autoplay": "autoplay" in a,
                               "muted": "muted" in a, "controls": "controls" in a,
                               "loop": "loop" in a})
        elif tag == "header":
            self.has_header = True
        elif tag == "footer":
            self.has_footer = True
        elif tag == "nav":
            self.has_nav = True
        elif tag == "main":
            self.has_main = True

        m = re.fullmatch(r"h([1-6])", tag)
        if m:
            self._cur_heading = int(m.group(1))
            self._cur_heading_buf = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in _SKIP_TEXT_TAGS:
            if tag == "script" and self._in_ldjson:
                self._in_ldjson = False
            elif self._skip > 0:
                self._skip -= 1
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._cur_link_buf is not None:
            href, buf = self._cur_link_buf
            txt = " ".join("".join(buf).split())
            self.link_pairs.append((href, txt))
            self.link_text_len += len(txt)
            self._cur_link_buf = None

        m = re.fullmatch(r"h([1-6])", tag)
        if m and self._cur_heading is not None:
            txt = " ".join("".join(self._cur_heading_buf).split())
            if txt:
                self.headings.append((self._cur_heading, txt))
            self._cur_heading = None
            self._cur_heading_buf = []

        # unwind the element stack to the nearest matching open tag
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                for _, hidden_here, ui_marked, landmark in self._stack[i:]:
                    if hidden_here:
                        self._hidden_depth = max(0, self._hidden_depth - 1)
                        if ui_marked:
                            self._ui_hidden_depth = max(0, self._ui_hidden_depth - 1)
                    if landmark:
                        self._landmark_depth = max(0, self._landmark_depth - 1)
                del self._stack[i:]
                break

    def handle_data(self, data):
        if self._in_ldjson:
            self.ldjson.append(data)
            return
        if self._in_title:
            self.title += data
        if self._skip:
            return
        s = data.strip()
        if not s:
            return
        if self._hidden_depth:
            # Text a human cannot see. Split UI chrome from everything else so the
            # integrity audit can tell a closed menu from a block of buried prose.
            if self._ui_hidden_depth:
                self.hidden_ui_text_len += len(s)
            else:
                self.hidden_text_len += len(s)
            return
        self.text_parts.append(s)
        if self._cur_heading is not None:
            self._cur_heading_buf.append(data)
        if self._cur_link_buf is not None:
            self._cur_link_buf[1].append(data)

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
    site = (site or "").strip()
    if not re.match(r"^https?://", site):
        site = "https://" + site
    return site.rstrip("/")


_DEFAULT_PORT = {"http": "80", "https": "443"}


def _registrable(netloc, scheme="https"):
    """Host[:port] without credentials, without a default port, and without a
    leading 'www.' LABEL (a prefix, not a character set - str.lstrip("www.")
    would eat the leading letters of hosts like 'weather.com')."""
    authority = (netloc or "").split("@")[-1].lower().rstrip(".")
    host, _, port = authority.partition(":")
    if host.startswith("www."):
        host = host[4:]
    if port and port != _DEFAULT_PORT.get(scheme):
        return f"{host}:{port}"
    return host


def same_host(base, url):
    """True when `url` belongs to the same site as `base`.

    http and https are treated as the same site, but an explicit non-default port
    is a different origin - which is what makes a local fixture on another port,
    or a service moved to a different host, correctly read as off-site.
    """
    try:
        b, u = urllib.parse.urlparse(base), urllib.parse.urlparse(url)
        if not u.netloc:
            return True                      # a relative URL is same-site by definition
        return (_registrable(u.netloc, u.scheme or b.scheme or "https")
                == _registrable(b.netloc, b.scheme or "https"))
    except Exception:
        return False


def absolutize(base, href):
    try:
        return urllib.parse.urljoin(base, href)
    except Exception:
        return href


def slug(url):
    return hashlib.sha1(url.encode("utf-8", "replace")).hexdigest()[:16]


def url_path(url):
    try:
        return (urllib.parse.urlparse(url).path or "/").lower()
    except Exception:
        return "/"


def is_homepage_url(site, url):
    try:
        p = urllib.parse.urlparse(url)
        return same_host(site, url) and (p.path or "/").rstrip("/") in ("", "/") and not p.query
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# robots.txt
# --------------------------------------------------------------------------- #
# The standard library's urllib.robotparser discards a rule's query component:
# it runs each rule path through urlparse/urlunparse, so the very common
# "Disallow: /?" (used by google.com, wikipedia.org and many large sites to keep
# crawlers off parameterised URLs) collapses into "Disallow: /" and appears to
# forbid the entire site. That silently produced empty crawls and a false
# "AI crawlers are blocked" finding for every such site.
#
# This parser follows RFC 9309 instead: a rule is matched against the URL's path
# AND query, "*" matches any run of characters, "$" anchors the end, and the
# longest matching rule wins with Allow breaking a tie. It is never more
# permissive than the stdlib on a rule the stdlib gets right.


class Robots:
    """A robots.txt policy that matches rules against path *and* query."""

    def __init__(self, text=""):
        self.text = text or ""
        self.groups = []          # [(set(agent_lower), [(pattern, allow), ...])]
        self.sitemaps = []
        self.crawl_delays = {}    # agent_lower -> float
        self._parse()

    def _parse(self):
        agents, rules, expecting_agent = set(), [], True
        for raw in self.text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            field, _, value = line.partition(":")
            field, value = field.strip().lower(), value.strip()
            if field == "sitemap":
                self.sitemaps.append(value)
                continue
            if field == "user-agent":
                if not expecting_agent:          # a new group starts here
                    if agents:
                        self.groups.append((agents, rules))
                    agents, rules, expecting_agent = set(), [], True
                agents.add(value.lower())
                continue
            if field in ("allow", "disallow"):
                expecting_agent = False
                if not agents:
                    continue
                # "Disallow:" with an empty value means "nothing is disallowed".
                if field == "disallow" and value == "":
                    continue
                rules.append((value, field == "allow"))
            elif field == "crawl-delay":
                expecting_agent = False
                try:
                    for a in agents:
                        self.crawl_delays[a] = float(value)
                except ValueError:
                    pass
        if agents:
            self.groups.append((agents, rules))

    @staticmethod
    def _product_token(ua):
        return (ua or "").split("/")[0].strip().lower()

    def _group_for(self, ua):
        """The most specific matching group, per RFC 9309: longest agent match,
        falling back to the '*' group."""
        token = self._product_token(ua)
        best, best_len = None, -1
        star = None
        for agents, rules in self.groups:
            for a in agents:
                if a == "*":
                    if star is None:
                        star = rules
                    continue
                if a and a in token and len(a) > best_len:
                    best, best_len = rules, len(a)
        return best if best is not None else star

    @staticmethod
    def _match(pattern, target):
        """RFC 9309 path matching: '*' is any run, '$' anchors the end."""
        if pattern == "":
            return False
        anchored = pattern.endswith("$")
        if anchored:
            pattern = pattern[:-1]
        parts = pattern.split("*")
        pos = 0
        if not target.startswith(parts[0]):
            return False
        pos = len(parts[0])
        for part in parts[1:]:
            if part == "":
                continue
            idx = target.find(part, pos)
            if idx < 0:
                return False
            pos = idx + len(part)
        if anchored:
            if parts[-1] == "":
                return True           # trailing "*$" matches any remainder
            return target.endswith(parts[-1]) and pos == len(target)
        return True

    def can_fetch(self, ua, url):
        """True when `ua` may fetch `url` under this policy."""
        rules = self._group_for(ua)
        if not rules:
            return True
        try:
            parts = urllib.parse.urlparse(url)
        except Exception:
            return True
        target = parts.path or "/"
        if parts.query:
            target += "?" + parts.query
        # Longest match wins; Allow wins a tie (RFC 9309 section 2.2.2).
        best_len, best_allow = -1, True
        for pattern, allow in rules:
            if self._match(pattern, target) and len(pattern) >= best_len:
                if len(pattern) > best_len or allow:
                    best_len, best_allow = len(pattern), allow
        return best_allow if best_len >= 0 else True

    def crawl_delay(self, ua):
        token = self._product_token(ua)
        for agents, _ in self.groups:
            for a in agents:
                if a != "*" and a and a in token and a in self.crawl_delays:
                    return self.crawl_delays[a]
        return self.crawl_delays.get("*")

    def disallowed_prefixes(self, ua, limit=8):
        """The Disallow patterns that apply to `ua`, for reporting in evidence."""
        rules = self._group_for(ua) or []
        return [p for p, allow in rules if not allow][:limit]


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
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


# --------------------------------------------------------------------------- #
# 1. Resource classification
# --------------------------------------------------------------------------- #
RESOURCE_KINDS = ("html", "xml", "json", "image", "pdf", "document", "text",
                  "other", "error", "unfetched", "offsite_redirect")

_XML_HEAD = re.compile(r"^\s*(?:<\?xml|<urlset|<sitemapindex|<rss|<feed\b)", re.I)
_HTML_HEAD = re.compile(r"<!doctype\s+html|<html[\s>]|<head[\s>]|<body[\s>]", re.I)
_IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".avif", ".bmp")
_DOC_EXT = (".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".csv")


def classify_resource(status=None, content_type="", url="", body="", error=None,
                      robots_blocked=False, offsite_redirect=False):
    """Decide what kind of resource a response actually is.

    Uses, in priority order: (1) the HTTP Content-Type header, (2) a sniff of the
    response body, (3) the URL path extension. No single signal decides alone,
    and a URL keyword never overrides a body that plainly parses as HTML.

    Returns a dict with `resource_kind`, `is_html`, `useful_for_page_audit` and
    `classification_basis` (which signal decided), so findings can cite it.
    """
    def out(kind, basis, html=False, useful=False):
        return {"resource_kind": kind, "is_html": html,
                "useful_for_page_audit": useful, "classification_basis": basis}

    if robots_blocked:
        return out("unfetched", "robots.txt disallow - not requested")
    if offsite_redirect:
        # The request was answered by a different host. Whatever came back is that
        # host's content, not this site's page, so no page-level check may run
        # against it - otherwise the redirect shows up as a page with no title.
        return out("offsite_redirect", "redirected to a different host")
    if status is None:
        return out("unfetched", f"no response ({error or 'request failed'})")
    if status >= 400:
        return out("error", f"HTTP {status}")

    ct = (content_type or "").split(";")[0].strip().lower()
    head = (body or "")[:4096]
    path = url_path(url)

    # (1) Content-Type, when it says something unambiguous.
    if ct:
        if ct in ("text/html", "application/xhtml+xml"):
            # Servers mislabel XML feeds as text/html; the body settles it.
            if _XML_HEAD.match(head) and not _HTML_HEAD.search(head):
                return out("xml", "body sniff overrides text/html Content-Type")
            return out("html", f"Content-Type: {ct}", html=True, useful=True)
        if "json" in ct:
            return out("json", f"Content-Type: {ct}")
        if "xml" in ct:
            return out("xml", f"Content-Type: {ct}")
        if ct.startswith("image/"):
            return out("image", f"Content-Type: {ct}")
        if ct == "application/pdf":
            return out("pdf", f"Content-Type: {ct}")
        if ct.startswith("text/"):
            # text/plain that is really markup (some hosts do this) still sniffs.
            if _HTML_HEAD.search(head):
                return out("html", f"body sniff overrides Content-Type: {ct}",
                           html=True, useful=True)
            if _XML_HEAD.match(head):
                return out("xml", f"body sniff overrides Content-Type: {ct}")
            return out("text", f"Content-Type: {ct}")
        if ct.startswith(("audio/", "video/", "font/")):
            return out("other", f"Content-Type: {ct}")
        if ct in ("application/msword", "application/zip") or ct.startswith("application/vnd"):
            return out("document", f"Content-Type: {ct}")

    # (2) Body sniff, when the header was missing or generic.
    if _XML_HEAD.match(head):
        return out("xml", "body starts with an XML declaration/root element")
    if _HTML_HEAD.search(head):
        return out("html", "body contains an HTML document structure", html=True, useful=True)
    if head.lstrip()[:1] in ("{", "["):
        try:
            json.loads(body)
            return out("json", "body parses as JSON")
        except Exception:
            pass

    # (3) URL extension, last resort only.
    if path.endswith(_IMG_EXT):
        return out("image", f"URL extension {os.path.splitext(path)[1]}")
    if path.endswith(".pdf"):
        return out("pdf", "URL extension .pdf")
    if path.endswith(_DOC_EXT):
        return out("document", f"URL extension {os.path.splitext(path)[1]}")
    if path.endswith((".xml", ".rss", ".atom")):
        return out("xml", f"URL extension {os.path.splitext(path)[1]}")
    if path.endswith(".json"):
        return out("json", "URL extension .json")
    if path.endswith(".txt"):
        return out("text", "URL extension .txt")

    if not (body or "").strip():
        return out("other", "empty response body")
    return out("other", "no HTML/XML/JSON structure detected in body")


def is_html_page(page):
    """True only for resources classified as an HTML document with a 2xx status.

    Every HTML-specific check (title, H1, viewport, CTA, navigation, walls of
    text, structured data) must filter on this. XML sitemaps, JSON endpoints,
    images and PDFs are not pages and must never be audited as pages.
    """
    if "is_html" in page:
        return bool(page["is_html"])
    return classify_resource(page.get("status"), page.get("content_type", ""),
                             page.get("url", ""), "", page.get("error"),
                             page.get("robots_blocked", False))["is_html"]


def html_pages(meta):
    """The standard page-selection filter for every sub-audit."""
    return [p for p in meta.get("pages", []) if is_html_page(p)]


def non_html_resources(meta):
    return [p for p in meta.get("pages", []) if not is_html_page(p)]


def homepage_of(meta):
    """The homepage record, chosen by URL and role rather than crawl order."""
    site = meta.get("site", "")
    pages = html_pages(meta)
    for p in pages:
        if p.get("page_role") == "homepage":
            return p
    for p in pages:
        if is_homepage_url(site, p.get("url", "")):
            return p
    return pages[0] if pages else None


# --------------------------------------------------------------------------- #
# 2. Page-role classification
# --------------------------------------------------------------------------- #
PAGE_ROLES = ("homepage", "article", "product", "documentation", "utility",
              "contact", "legal", "directory", "authentication", "resource",
              "generic", "unknown")

# Roles where a conversion-style next step is a reasonable expectation at all.
# A documentation page, an article, a legal notice or a login form is not
# defective for lacking one.
CONVERSION_ROLES = {"homepage", "product"}

# Roles whose prose is legitimately paragraph-heavy; "walls of text" is not a
# defect for them.
PROSE_ROLES = {"article", "legal", "documentation", "generic", "unknown"}

_SCHEMA_ROLE = {
    "newsarticle": "article", "blogposting": "article", "article": "article",
    "report": "article", "liveblogposting": "article", "socialmediaposting": "article",
    "product": "product", "offer": "product", "aggregateoffer": "product",
    "service": "product", "softwareapplication": "product", "course": "product",
    "techarticle": "documentation", "apireference": "documentation",
    "howto": "documentation", "faqpage": "documentation",
    "contactpage": "contact",
    "collectionpage": "directory", "itemlist": "directory",
    "searchresultspage": "directory",
}


def classify_page_role(evidence):
    """Infer what an HTML page is FOR, from converging evidence.

    `evidence` keys (all optional): url, site, title, headings, text, text_len,
    schema_types, n_forms, n_password_inputs, n_inputs, n_buttons, n_selects,
    n_links, link_text_ratio, n_time_elements, n_code_blocks, has_price,
    n_mailto, n_tel.

    Returns (role, confidence) where confidence is 'high' | 'medium' | 'low'.
    A URL keyword alone is never enough for 'high'. When signals are weak the
    answer is ('unknown', 'low') and role-specific checks stand down rather than
    guess.
    """
    url = (evidence.get("url") or "").lower()
    site = evidence.get("site") or ""
    path = url_path(url)
    title = (evidence.get("title") or "").lower()
    text_len = evidence.get("text_len", len(evidence.get("text") or ""))
    heads = " ".join(h.lower() for h in (evidence.get("headings") or []))
    schema = {str(t).lower() for t in (evidence.get("schema_types") or [])}
    blob = " ".join([title, heads])

    # Homepage is decided by URL alone - that is what a homepage *is*.
    if site and is_homepage_url(site, url):
        return "homepage", "high"

    # Structured data, when present, is the strongest single statement a site
    # makes about what a page is.
    for t in sorted(schema):
        role = _SCHEMA_ROLE.get(t)
        if role:
            return role, "high"

    def url_hit(*pats):
        return any(p in path for p in pats)

    def word_hit(*pats):
        return any(p in blob for p in pats)

    # Each role needs a URL/title hint PLUS an independent content signal for
    # 'high'; a lone hint yields 'medium'.
    candidates = []

    if url_hit("/login", "/signin", "/sign-in", "/signup", "/sign-up", "/register",
               "/auth", "/session") or word_hit("sign in", "log in", "create account"):
        strong = evidence.get("n_password_inputs", 0) > 0 or (
            evidence.get("n_forms", 0) > 0 and text_len < 2000)
        candidates.append(("authentication", "high" if strong else "medium"))

    if url_hit("/privacy", "/terms", "/legal", "/cookie", "/gdpr", "/imprint",
               "/disclaimer", "/policy", "/eula", "/licen") or \
            word_hit("privacy policy", "terms of service", "terms and conditions",
                     "cookie policy", "legal notice", "imprint"):
        strong = text_len > 1500 or word_hit("privacy policy", "terms of service",
                                             "terms and conditions")
        candidates.append(("legal", "high" if strong else "medium"))

    if url_hit("/contact", "/get-in-touch", "/reach-us") or word_hit("contact us"):
        strong = (evidence.get("n_mailto", 0) > 0 or evidence.get("n_tel", 0) > 0
                  or evidence.get("n_forms", 0) > 0)
        candidates.append(("contact", "high" if strong else "medium"))

    if url_hit("/docs", "/doc/", "/documentation", "/reference", "/api", "/manual",
               "/guide", "/handbook", "/help", "/support", "/kb", "/knowledge",
               "/tutorial", "/faq"):
        strong = evidence.get("n_code_blocks", 0) > 0 or len(evidence.get("headings") or []) >= 4
        candidates.append(("documentation", "high" if strong else "medium"))

    if url_hit("/blog/", "/news/", "/post/", "/posts/", "/article/", "/articles/",
               "/story/", "/stories/", "/journal/", "/essay"):
        strong = evidence.get("n_time_elements", 0) > 0 or text_len > 1200
        candidates.append(("article", "high" if strong else "medium"))

    if url_hit("/product", "/products/", "/pricing", "/plans", "/shop", "/store",
               "/item/", "/buy", "/p/"):
        strong = bool(evidence.get("has_price")) or word_hit("pricing", "plans", "per month")
        candidates.append(("product", "high" if strong else "medium"))

    if url_hit("/category", "/categories", "/tag/", "/tags/", "/archive",
               "/browse", "/directory", "/listing", "/search"):
        ratio = evidence.get("link_text_ratio")
        strong = ratio is not None and ratio > 0.5
        candidates.append(("directory", "high" if strong else "medium"))

    if candidates:
        candidates.sort(key=lambda c: 0 if c[1] == "high" else 1)
        return candidates[0]

    # No URL/title hint matched. Fall back to the shape of the content itself.
    ratio = evidence.get("link_text_ratio")
    n_links = evidence.get("n_links", 0)
    if ratio is not None and ratio > 0.6 and n_links >= 20 and text_len < 4000:
        return "directory", "medium"          # a page that is mostly a link list
    interactive = (evidence.get("n_inputs", 0) + evidence.get("n_buttons", 0)
                   + evidence.get("n_selects", 0))
    if interactive >= 4 and text_len < 800:
        return "utility", "medium"            # a tool/app screen, not a document
    if text_len >= 800:
        return "generic", "medium"            # real prose, role simply unstated
    return "unknown", "low"


def role_of(page):
    return page.get("page_role") or "unknown"


def role_confident(page):
    """True when a role-specific check may rely on the role assignment."""
    return page.get("page_role_confidence") in ("high", "medium") \
        and role_of(page) != "unknown"


def role_histogram(pages):
    hist = {}
    for p in pages:
        hist[role_of(p)] = hist.get(role_of(p), 0) + 1
    return dict(sorted(hist.items()))


# --------------------------------------------------------------------------- #
# 3. Evidence discipline, severity gating, findings
# --------------------------------------------------------------------------- #
SEVERITIES = ("critical", "high", "medium", "low")
SEV_ORDER = {s: i for i, s in enumerate(SEVERITIES)}
CONFIDENCE_CAP = {"high": "critical", "medium": "medium", "low": "low"}


def cap(severity, ceiling):
    """Return the less severe of `severity` and `ceiling`."""
    if SEV_ORDER.get(severity, 3) < SEV_ORDER.get(ceiling, 3):
        return ceiling
    return severity


def calibrate(f):
    """Apply the severity gates to one finding, in place, recording every change.

    Gates (see references/severity-rubric.md):
      - An IMPROVEMENT is an optional recommendation, never a defect: max 'low'.
      - Confidence caps severity: medium -> 'medium', low -> 'low'.
      - CRITICAL and HIGH additionally require `material=True`, which a check
        sets only after establishing that the affected resource is relevant, the
        problem is real, and the impact is material.
    """
    original = f.get("severity", "low")
    sev = original if original in SEVERITIES else "low"
    reasons = []

    if f.get("finding_type") == "improvement":
        new = cap(sev, "low")
        if new != sev:
            reasons.append("improvement (optional recommendation, not a defect)")
        sev = new

    ceiling = CONFIDENCE_CAP.get(f.get("confidence", "high"), "low")
    new = cap(sev, ceiling)
    if new != sev:
        reasons.append(f"confidence={f.get('confidence')}")
    sev = new

    if sev in ("critical", "high") and not f.get("material"):
        sev = "medium"
        reasons.append("materiality not established")

    f["severity"] = sev
    f.setdefault("suggested_action", {})["priority"] = sev
    if reasons:
        f["severity_capped_from"] = original
        f["severity_cap_reason"] = "; ".join(reasons)
    return f


def scope_phrase(n_affected, n_checked, unit="sampled HTML pages"):
    """Render a claim's scope so a reader never mistakes a sample for the site."""
    if not n_checked:
        return f"{n_affected} {unit}"
    return f"{n_affected}/{n_checked} {unit}"


def finding(title, severity, observation, interpretation, action_summary, priority,
            category, *, checked=None, checked_unit="sampled HTML pages",
            finding_type="defect", confidence="high", material=False, page_role=None,
            scope=None, mechanism=None, dedup_key=None, not_verified=None,
            thin_html_sensitive=False):
    """Build one finding with its evidence chain kept explicit.

    observation      what the audit directly measured, with its scope. No inference.
    interpretation   what that may imply, in cautious language. Never causal
                     unless causality was actually measured.
    not_verified     anything the audit did NOT establish but that a reader might
                     otherwise assume it had.
    checked          how many items were inspected, with `checked_unit` naming what
                     they were. Without the unit a count of user-agents reads as a
                     count of pages.

    `evidence` (required by the report schema) is composed from these, so the
    string a grader reads can never claim more than the observation supports.
    """
    if severity not in SEVERITIES:
        severity = "low"
    parts = [observation.strip()]
    if interpretation:
        parts.append(interpretation.strip())
    if not_verified:
        parts.append(f"Not verified by this audit: {not_verified.strip()}")
    f = {
        "title": title,
        "severity": severity,
        "category": category,
        "evidence": " ".join(p for p in parts if p),
        "evidence_detail": {
            "observation": observation.strip(),
            "interpretation": (interpretation or "").strip(),
            "not_verified": (not_verified or "").strip(),
        },
        "suggested_action": {"summary": action_summary, "priority": priority},
        "finding_type": finding_type,
        "confidence": confidence,
        "material": bool(material),
    }
    if checked is not None:
        f["checked"] = checked
        f["checked_unit"] = checked_unit
    if page_role:
        f["page_role"] = page_role
    if scope:
        f["scope"] = scope
    if mechanism:
        f["mechanism"] = mechanism
    f["dedup_key"] = dedup_key or f"{category}:{title.lower()[:60]}"
    if thin_html_sensitive:
        f["_thin_html_sensitive"] = True
    return f


def skipped(check, reason, **extra):
    """Record a check that did not run. A skipped check is scope, not a finding."""
    rec = {"check": check, "reason": reason}
    rec.update(extra)
    return rec


def emit(skill_id, findings, skipped_checks=None):
    """Print the standard sub-audit envelope on a UTF-8 stream.

    Windows consoles default to cp1252 and cannot encode characters that appear
    in page titles and evidence; wrapping stdout keeps the envelope parseable
    regardless of the host console encoding.
    """
    import io
    payload = json.dumps({"skill": skill_id, "findings": findings,
                          "skipped_checks": skipped_checks or []},
                         ensure_ascii=False, indent=2)
    try:
        stream = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        stream = sys.stdout
    print(payload, file=stream)
    try:
        stream.flush()
    except Exception:
        pass
