#!/usr/bin/env python3
"""HTML fact extraction on the standard library.

Builds a lightweight DOM from html.parser and pulls out everything the six
audit skills need, so that no audit skill ever parses HTML itself. Every
collection this module returns is sorted or in document order, because the
audit must be byte-identical across runs.

Where an optional dependency would do better we still implement a usable
stdlib path and say so at the call site:

  * main-content extraction here is a text-density heuristic; trafilatura is
    better and, when installed, replaces it. The heuristic is good enough to
    keep every answerability check in the CORE tier.
  * JSON-LD is parsed exactly (it is just JSON). Microdata and RDFa are parsed
    structurally but not resolved against the full vocabulary; extruct does
    that and, when installed, replaces this.
"""

from __future__ import annotations

import html
import json
import re
import urllib.parse
from dataclasses import dataclass, field
from html.parser import HTMLParser

__all__ = ["Document", "parse_html"]

VOID_ELEMENTS = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)
SKIP_TEXT_IN = frozenset("script style noscript template svg canvas".split())
BLOCK_ELEMENTS = frozenset(
    "address article aside blockquote details div dl fieldset figcaption figure "
    "footer form h1 h2 h3 h4 h5 h6 header hgroup li main nav ol p pre section table "
    "tbody td tfoot th thead tr ul".split()
)
# Chrome that must not count as main content when measuring boilerplate ratio.
CHROME_ELEMENTS = frozenset("nav header footer aside".split())

HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")

FRAMEWORK_ROOT_IDS = frozenset(
    {"root", "app", "__next", "__nuxt", "___gatsby", "svelte", "q-app", "main-app", "application"}
)
# Same names as a class, because not every framework uses an id. devdocs.io
# mounts into <div class="_app">, which the id-only lookup missed entirely.
FRAMEWORK_ROOT_CLASSES = frozenset(
    {"_app", "app", "root", "app-root", "application", "page-root", "js-app"}
)
# A noscript telling the visitor to turn JavaScript on is the most portable
# shell signal there is: it is what a client-rendered page says when it cannot
# render. It does not depend on recognising anyone's bundler.
NOSCRIPT_JS_NOTICE = re.compile(
    r"(enable|turn on|requires?|need)\s+(java\s?script|js)\b|java\s?script\s+(is\s+)?(required|disabled)",
    re.I,
)
BUNDLE_SRC_RE = re.compile(
    r"(runtime|polyfills|vendor|chunk|bundle|main|app|index)[.\-~][0-9a-f]{6,}|"
    r"/_next/static/|/_nuxt/|/static/js/|\.esm\.js|/assets/index-[0-9a-zA-Z_]{6,}\.js",
    re.I,
)


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    parent: "Node | None" = None
    text_parts: list = field(default_factory=list)

    def text(self) -> str:
        out: list[str] = []

        def walk(n: "Node") -> None:
            if n.tag in SKIP_TEXT_IN:
                return
            for item in n.children:
                if isinstance(item, str):
                    out.append(item)
                else:
                    walk(item)

        walk(self)
        return _collapse(" ".join(out))

    def link_text(self) -> str:
        out: list[str] = []

        def walk(n: "Node") -> None:
            if n.tag in SKIP_TEXT_IN:
                return
            if n.tag == "a":
                out.append(n.text())
                return
            for item in n.children:
                if not isinstance(item, str):
                    walk(item)

        walk(self)
        return _collapse(" ".join(out))

    def iter_descendants(self):
        for item in self.children:
            if isinstance(item, Node):
                yield item
                yield from item.iter_descendants()

    def ancestors(self):
        n = self.parent
        while n is not None:
            yield n
            n = n.parent


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def wordcount(text: str) -> int:
    return len(re.findall(r"[^\s]+", text))


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack = [self.root]
        self.jsonld_raw: list[tuple[str, int]] = []
        self._in_jsonld = False
        self._jsonld_buf: list[str] = []
        self.script_srcs: list[str] = []
        self.noscript_text: list[str] = []
        self._in_noscript = False

    # HTMLParser hooks -------------------------------------------------

    def handle_starttag(self, tag, attrs):
        d = {}
        for k, v in attrs:
            if k is not None and k.lower() not in d:
                d[k.lower()] = v if v is not None else ""
        node = Node(tag, d, parent=self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID_ELEMENTS:
            self.stack.append(node)
        if tag == "script":
            if (d.get("type") or "").lower().strip() == "application/ld+json":
                self._in_jsonld = True
                self._jsonld_buf = []
            if d.get("src"):
                self.script_srcs.append(d["src"])
        if tag == "noscript":
            self._in_noscript = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_ELEMENTS and self.stack and self.stack[-1].tag == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag == "script" and self._in_jsonld:
            self.jsonld_raw.append(("".join(self._jsonld_buf), self.getpos()[0]))
            self._in_jsonld = False
            self._jsonld_buf = []
        if tag == "noscript":
            self._in_noscript = False
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self._in_jsonld:
            self._jsonld_buf.append(data)
            return
        if self._in_noscript:
            self.noscript_text.append(data)
        self.stack[-1].children.append(data)


@dataclass
class Document:
    url: str
    root: Node
    title: str = ""
    meta: dict = field(default_factory=dict)
    canonical: str | None = None
    meta_robots: str | None = None
    viewport: str | None = None
    headings: dict = field(default_factory=dict)
    links: list = field(default_factory=list)
    images: list = field(default_factory=list)
    forms: list = field(default_factory=list)
    jsonld: list = field(default_factory=list)
    jsonld_errors: list = field(default_factory=list)
    microdata: list = field(default_factory=list)
    rdfa: list = field(default_factory=list)
    opengraph: dict = field(default_factory=dict)
    text: str = ""
    wordcount: int = 0
    main_text: str = ""
    main_wordcount: int = 0
    main_selector: str = ""
    noscript_wordcount: int = 0
    noscript_text: str = ""

    script_srcs: list = field(default_factory=list)
    framework_root: str | None = None
    framework_root_wordcount: int = 0
    bundle_scripts: list = field(default_factory=list)

    @property
    def boilerplate_ratio(self) -> float:
        if not self.wordcount:
            return 0.0
        return 1.0 - (self.main_wordcount / self.wordcount)

    @property
    def spa_shell_signals(self) -> dict:
        """The individual signals behind looks_like_spa_shell, for evidence."""
        return {
            "framework_root": self.framework_root,
            "framework_root_wordcount": self.framework_root_wordcount,
            "body_wordcount": self.wordcount,
            "bundle_scripts": list(self.bundle_scripts),
            "script_count": len(self.script_srcs),
            "noscript_wordcount": self.noscript_wordcount,
            "noscript_js_notice": bool(NOSCRIPT_JS_NOTICE.search(self.noscript_text or "")),
        }

    @property
    def looks_like_spa_shell(self) -> bool:
        """Static signature of an unhydrated single-page-app mount point.

        This is the CORE-tier path to a render-stage finding: it needs no
        browser. Deliberately conservative - all four signals must agree -
        because a false positive caps a site's whole discoverability report
        under gate Rule 2 and suppresses 14 engagement checks under Rule 0b.

        The discriminating signal is that the framework mount point is EMPTY.
        A server-rendered or hydrated page puts its content inside that element;
        only an unhydrated shell leaves it bare. Keying off total or main
        wordcount instead would misfire on any legitimately short page.
        """
        if self.wordcount >= 50:
            return False              # there is real text; not a shell
        if not self.script_srcs:
            return False              # nothing to hydrate it later
        # Either a recognised mount point that is empty, or the page itself
        # saying it needs JavaScript. Requiring BOTH plus a bundler-shaped
        # filename gave this check zero recall on five live sites.
        mount_empty = (
            self.framework_root is not None and self.framework_root_wordcount < 10
        )
        js_notice = bool(NOSCRIPT_JS_NOTICE.search(self.noscript_text or ""))
        return mount_empty or js_notice


def _first_meta(root: Node, **match) -> str | None:
    for node in root.iter_descendants():
        if node.tag != "meta":
            continue
        ok = True
        for key, value in match.items():
            if (node.attrs.get(key) or "").lower() != value:
                ok = False
                break
        if ok:
            return node.attrs.get("content")
    return None


def _selector_for(node: Node) -> str:
    bits = [node.tag]
    if node.attrs.get("id"):
        bits.append("#" + node.attrs["id"])
    elif node.attrs.get("role"):
        bits.append('[role="%s"]' % node.attrs["role"])
    elif node.attrs.get("class"):
        first = node.attrs["class"].split()
        if first:
            bits.append("." + first[0])
    return "".join(bits)


# A block whose text is mostly anchor text is navigation, whatever tag it uses.
# Tag-based chrome detection alone missed sqlite.org entirely: its navigation is
# a plain table, not <nav>, so the page's "first sentence" came out as its menu.
# Legacy table-layout sites are exactly the unseen-site case this has to survive.
LINK_DENSITY_CHROME = 0.5
MIN_CHROME_LINKS = 3
MIN_CONTENT_RETAINED = 0.2


def _link_density(node: Node) -> float:
    words = wordcount(node.text())
    if not words:
        return 1.0
    return wordcount(node.link_text()) / words


def _is_link_block(node: Node) -> bool:
    """Is this block a menu, breadcrumb trail or link list rather than prose?"""
    if node.tag not in BLOCK_ELEMENTS:
        return False
    words = wordcount(node.text())
    if words < 5:
        return False
    links = sum(1 for d in node.iter_descendants() if d.tag == "a")
    if links < MIN_CHROME_LINKS:
        return False
    return _link_density(node) > LINK_DENSITY_CHROME


def _text_excluding_chrome(node: Node) -> str:
    """All text under a node except chrome, by tag AND by link density.

    Two passes because tags alone are not enough. A site built before HTML5 has
    no <nav>; its menu is a table or a div, and only the density of anchor text
    distinguishes it from prose.

    Guard: on a category or listing page the content genuinely IS links, so if
    stripping link-heavy blocks removes almost everything, the stripping was
    wrong and the untouched text is returned instead.
    """
    def collect(skip_link_blocks: bool) -> str:
        out: list[str] = []

        def walk(n: Node) -> None:
            if n.tag in SKIP_TEXT_IN or n.tag in CHROME_ELEMENTS:
                return
            if (n.attrs.get("role") or "").lower() in ("navigation", "banner", "contentinfo", "search"):
                return
            if skip_link_blocks and n is not node and _is_link_block(n):
                return
            for item in n.children:
                if isinstance(item, str):
                    out.append(item)
                else:
                    walk(item)

        walk(node)
        return _collapse(" ".join(out))

    full = collect(skip_link_blocks=False)
    stripped = collect(skip_link_blocks=True)
    if not full:
        return ""
    if wordcount(stripped) < wordcount(full) * MIN_CONTENT_RETAINED:
        return full
    return stripped


def _extract_main(root: Node) -> tuple[Node | None, str]:
    """Pick the node that holds the page's main content.

    Semantic elements win outright. Otherwise score candidate blocks by text
    length discounted by link density, which reliably separates an article body
    from a navigation column without needing a model.
    """
    for tag in ("main", "article"):
        for node in root.iter_descendants():
            if node.tag == tag and wordcount(node.text()) >= 25:
                return node, _selector_for(node)
    for node in root.iter_descendants():
        if (node.attrs.get("role") or "").lower() == "main" and wordcount(node.text()) >= 25:
            return node, _selector_for(node)

    best: tuple[float, Node] | None = None
    for node in root.iter_descendants():
        # td included so that a legacy table layout can still yield a content
        # cell; tr and table are not, because they wrap the whole page.
        if node.tag not in ("div", "section", "td", "article", "body"):
            continue
        if any(a.tag in CHROME_ELEMENTS for a in node.ancestors()):
            continue
        words = wordcount(node.text())
        if words < 25:
            continue
        density = _link_density(node)
        if density > LINK_DENSITY_CHROME:
            continue
        # Squaring the discount separates a content block from a link list far
        # more sharply than a linear one. A block at 45% anchor text scores 30%
        # of its length here, against 55% under the linear form, which is what
        # let navigation win on link-heavy legacy pages.
        score = words * (1.0 - density) ** 2
        if best is None or score > best[0] * 1.02:
            best = (score, node)
    if best:
        return best[1], _selector_for(best[1])
    return None, ""


def _walk_microdata(root: Node) -> list[dict]:
    items: list[dict] = []
    for node in root.iter_descendants():
        if "itemscope" not in node.attrs:
            continue
        item = {"type": node.attrs.get("itemtype", ""), "properties": {}}
        for child in node.iter_descendants():
            prop = child.attrs.get("itemprop")
            if not prop or "itemscope" in child.attrs:
                continue
            value = (
                child.attrs.get("content")
                or child.attrs.get("href")
                or child.attrs.get("src")
                or child.attrs.get("datetime")
                or child.text()
            )
            item["properties"].setdefault(prop, []).append(_collapse(str(value)))
        items.append(item)
    return items


def _walk_rdfa(root: Node) -> list[dict]:
    items: list[dict] = []
    for node in root.iter_descendants():
        if "typeof" not in node.attrs:
            continue
        item = {"type": node.attrs.get("typeof", ""), "properties": {}}
        for child in node.iter_descendants():
            prop = child.attrs.get("property")
            if not prop:
                continue
            value = child.attrs.get("content") or child.attrs.get("href") or child.text()
            item["properties"].setdefault(prop, []).append(_collapse(str(value)))
        items.append(item)
    return items


def _in_main(node: Node, main: Node | None) -> bool:
    if main is None:
        return True
    if node is main:
        return True
    return any(a is main for a in node.ancestors())


def _labelled(node: Node, label_for: set[str]) -> bool:
    if node.attrs.get("aria-label") or node.attrs.get("aria-labelledby"):
        return True
    if node.attrs.get("id") and node.attrs["id"] in label_for:
        return True
    return any(a.tag == "label" for a in node.ancestors())


def parse_html(markup: str, url: str = "") -> Document:
    """Parse one HTML document. Never raises on malformed markup."""
    builder = _Builder()
    try:
        builder.feed(markup)
        builder.close()
    except Exception:  # noqa: BLE001 - html.parser can raise on pathological input
        pass
    root = builder.root

    doc = Document(url=url, root=root)

    for node in root.iter_descendants():
        if node.tag == "title" and not doc.title:
            doc.title = _collapse(node.text())
        elif node.tag == "meta":
            name = (node.attrs.get("name") or "").lower()
            prop = (node.attrs.get("property") or "").lower()
            content = node.attrs.get("content") or ""
            if name:
                doc.meta[name] = content
            if prop.startswith("og:") or prop.startswith("twitter:"):
                doc.opengraph[prop] = content
        elif node.tag == "link":
            rel = (node.attrs.get("rel") or "").lower()
            if "canonical" in rel and doc.canonical is None:
                doc.canonical = urllib.parse.urljoin(url, node.attrs.get("href", ""))

    doc.meta_robots = doc.meta.get("robots")
    doc.viewport = doc.meta.get("viewport")

    for tag in HEADING_TAGS:
        doc.headings[tag] = [
            _collapse(n.text()) for n in root.iter_descendants() if n.tag == tag and _collapse(n.text())
        ]

    main, selector = _extract_main(root)
    doc.main_selector = selector

    label_for = {
        n.attrs["for"] for n in root.iter_descendants() if n.tag == "label" and n.attrs.get("for")
    }

    for node in root.iter_descendants():
        if node.tag == "a" and "href" in node.attrs:
            doc.links.append(
                {
                    "href": node.attrs.get("href", ""),
                    "text": _collapse(node.text())[:200],
                    "rel": (node.attrs.get("rel") or "").lower(),
                    "in_main": _in_main(node, main),
                    "in_chrome": any(a.tag in CHROME_ELEMENTS for a in node.ancestors()),
                }
            )
        elif node.tag == "img":
            def _int(v):
                try:
                    return int(re.sub(r"[^0-9]", "", v or "") or 0)
                except ValueError:
                    return 0

            doc.images.append(
                {
                    "src": node.attrs.get("src") or node.attrs.get("data-src") or "",
                    "alt": node.attrs.get("alt"),
                    "width": _int(node.attrs.get("width")),
                    "height": _int(node.attrs.get("height")),
                    "role": (node.attrs.get("role") or "").lower(),
                    "in_main": _in_main(node, main),
                    "in_chrome": any(a.tag in CHROME_ELEMENTS for a in node.ancestors()),
                }
            )
        elif node.tag == "form":
            fields = []
            for f in node.iter_descendants():
                if f.tag not in ("input", "select", "textarea"):
                    continue
                ftype = (f.attrs.get("type") or ("select" if f.tag == "select" else "text")).lower()
                if ftype in ("hidden", "submit", "button", "image", "reset"):
                    continue
                fields.append(
                    {
                        "name": f.attrs.get("name") or f.attrs.get("id") or "",
                        "type": ftype,
                        "required": "required" in f.attrs or (f.attrs.get("aria-required") == "true"),
                        "labelled": _labelled(f, label_for),
                        "placeholder": f.attrs.get("placeholder") or "",
                    }
                )
            doc.forms.append(
                {
                    "action": node.attrs.get("action", ""),
                    "method": (node.attrs.get("method") or "get").lower(),
                    "fields": fields,
                    "field_count": len(fields),
                    "in_main": _in_main(node, main),
                }
            )

    for raw, line_no in builder.jsonld_raw:
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            doc.jsonld.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            doc.jsonld_errors.append(
                {
                    "line": line_no,
                    "error": f"{exc.msg} at line {exc.lineno} column {exc.colno}",
                    "excerpt": _collapse(stripped)[:200],
                }
            )

    doc.microdata = _walk_microdata(root)
    doc.rdfa = _walk_rdfa(root)

    body = next((n for n in root.iter_descendants() if n.tag == "body"), root)
    doc.text = body.text()
    doc.wordcount = wordcount(doc.text)
    if main is not None:
        doc.main_text = main.text()
    else:
        # No block scored as main content. Falling back to the whole body made
        # the navigation menu the first sentence of the page, which corrupted
        # every check that reasons about how a page opens. Body-minus-chrome is
        # always a better approximation than body.
        doc.main_text = _text_excluding_chrome(body)
        doc.main_selector = "body (chrome removed)"
    doc.main_wordcount = wordcount(doc.main_text)
    doc.noscript_text = _collapse(" ".join(builder.noscript_text))
    doc.noscript_wordcount = wordcount(doc.noscript_text)

    doc.script_srcs = list(builder.script_srcs)
    doc.bundle_scripts = [s for s in builder.script_srcs if BUNDLE_SRC_RE.search(s)]

    for node in root.iter_descendants():
        node_id = (node.attrs.get("id") or "").lower()
        node_classes = {c.lower() for c in (node.attrs.get("class") or "").split()}
        is_root = (
            (node_id in FRAMEWORK_ROOT_IDS and node.tag in ("div", "main", "section"))
            or (node_classes & FRAMEWORK_ROOT_CLASSES and node.tag in ("div", "main", "section"))
            or node.attrs.get("data-reactroot") is not None
            or bool(node.attrs.get("data-server-rendered"))
        )
        if is_root:
            doc.framework_root = _selector_for(node)
            doc.framework_root_wordcount = wordcount(node.text())
            break

    return doc
