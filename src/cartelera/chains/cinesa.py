"""Cinesa — web SPA: se renderiza con Playwright la página pública de cada cine.

https://www.cinesa.es/cines/<cine>/
  li.v-showtime-picker-film-list__item          → una película
     h2.v-film-title__text, img (póster)
     a.v-showtime-button                       → un pase
        time[datetime]  (ISO en UTC, ¡muy limpio!)
        .v-showtime-button__screen-name        → "Sala 1"
        img[alt]  dentro de la lista de atributos → "Vose", "3D", "iSens"...
  button.v-date-picker-date__button             → selector de día
"""

from __future__ import annotations

import asyncio
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Cine, Sesion
from ..normalize import limpiar_titulo
from ..timeutil import parse_iso
from .base import Ctx, Scraper

BASE = "https://www.cinesa.es"
FILM = "li.v-showtime-picker-film-list__item"
DATE_BTN = "button.v-date-picker-date__button"


def parse_pagina(html: str, cine: Cine) -> list[Sesion]:
    soup = BeautifulSoup(html, "lxml")
    out: list[Sesion] = []
    for li in soup.select(FILM):
        h = li.select_one(".v-film-title__text, h2")
        if not h:
            continue
        img = li.select_one(".v-showtime-picker-film-thumbnail img, img")
        for a in li.select("a.v-showtime-button"):
            t = a.select_one("time[datetime]")
            if not t:
                continue
            attrs = [i.get("alt") or i.get("title") or "" for i in a.select(".v-attribute-list img")]
            attrs += [x.get_text(strip=True) for x in a.select(".v-attribute-list__item")]
            extra = limpiar_titulo("X " + " ".join(f"({x})" for x in attrs if x))
            sala = a.select_one(".v-showtime-button__screen-name")
            out.append(
                Sesion(
                    cine_id=cine.id,
                    titulo=h.get_text(strip=True),
                    inicio=parse_iso(t["datetime"]),
                    version=extra.version,
                    formatos=extra.formatos,
                    sala=sala.get_text(strip=True).replace("Sala", "").strip() if sala else None,
                    url=urljoin(BASE, a.get("href", "")) if a.get("href") else cine.web,
                    poster=img.get("src") if img else None,
                )
            )
    return out


async def _rechazar_cookies(page) -> None:
    for sel in ("#onetrust-reject-all-handler", "button:has-text('Rechazar')"):
        try:
            await page.click(sel, timeout=4000)
            return
        except Exception:
            continue


class Cinesa(Scraper):
    cadena = "Cinesa"
    usa_navegador = True
    paralelos = 3

    async def _cine(self, ctx: Ctx, cine: Cine) -> list[Sesion]:
        res: list[Sesion] = []
        async with ctx.fetch.page(cine.web) as page:
            await _rechazar_cookies(page)
            try:
                await page.wait_for_selector(DATE_BTN, timeout=45_000)
            except Exception:
                self.log.warning("%s: no carga el selector de fechas", cine.nombre)
                await ctx.fetch.dump_page(page, f"cinesa_{cine.id}_error")
                return res
            n = min(await page.locator(DATE_BTN).count(), ctx.dias)
            for i in range(n):
                try:
                    if i:
                        await page.locator(DATE_BTN).nth(i).click()
                    await page.wait_for_load_state("networkidle", timeout=20_000)
                    await page.wait_for_timeout(600)
                    html = await page.content()
                    res.extend(parse_pagina(html, cine))
                except Exception as e:
                    self.log.warning("%s día %d: %s", cine.nombre, i, e)
            await ctx.fetch.dump_page(page, f"cinesa_{cine.id}")
        return res

    async def scrape(self, ctx: Ctx) -> list[Sesion]:
        sem = asyncio.Semaphore(self.paralelos)

        async def uno(c: Cine) -> list[Sesion]:
            async with sem:
                try:
                    return await self._cine(ctx, c)
                except Exception as e:
                    self.log.warning("%s: %s", c.nombre, e)
                    return []

        lotes = await asyncio.gather(*(uno(c) for c in self.cines))
        return [s for lote in lotes for s in lote if ctx.en_rango(s.inicio.date())]
