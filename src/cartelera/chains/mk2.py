"""MK2 (Palacio de Hielo, Cine Paz) — HTML estático con TODOS los días.

https://www.<dominio>/es/cartelera
  .rotulo_dia.rotulo_diaN       → "Hoy" / "Mañana" / "Lunes 16/11"
  .contenedor_cines.cines-N     → películas de ese día
     .horarios > .peli (título, póster) + .horas a.btn (HH:MM)
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Cine, Sesion
from ..timeutil import combine, infer_year, parse_hhmm
from .base import Ctx, Scraper


def _fecha_rotulo(txt: str, hoy: date) -> date | None:
    t = txt.strip().lower()
    if t.startswith("hoy"):
        return hoy
    if t.startswith("mañana") or t.startswith("manana"):
        return hoy + timedelta(days=1)
    m = re.search(r"(\d{1,2})/(\d{1,2})", t)
    return infer_year(int(m.group(1)), int(m.group(2)), hoy) if m else None


def parse_cartelera(html: str, cine: Cine, hoy: date) -> list[Sesion]:
    soup = BeautifulSoup(html, "lxml")
    base = (soup.select_one("base") or {}).get("href") or cine.web
    dias: dict[str, date] = {}
    for r in soup.select(".rotulo_dia"):
        n = r.get("data-num")
        f = _fecha_rotulo(r.get_text(), hoy)
        if n is not None and f:
            dias[n] = f

    out: list[Sesion] = []
    for cont in soup.select(".contenedor_cines"):
        m = re.search(r"\bcines-(\d+)\b", " ".join(cont.get("class", [])))
        if not m or m.group(1) not in dias:
            continue
        dia = dias[m.group(1)]
        for h in cont.select(".horarios"):
            peli = h.select_one(".peli")
            tnode = peli.select_one("b") if peli else None
            if not tnode:
                continue
            ficha = peli.select_one("a[href]")
            img = peli.select_one("img")
            dur = re.search(r"(\d{2,3})\s*minutos", peli.get_text(" "))
            for a in h.select(".horas a"):
                hhmm = parse_hhmm(a.get_text())
                if not hhmm:
                    continue
                out.append(
                    Sesion(
                        cine_id=cine.id,
                        titulo=tnode.get_text(strip=True),
                        inicio=combine(dia, hhmm),
                        url=a.get("href") or (ficha.get("href") if ficha else None),
                        poster=urljoin(base, img["src"]) if img and img.get("src") else None,
                        duracion_min=int(dur.group(1)) if dur else None,
                    )
                )
    return out


class MK2(Scraper):
    cadena = "MK2"

    async def scrape(self, ctx: Ctx) -> list[Sesion]:
        res: list[Sesion] = []
        for cine in self.cines:
            try:
                html = await ctx.fetch.get_text(cine.web)
            except Exception as e:  # un cine caído no tumba la cadena
                self.log.warning("%s: %s", cine.nombre, e)
                continue
            ses = parse_cartelera(html, cine, ctx.hoy)
            self.log.info("%s: %d sesiones", cine.nombre, len(ses))
            res.extend(s for s in ses if ctx.en_rango(s.inicio.date()))
        return res
