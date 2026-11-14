"""Kinépolis — todo el programa viene incrustado en el HTML público.

https://kinepolis.es/?main_section=hoy  (≈10 MB)
  <script>jQuery.extend(Drupal.settings, {... "variables": {"current_movies":
      {"sessions": [...], "films": [...]}}})</script>

Cada sesión: complexOperator (KMAD, KALCO...), showtime en UTC, hall,
rawSessionAttributes ("2D,English,es" → VOSE; "3D,4DX,nosubt,Spanish" → 3D+4DX).
"""

from __future__ import annotations

import json
import re

from ..models import Sesion
from ..timeutil import parse_iso
from .base import Ctx, Scraper

URL = "https://kinepolis.es/?main_section=hoy"
IMG_BASE = "https://cdn.kinepolis.es"

# código de complejo → id en cines.py
COMPLEJOS = {"KMAD": "kinepolis-ciudad-de-la-imagen", "KALCO": "kinepolis-diversia"}

_SETTINGS = re.compile(r"jQuery\.extend\(Drupal\.settings,\s*(\{.*?\})\);\s*</script>", re.S)

_FORMATOS = {
    "3D": "3D", "IMAX": "IMAX", "4DX": "4DX", "ScreenX": "ScreenX",
    "LASERULTRA": "Láser", "DolbyAtmos": "ATMOS", "ATMOS": "ATMOS",
}


def _programa(html: str) -> dict:
    for m in _SETTINGS.finditer(html):
        txt = m.group(1)
        if '"current_movies"' not in txt:
            continue
        return json.loads(txt)["variables"]["current_movies"]
    raise ValueError("No encuentro current_movies en Drupal.settings (¿ha cambiado la web?)")


def _version(attrs: list[str]) -> str | None:
    a = {x.lower() for x in attrs}
    if "spanish" in a and "nosubt" in a:
        return "Castellano"
    if "es" in a and "spanish" not in a:
        return "VOSE"
    if "nosubt" in a and "spanish" not in a:
        return "VO"
    return None


def _poster(film: dict) -> str | None:
    for im in film.get("images") or []:
        if im.get("mediaType") == "Poster Graphic" and im.get("url"):
            return IMG_BASE + im["url"]
    return None


def parse_programa(html: str) -> list[Sesion]:
    prog = _programa(html)
    films = {f["id"]: f for f in prog.get("films", []) if f.get("id")}
    out: list[Sesion] = []
    for s in prog.get("sessions", []):
        cine_id = COMPLEJOS.get(s.get("complexOperator"))
        if not cine_id or not s.get("showtime"):
            continue
        film = films.get((s.get("film") or {}).get("id"), {})
        titulo = film.get("title") or film.get("name")
        if not titulo:
            continue
        attrs = [x.strip() for x in (s.get("rawSessionAttributes") or "").split(",") if x.strip()]
        out.append(
            Sesion(
                cine_id=cine_id,
                titulo=titulo,
                inicio=parse_iso(s["showtime"]),
                version=_version(attrs),
                formatos=[_FORMATOS[a] for a in attrs if a in _FORMATOS],
                sala=str(s["hall"]) if s.get("hall") is not None else None,
                url=f"https://kinepolis.es/movies/overview/?complex={s['complexOperator']}",
                poster=_poster(film),
                duracion_min=film.get("duration") or None,
            )
        )
    return out


class Kinepolis(Scraper):
    cadena = "Kinépolis"

    async def scrape(self, ctx: Ctx) -> list[Sesion]:
        html = await ctx.fetch.get_text(URL)
        return [s for s in parse_programa(html) if ctx.en_rango(s.inicio.date())]
