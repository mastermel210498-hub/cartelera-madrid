"""Descarga de páginas: httpx para HTML estático, Playwright sólo si hace falta JS.

- Un User-Agent honesto, reintentos con backoff y límite de concurrencia por host.
- Si `debug_dir` está definido, guarda cada HTML descargado (útil para depurar
  selectores rotos desde los artefactos de GitHub Actions).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:  # pragma: no cover
    from playwright.async_api import Browser, Page

log = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36 cartelera-madrid/2.0 (+https://carteleramadrid.es)"
)
HEADERS = {"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"}


class FetchError(RuntimeError):
    pass


class Fetcher:
    def __init__(self, debug_dir: Path | None = None, per_host: int = 3, retries: int = 3):
        self.debug_dir = debug_dir
        self.retries = retries
        self._sems: dict[str, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(per_host))
        self._client: Any = None
        self._pw: Any = None
        self._browser: Browser | None = None
        self._browser_lock = asyncio.Lock()

    # ------------------------------------------------------------------ HTTP
    async def __aenter__(self) -> Fetcher:
        import httpx

        self._client = httpx.AsyncClient(
            headers=HEADERS, timeout=httpx.Timeout(30.0), follow_redirects=True, http2=False
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client:
            await self._client.aclose()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def get_text(self, url: str) -> str:
        host = urlparse(url).netloc
        last: Exception | None = None
        async with self._sems[host]:
            for intento in range(1, self.retries + 1):
                try:
                    r = await self._client.get(url)
                except Exception as e:  # red, timeout... → reintentar
                    last = e
                else:
                    if r.status_code < 400:
                        self._dump(url, r.text)
                        return r.text
                    last = FetchError(f"HTTP {r.status_code}")
                    if r.status_code not in (429, 500, 502, 503, 504):
                        break  # 403/404: reintentar no sirve
                await asyncio.sleep(1.5 * intento)
        raise FetchError(f"No pude descargar {url}: {last}")

    # --------------------------------------------------------------- Browser
    async def browser(self) -> Browser:
        async with self._browser_lock:
            if self._browser is None:
                from playwright.async_api import async_playwright

                self._pw = await async_playwright().start()
                self._browser = await self._pw.chromium.launch(headless=True)
            return self._browser

    @asynccontextmanager
    async def page(self, url: str | None = None):
        """Página de Playwright ya navegada a `url` (si se da). Bloquea imágenes/fuentes."""
        browser = await self.browser()
        ctx = await browser.new_context(
            user_agent=UA, locale="es-ES", timezone_id="Europe/Madrid",
            viewport={"width": 1366, "height": 900},
        )

        async def _block(route):  # ahorra tiempo y ancho de banda
            if route.request.resource_type in ("image", "media", "font"):
                await route.abort()
            else:
                await route.continue_()

        await ctx.route("**/*", _block)
        page: Page = await ctx.new_page()
        try:
            if url:
                await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            yield page
        finally:
            await ctx.close()

    async def dump_page(self, page: Page, tag: str) -> None:
        if self.debug_dir:
            self._dump(tag, await page.content())

    # ----------------------------------------------------------------- debug
    def _dump(self, key: str, html: str) -> None:
        if not self.debug_dir:
            return
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", key)[-80:]
        h = hashlib.md5(key.encode()).hexdigest()[:6]
        (self.debug_dir / f"{slug}_{h}.html").write_text(html, encoding="utf-8")
