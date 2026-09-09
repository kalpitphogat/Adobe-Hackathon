#!/usr/bin/env python3
"""Rendered-DOM capture. Optional dependency, degrades loudly.

Three renderers share one interface:

  PlaywrightRenderer - a real headless browser. ENRICHMENT tier.
  OfflineRenderer    - serves pre-baked .rendered.html fixture pairs, so the
                       raw-versus-rendered diff logic is fully testable with no
                       browser and no network. This is what makes the two
                       critical render-stage checks provable offline.
  NullRenderer       - always returns "unavailable" and records why.

When no renderer is available the collector records a degraded capability
rather than silently skipping, and read.render.raw_text_gap becomes a
limitations[] entry instead of a finding. It never becomes a quiet pass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

__all__ = ["RenderResult", "NullRenderer", "OfflineRenderer", "PlaywrightRenderer", "build_renderer"]


@dataclass
class RenderResult:
    url: str
    html: str | None = None
    error: str | None = None
    renderer: str = "none"

    @property
    def ok(self) -> bool:
        return self.html is not None


class NullRenderer:
    name = "none"

    def __init__(self, reason: str = "no renderer configured") -> None:
        self.reason = reason

    @property
    def available(self) -> bool:
        return False

    def render(self, url: str) -> RenderResult:
        return RenderResult(url=url, error=self.reason, renderer=self.name)

    def close(self) -> None:
        return None


class OfflineRenderer:
    """Serves pre-baked rendered HTML from a fixture directory.

    Fixture sites declare a `rendered` map in _meta.json from route to file.
    A route with no entry is genuinely unrendered, which is how the
    spa_shell_norender and site_d fixtures exercise gate Rule 0b.
    """

    name = "offline-fixture"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        meta_path = self.root / "_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        self.origin = (meta.get("origin") or "").rstrip("/")
        self.map = meta.get("rendered", {})

    @property
    def available(self) -> bool:
        return bool(self.map)

    def _route(self, url: str) -> str:
        if self.origin and url.startswith(self.origin):
            return url[len(self.origin) :] or "/"
        return url

    def render(self, url: str) -> RenderResult:
        route = self._route(url)
        filename = self.map.get(route)
        if not filename:
            return RenderResult(
                url=url,
                error=f"no rendered fixture for route {route}",
                renderer=self.name,
            )
        path = self.root / filename
        if not path.exists():
            return RenderResult(url=url, error=f"missing fixture file {filename}", renderer=self.name)
        return RenderResult(url=url, html=path.read_text(encoding="utf-8"), renderer=self.name)

    def close(self) -> None:
        return None


class PlaywrightRenderer:
    """Headless Chromium via Playwright, if it is installed.

    Read-only by construction: navigation only, no clicking, no form entry, no
    script injection beyond reading document content.
    """

    name = "playwright"

    def __init__(self, timeout_ms: int = 12000, wait_until: str = "networkidle") -> None:
        self.timeout_ms = timeout_ms
        self.wait_until = wait_until
        self._pw = None
        self._browser = None
        self._error: str | None = None
        try:
            from playwright.sync_api import sync_playwright  # noqa: PLC0415
        except ImportError as exc:
            self._error = f"playwright not installed ({exc})"
            return
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
        except Exception as exc:  # noqa: BLE001 - browser download/launch can fail many ways
            self._error = f"playwright browser unavailable ({type(exc).__name__}: {exc})"
            self._teardown()

    @property
    def available(self) -> bool:
        return self._browser is not None

    def render(self, url: str) -> RenderResult:
        if not self.available:
            return RenderResult(url=url, error=self._error or "unavailable", renderer=self.name)
        context = None
        try:
            context = self._browser.new_context(
                java_script_enabled=True,
                bypass_csp=False,
                ignore_https_errors=False,
            )
            page = context.new_page()
            page.goto(url, timeout=self.timeout_ms, wait_until=self.wait_until)
            html = page.content()
            return RenderResult(url=url, html=html, renderer=self.name)
        except Exception as exc:  # noqa: BLE001 - a render failure is data, not a crash
            return RenderResult(url=url, error=f"{type(exc).__name__}: {exc}", renderer=self.name)
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:  # noqa: BLE001
                    pass

    def _teardown(self) -> None:
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:  # noqa: BLE001
                pass
            self._pw = None

    def close(self) -> None:
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:  # noqa: BLE001
                pass
            self._browser = None
        self._teardown()


def build_renderer(offline_root: Path | None = None, enable: bool = True):
    """Pick the best available renderer and report which one, and why."""
    if not enable:
        return NullRenderer("rendering disabled by --no-render")
    if offline_root is not None:
        renderer = OfflineRenderer(offline_root)
        if renderer.available:
            return renderer
        return NullRenderer("offline fixture declares no rendered pairs")
    renderer = PlaywrightRenderer()
    if renderer.available:
        return renderer
    return NullRenderer(renderer._error or "playwright unavailable")
