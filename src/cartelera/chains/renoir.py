"""Cines Renoir (+ Princesa) — HTML estático, una página por cine y día.

URL: https://www.cinesrenoir.com/cine/<cine>/cartelera/?fecha=YYYY-MM-DD
Cada película es un bloque `.my-account-content` (la web lo repite para lg/md/sm:
nos quedamos con el de escritorio `.d-lg-block`).
"""

from __future__ import annotations

import asyncio
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Cine, Sesion
from ..normalize import version_desde_texto
from ..timeutil import combine, parse_hhmm
from .base import Ctx, Scraper

BASE = "https://www.cinesrenoir.com/"


def parse_dia(html: str, cine: Cine, dia: date) -> list[Sesion]:
    soup = BeautifulSoup(html, "lxml")
    bloques = soup.select(".my-account-content.d-lg-block") or soup.select(".my-account-content")
    out: list[Sesion] = []
    for b in bloques:
        a = b.select_one("a[href*='/pelicula/']")
        if not a:
            continue
        titulo = a.get_text(strip=True)
        img = b.select_one("img")
        smalls = [s.get_text(" ", strip=True) for s in b.select("small")]
        info = " · ".join(smalls)
        dur = re.search(r"(\d{2,3})\s*minutos", info)
        version = version_desde_texto(info)
        for pase in b.select(".pase-cartelera"):
            boton = pase.select_one("a")
            hhmm = parse_hhmm(boton.get_text() if boton else "")
            if not hhmm:
                continue
            sala = pase.select_one("span")
            out.append(
                Sesion(
                    cine_id=cine.id,
                    titulo=titulo,
                    inicio=combine(dia, hhmm),
                    version=version,
                    sala=(sala.get_text(strip=True).replace("sala", "").strip() if sala else None),
                    url=boton.get("href") or urljoin(BASE, a.get("href", "")),
                    poster=img.get("src") if img else None,
                    duracion_min=int(dur.group(1)) if dur else None,
                )
            )
    return out


class Renoir(Scraper):
    cadena = "Renoir"

    async def scrape(self, ctx: Ctx) -> list[Sesion]:
        async def uno(cine: Cine, dia: date) -> list[Sesion]:
            url = f"{cine.web}?fecha={dia.isoformat()}"
            try:
                return parse_dia(await ctx.fetch.get_text(url), cine, dia)
            except Exception as e:
                self.log.warning("%s %s: %s", cine.nombre, dia, e)
                return []

        tareas = [uno(c, d) for c in self.cines for d in ctx.fechas()]
        return [s for lote in await asyncio.gather(*tareas) for s in lote]
