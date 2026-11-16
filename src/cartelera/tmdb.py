"""Enriquecimiento de fichas con TMDB (The Movie Database).

Este producto usa la API de TMDB pero no está respaldado ni certificado por TMDB.

- Token en la variable de entorno TMDB_TOKEN (GitHub: Settings → Secrets → TMDB_TOKEN,
  el "API Read Access Token" v4, el largo que empieza por eyJ…).
- Caché en docs/data/tmdb.json: cada película se consulta una vez (y los "no encontrados"
  se reintentan pasados 3 días), así no repetimos llamadas en cada run.
- Sin token, no hace nada: la web funciona igual, sólo sin sinopsis/reparto.
"""

from __future__ import annotations

import json
import logging
import os
import unicodedata
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path

log = logging.getLogger("cartelera.tmdb")

API = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/"


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return " ".join("".join(ch if ch.isalnum() else " " for ch in t).split())


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def elegir(titulo: str, resultados: list[dict], hoy: date | None = None) -> dict | None:
    """Mejor candidato de /search/movie para un título de cartelera.

    Puntúa parecido del título (español u original) y cercanía de la fecha de estreno
    (lo normal es que esté en cines algo estrenado hace poco), con un plus por popularidad.
    Devuelve None si nada se parece lo suficiente.
    """
    hoy = hoy or date.today()
    mejor, mejor_p = None, 0.0
    for r in resultados[:10]:
        sim = max(_sim(titulo, r.get("title", "")), _sim(titulo, r.get("original_title", "")))
        if sim < 0.6:
            continue
        p = sim * 2
        fecha = r.get("release_date") or ""
        if len(fecha) >= 4:
            try:
                dias = abs((hoy - date.fromisoformat(fecha[:10])).days)
                p += 1.0 if dias < 200 else 0.5 if dias < 800 else 0.0  # reestrenos y clásicos: menos
            except ValueError:
                pass
        p += min((r.get("popularity") or 0) / 100, 0.5)
        if p > mejor_p:
            mejor, mejor_p = r, p
    return mejor


def ficha(det: dict) -> dict:
    """Detalle de TMDB (con credits) → lo que guardamos y mostramos."""
    cred = det.get("credits") or {}
    dirs = [c["name"] for c in cred.get("crew", []) if c.get("job") == "Director"]
    reparto = [c["name"] for c in sorted(cred.get("cast", []), key=lambda c: c.get("order", 99))[:6]]
    out = {
        "id": det["id"],
        "titulo": det.get("title"),
        "original": det.get("original_title"),
        "sinopsis": (det.get("overview") or "").strip(),
        "generos": [g["name"] for g in det.get("genres", [])],
        "director": dirs[:2],
        "reparto": reparto,
        "estreno": det.get("release_date") or None,
        "duracion": det.get("runtime") or None,
        "nota": round(det["vote_average"], 1) if det.get("vote_count", 0) >= 20 else None,
        "poster": f"{IMG}w342{det['poster_path']}" if det.get("poster_path") else None,
        "fondo": f"{IMG}w780{det['backdrop_path']}" if det.get("backdrop_path") else None,
        "url": f"https://www.themoviedb.org/movie/{det['id']}",
    }
    return {k: v for k, v in out.items() if v not in (None, [], "")}


def enriquecer(data_dir: Path, token: str | None = None, cliente=None) -> dict:
    """Completa docs/data/tmdb.json para las películas de index.json y mete el póster de
    TMDB en index.json (la app lo usa). Devuelve un pequeño resumen."""
    token = token or os.getenv("TMDB_TOKEN") or ""
    cache_f = data_dir / "tmdb.json"
    cache = json.loads(cache_f.read_text("utf-8")) if cache_f.exists() else {}
    idx_f = data_dir / "index.json"
    idx = json.loads(idx_f.read_text("utf-8"))
    hoy = date.today()
    nuevos = fallos = 0

    if token:
        if cliente is None:
            import httpx

            cliente = httpx.Client(
                base_url=API, timeout=20,
                headers={"Authorization": f"Bearer {token}", "accept": "application/json"},
            )
        for p in idx["peliculas"]:
            c = cache.get(p["id"])
            if c and (c.get("id") or c.get("no") and c["no"] > (hoy - timedelta(days=3)).isoformat()):
                continue
            try:
                r = cliente.get("/search/movie", params={"query": p["titulo"], "language": "es-ES",
                                                         "region": "ES", "include_adult": "false"})
                r.raise_for_status()
                cand = elegir(p["titulo"], r.json().get("results", []), hoy)
                if not cand:
                    cache[p["id"]] = {"no": hoy.isoformat()}
                    continue
                d = cliente.get(f"/movie/{cand['id']}", params={"language": "es-ES",
                                                                "append_to_response": "credits"})
                d.raise_for_status()
                cache[p["id"]] = ficha(d.json())
                nuevos += 1
            except Exception as e:  # TMDB caído: seguimos con lo que haya en caché
                fallos += 1
                log.warning("TMDB %s: %s", p["titulo"], e)
                if fallos > 10:
                    log.warning("Demasiados fallos de TMDB, lo dejo para el siguiente run")
                    break
        cache_f.write_text(json.dumps(cache, ensure_ascii=False, indent=0), "utf-8")

    # Los carteles se mantienen (los de las cadenas); de TMDB sólo duración y géneros
    for p in idx["peliculas"]:
        t = cache.get(p["id"]) or {}
        if t.get("duracion") and not p.get("duracion"):
            p["duracion"] = t["duracion"]
        if t.get("generos"):
            p["generos"] = t["generos"][:3]
    idx_f.write_text(json.dumps(idx, ensure_ascii=False, indent=1), "utf-8")
    con = sum(1 for p in idx["peliculas"] if (cache.get(p["id"]) or {}).get("id"))
    return {"tmdb_nuevos": nuevos, "tmdb_con_ficha": con, "peliculas": len(idx["peliculas"]),
            "fallos": fallos, "token": bool(token)}
