"""Ocine — la cartelera vive en la taquilla (SPA Vue) de cada cine.

https://tickets.<dominio>/?nocap=1#/SeleccioPelicula
   a[href^="#/DetallPelicula/<id>"] + h4.name           → películas
https://tickets.<dominio>/?nocap=1#/DetallPelicula/<id>
   select > option.date-option[value=YYYY-MM-DD]        → días con pases
   tr > td.sala-nom ("SALA 5") + button.btn-hora ("18:10")
"""

from __future__ import annotations

import asyncio
import re
from datetime import date
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..models import Cine, Sesion
from ..normalize import limpiar_titulo
from ..timeutil import combine, parse_hhmm
from .base import Ctx, Scraper


def taquilla(cine: Cine) -> str:
    host = urlparse(cine.web).netloc.removeprefix("www.")
    return f"https://tickets.{host}/?nocap=1#/"


def parse_lista(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    pelis: dict[str, dict] = {}
    for a in soup.select("a[href*='DetallPelicula/']"):
        m = re.search(r"DetallPelicula/(\d+)", a["href"])
        if not m or m.group(1) in pelis:
            continue
        h = a.select_one("h4") or a.find_previous("h4")
        card = a.find_parent(class_=re.compile("zitem")) or a.parent
        h = (card.select_one("h4.name") if card else None) or h
        if h and h.get_text(strip=True):
            pelis[m.group(1)] = {"id": m.group(1), "titulo": h.get_text(strip=True)}
    return list(pelis.values())


_FMT_HEAD = re.compile(r"^\s*(2D|3D|V\.?O\.?S\.?E\.?|VOSE|ATMOS|IMAX|4DX|URBAN|XL)\b", re.I)


def parse_detalle(html: str, cine: Cine, dia: date, titulo: str, url: str) -> list[Sesion]:
    soup = BeautifulSoup(html, "lxml")
    h = soup.select_one("h1, h2, .titol, .titol-peli")
    titulo = titulo or (h.get_text(strip=True) if h else "")
    out: list[Sesion] = []
    for tr in soup.select("tr"):
        sala = tr.select_one(".sala-nom")
        if not sala:
            continue
        # Cabecera de formato ("2D", "3D", "VOSE"...) que precede a la tabla
        cab = tr.find_previous(string=_FMT_HEAD)
        extra = limpiar_titulo(f"X ({cab.strip()})") if cab else None
        for b in tr.select(".btn-hora, button"):
            hhmm = parse_hhmm(b.get_text())
            if not hhmm:
                continue
            out.append(
                Sesion(
                    cine_id=cine.id,
                    titulo=titulo,
                    inicio=combine(dia, hhmm),
                    version=extra.version if extra else None,
                    formatos=extra.formatos if extra else [],
                    sala=sala.get_text(strip=True).upper().replace("SALA", "").strip() or None,
                    url=url,
                )
            )
    return out


class Ocine(Scraper):
    cadena = "Ocine"
    usa_navegador = True

    async def _cine(self, ctx: Ctx, cine: Cine) -> list[Sesion]:
        base = taquilla(cine)
        res: list[Sesion] = []
        async with ctx.fetch.page(base + "SeleccioPelicula") as page:
            try:
                await page.wait_for_selector("a[href*='DetallPelicula/']", timeout=45_000)
            except Exception:
                self.log.warning("%s: no carga la cartelera", cine.nombre)
                await ctx.fetch.dump_page(page, f"ocine_{cine.id}_error")
                return res
            pelis = parse_lista(await page.content())
            self.log.info("%s: %d películas", cine.nombre, len(pelis))

            for p in pelis:
                url = f"{base}DetallPelicula/{p['id']}"
                try:
                    await page.goto(url, wait_until="domcontentloaded")
                    await page.wait_for_selector(
                        "option.date-option, :text('No hay sesiones')", timeout=20_000
                    )
                    await page.wait_for_timeout(500)
                    fechas = await page.eval_on_selector_all(
                        "option.date-option", "els => els.map(e => e.value)"
                    )
                    for f in fechas:
                        d = date.fromisoformat(f[:10])
                        if not ctx.en_rango(d):
                            continue
                        await page.select_option("select:has(option.date-option)", f)
                        await page.wait_for_timeout(700)
                        res.extend(parse_detalle(await page.content(), cine, d, p["titulo"], url))
                except Exception as e:
                    self.log.warning("%s / %s: %s", cine.nombre, p["titulo"], e)
        return res

    async def scrape(self, ctx: Ctx) -> list[Sesion]:
        async def uno(c: Cine) -> list[Sesion]:
            try:
                return await self._cine(ctx, c)
            except Exception as e:
                self.log.warning("%s: %s", c.nombre, e)
                return []

        lotes = await asyncio.gather(*(uno(c) for c in self.cines))
        return [s for lote in lotes for s in lote]
