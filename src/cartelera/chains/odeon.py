"""Odeon Multicines — HTML estático + JSON-LD (ScreeningEvent) en cada ficha.

Listado:  https://odeonmulticines.com/<cine>          → enlaces /producto/<slug>
Ficha:    https://odeonmulticines.com/<cine>/producto/<slug>
          → <script type="application/ld+json"> con un ScreeningEvent por pase
            (todas las fechas a la venta, con hora ISO y zona).
"""

from __future__ import annotations

import asyncio
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import jsonld
from ..models import Cine, Sesion
from ..normalize import limpiar_titulo
from ..timeutil import parse_iso
from .base import Ctx, Scraper


def _primera_url_srcset(srcset: str) -> str | None:
    partes = [p.strip().split(" ")[0] for p in (srcset or "").split(",") if p.strip()]
    return partes[-1] if partes else None  # la más grande


def parse_listado(html: str, base: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    vistos: dict[str, dict] = {}
    for a in soup.select("a[href*='/producto/']"):
        href = urljoin(base, a.get("href", ""))
        if href in vistos:
            continue
        h = a.select_one("h1, h2, h3, .visually-hidden")
        img = a.select_one("img")
        titulo = (h.get_text(strip=True) if h else "") or (img.get("alt", "") if img else "")
        poster = None
        if img:
            poster = _primera_url_srcset(img.get("srcset", "")) or img.get("src")
        if titulo:
            vistos[href] = {"titulo": titulo, "url": href, "poster": poster}
    return list(vistos.values())


def _formatos_por_pase(soup: BeautifulSoup) -> dict[str, list[str]]:
    """URL de compra → formatos de la fila ('LASER CINITY' → ['LASER', 'CINITY'])."""
    res: dict[str, list[str]] = {}
    for fila in soup.select(".item-session"):
        fmt = fila.select_one("[data-format]")
        raw = fmt.get("data-format", "").split() if fmt else []
        fmts = limpiar_titulo("X " + " ".join(f"({f})" for f in raw)).formatos
        for a in fila.select("a.btn_sesion[href]"):
            res[a["href"]] = fmts
    return res


def parse_ficha(html: str, cine: Cine, poster: str | None = None) -> list[Sesion]:
    idx = jsonld.indice_por_id(html)
    soup = BeautifulSoup(html, "lxml")
    fmts = _formatos_por_pase(soup)
    out: list[Sesion] = []
    for ev in jsonld.de_tipo(html, "ScreeningEvent"):
        if not ev.get("startDate"):
            continue
        peli = jsonld.resolver(ev.get("workPresented"), idx)
        titulo = peli.get("name") or ev.get("name", "").split(" — ")[0]
        oferta = ev.get("offers") or {}
        if isinstance(oferta, list):
            oferta = oferta[0] if oferta else {}
        url = oferta.get("url") or peli.get("url")
        out.append(
            Sesion(
                cine_id=cine.id,
                titulo=titulo,
                inicio=parse_iso(ev["startDate"]),
                formatos=fmts.get(url or "", []),
                url=url,
                poster=poster or jsonld.imagen(peli),
                duracion_min=jsonld.duracion_min(peli.get("duration")),
            )
        )
    return out


class Odeon(Scraper):
    cadena = "Odeon"

    async def scrape(self, ctx: Ctx) -> list[Sesion]:
        res: list[Sesion] = []
        for cine in self.cines:
            try:
                html = await ctx.fetch.get_text(cine.web)
            except Exception as e:
                self.log.warning("%s: %s", cine.nombre, e)
                continue
            pelis = parse_listado(html, cine.web)
            self.log.info("%s: %d películas", cine.nombre, len(pelis))

            async def ficha(p: dict, cine: Cine = cine) -> list[Sesion]:
                try:
                    return parse_ficha(await ctx.fetch.get_text(p["url"]), cine, p["poster"])
                except Exception as e:  # una ficha rota no tumba el cine
                    self.log.warning("ficha %s: %s", p["url"], e)
                    return []

            for lote in await asyncio.gather(*(ficha(p) for p in pelis)):
                res.extend(s for s in lote if ctx.en_rango(s.inicio.date()))
        return res
