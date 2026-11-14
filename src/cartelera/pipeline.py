"""Orquestación: ejecutar cadenas → unificar películas → escribir JSON para la web.

Salida (en `out_dir`, p.ej. docs/data/):
  index.json          cines, películas, días disponibles y estado de cada cadena
  dias/YYYY-MM-DD.json  sesiones de ese día (la web sólo carga el día que miras)

Si una cadena falla entera, se reutilizan sus sesiones futuras de la ejecución
anterior (marcadas en `estado`), para que un cambio en una web no deje la
cartelera vacía de golpe.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from .chains import TODAS, Ctx
from .cines import CINES, POR_ID
from .fetch import Fetcher
from .models import Sesion
from .normalize import limpiar_titulo
from .timeutil import MADRID

log = logging.getLogger("cartelera")


@dataclass
class Resultado:
    sesiones: list[Sesion] = field(default_factory=list)
    estado: dict[str, dict] = field(default_factory=dict)


async def ejecutar(
    cadenas: list[str], dias: int = 7, debug_dir: Path | None = None, hoy: date | None = None
) -> Resultado:
    res = Resultado()
    async with Fetcher(debug_dir=debug_dir) as fetch:
        ctx = Ctx(fetch=fetch, dias=dias, **({"hoy": hoy} if hoy else {}))

        async def una(nombre: str) -> None:
            scraper = TODAS[nombre]()
            t0 = time.monotonic()
            try:
                ses = await scraper.scrape(ctx)
                res.sesiones.extend(ses)
                res.estado[scraper.cadena] = {"ok": bool(ses), "sesiones": len(ses)}
                if not ses:
                    res.estado[scraper.cadena]["error"] = "0 sesiones"
            except Exception as e:  # una cadena rota no tumba las demás
                log.exception("%s falló", scraper.cadena)
                res.estado[scraper.cadena] = {"ok": False, "sesiones": 0, "error": repr(e)[:300]}
            res.estado[scraper.cadena]["segundos"] = round(time.monotonic() - t0, 1)
            log.info("%-10s %s", scraper.cadena, res.estado[scraper.cadena])

        await asyncio.gather(*(una(c) for c in cadenas))
    return res


# --------------------------------------------------------------------------- unificar
def _mejor_titulo(variantes: list[str]) -> str:
    """Prefiere la variante que no está TODA EN MAYÚSCULAS y es más frecuente."""
    def score(t: str) -> tuple[int, int, int]:
        letras = [c for c in t if c.isalpha()]
        mayus = sum(c.isupper() for c in letras) / max(len(letras), 1)
        return (mayus < 0.8, cnt[t], -len(t))

    cnt = Counter(variantes)
    return max(cnt, key=score)


def unificar(sesiones: list[Sesion]) -> tuple[list[dict], list[dict]]:
    """→ (peliculas, sesiones_compactas). Agrupa por slug del título limpio."""
    raw_titulos: dict[str, list[str]] = defaultdict(list)
    posters: dict[str, Counter] = defaultdict(Counter)
    duraciones: dict[str, Counter] = defaultdict(Counter)
    vistas: set[tuple] = set()
    compactas: list[dict] = []

    for s in sorted(sesiones, key=lambda s: (s.inicio, s.cine_id)):
        lt = limpiar_titulo(s.titulo)
        slug = lt.slug or "sin-titulo"
        raw_titulos[slug].append(lt.titulo)
        if s.poster:
            posters[slug][s.poster] += 1
        if s.duracion_min:
            duraciones[slug][s.duracion_min] += 1
        version = s.version or lt.version
        formatos = sorted(set(s.formatos) | set(lt.formatos))
        clave = (s.cine_id, slug, s.inicio, version, s.sala)
        if clave in vistas:
            continue
        vistas.add(clave)
        c = {"p": slug, "c": s.cine_id, "t": s.inicio.strftime("%Y-%m-%dT%H:%M")}
        if version:
            c["v"] = version
        if formatos:
            c["f"] = formatos
        if s.sala:
            c["s"] = s.sala
        if s.url:
            c["u"] = s.url
        compactas.append(c)

    peliculas = []
    for slug, tits in raw_titulos.items():
        p = {"id": slug, "titulo": _mejor_titulo(tits)}
        if posters[slug]:
            p["poster"] = posters[slug].most_common(1)[0][0]
        if duraciones[slug]:
            p["duracion"] = duraciones[slug].most_common(1)[0][0]
        peliculas.append(p)
    peliculas.sort(key=lambda p: p["titulo"].lower())
    return peliculas, compactas


# --------------------------------------------------------------------------- escribir
def _previas(out_dir: Path, cines_caidos: set[str], desde: datetime) -> list[dict]:
    """Sesiones futuras de la ejecución anterior para los cines cuya cadena ha fallado."""
    dias_dir = out_dir / "dias"
    if not cines_caidos or not dias_dir.exists():
        return []
    res = []
    lim = desde.strftime("%Y-%m-%dT%H:%M")
    for f in sorted(dias_dir.glob("*.json")):
        try:
            for s in json.loads(f.read_text(encoding="utf-8")):
                if s["c"] in cines_caidos and s["t"] >= lim:
                    res.append({**s, "prev": 1})
        except Exception:
            continue
    return res


def escribir(res: Resultado, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    ahora = datetime.now(MADRID).replace(tzinfo=None)
    peliculas, sesiones = unificar(res.sesiones)

    # Reutilizar datos previos de cadenas caídas
    caidas = {cad for cad, e in res.estado.items() if not e.get("ok")}
    cines_caidos = {c.id for c in CINES if c.cadena in caidas}
    previas = _previas(out_dir, cines_caidos, ahora)
    if previas:
        log.warning("Reutilizo %d sesiones previas de: %s", len(previas), ", ".join(caidas))
        sesiones += previas
        for cad in caidas:
            res.estado[cad]["reutilizadas"] = sum(
                1 for s in previas if POR_ID[s["c"]].cadena == cad
            )
        # Asegurar que las películas de sesiones previas existen en el índice
        old_idx = out_dir / "index.json"
        if old_idx.exists():
            old = {p["id"]: p for p in json.loads(old_idx.read_text("utf-8"))["peliculas"]}
            ids = {p["id"] for p in peliculas}
            for s in previas:
                if s["p"] not in ids and s["p"] in old:
                    peliculas.append(old[s["p"]])
                    ids.add(s["p"])

    por_dia: dict[str, list[dict]] = defaultdict(list)
    for s in sesiones:
        por_dia[s["t"][:10]].append(s)

    dias_dir = out_dir / "dias"
    dias_dir.mkdir(exist_ok=True)
    for viejo in dias_dir.glob("*.json"):
        viejo.unlink()
    for dia, lista in por_dia.items():
        lista.sort(key=lambda s: (s["t"], s["c"], s["p"]))
        (dias_dir / f"{dia}.json").write_text(
            json.dumps(lista, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )

    usados = {s["c"] for s in sesiones}
    index = {
        "generado": ahora.isoformat(timespec="minutes"),
        "dias": sorted(por_dia),
        "estado": res.estado,
        "cines": [c.model_dump(exclude_none=True) for c in CINES if c.id in usados],
        "peliculas": sorted(peliculas, key=lambda p: p["titulo"].lower()),
    }
    (out_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return index
