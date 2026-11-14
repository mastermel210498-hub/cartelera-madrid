"""Cines Verdi Madrid — JSON-LD.

Portada: ItemList de Movie (url + póster) + ScreeningEvent de HOY.
Ficha de cada película: ScreeningEvent de toda la semana.
"""

from __future__ import annotations

import asyncio

from .. import jsonld
from ..models import Cine, Sesion
from ..normalize import version_desde_texto
from ..timeutil import parse_iso
from .base import Ctx, Scraper


def parse_portada(html: str) -> list[dict]:
    pelis: dict[str, dict] = {}
    for lista in jsonld.de_tipo(html, "ItemList"):
        for it in lista.get("itemListElement", []):
            m = it.get("item", it) if isinstance(it, dict) else {}
            url = m.get("url") or m.get("@id")
            if url and m.get("name"):
                pelis[url] = {"titulo": m["name"], "url": url, "poster": jsonld.imagen(m)}
    return list(pelis.values())


def parse_eventos(html: str, cine: Cine, poster: str | None = None) -> list[Sesion]:
    out = []
    for ev in jsonld.de_tipo(html, "ScreeningEvent"):
        if not ev.get("startDate"):
            continue
        peli = ev.get("workPresented") or {}
        oferta = ev.get("offers") or {}
        if isinstance(oferta, list):
            oferta = oferta[0] if oferta else {}
        out.append(
            Sesion(
                cine_id=cine.id,
                titulo=peli.get("name") or ev.get("name", ""),
                inicio=parse_iso(ev["startDate"]),
                version=version_desde_texto(peli.get("inLanguage", "")),
                url=oferta.get("url") or peli.get("@id"),
                poster=poster or jsonld.imagen(peli),
                duracion_min=jsonld.duracion_min(peli.get("duration")),
            )
        )
    return out


class Verdi(Scraper):
    cadena = "Verdi"

    async def scrape(self, ctx: Ctx) -> list[Sesion]:
        (cine,) = self.cines
        portada = await ctx.fetch.get_text(cine.web)
        pelis = parse_portada(portada)
        self.log.info("%s: %d películas", cine.nombre, len(pelis))

        async def ficha(p: dict) -> list[Sesion]:
            try:
                return parse_eventos(await ctx.fetch.get_text(p["url"]), cine, p["poster"])
            except Exception as e:
                self.log.warning("ficha %s: %s", p["url"], e)
                return []

        res = [s for lote in await asyncio.gather(*(ficha(p) for p in pelis)) for s in lote]
        if not res:  # plan B: al menos lo de hoy que viene en portada
            res = parse_eventos(portada, cine)
        return [s for s in res if ctx.en_rango(s.inicio.date())]
