"""Extracción genérica de schema.org (JSON-LD) — Odeon y Verdi lo publican.

Si una web publica `ScreeningEvent`, esto es lo más estable que hay: no depende
del diseño de la página, sólo del estándar.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any

from bs4 import BeautifulSoup


def bloques(html: str) -> list[Any]:
    soup = BeautifulSoup(html, "lxml")
    out: list[Any] = []
    for s in soup.find_all("script", type="application/ld+json"):
        txt = (s.string or s.get_text() or "").strip()
        if not txt:
            continue
        try:
            out.append(json.loads(txt))
        except json.JSONDecodeError:
            # Algunas webs dejan comas colgando o saltos raros
            limpio = re.sub(r",\s*([}\]])", r"\1", txt)
            try:
                out.append(json.loads(limpio))
            except json.JSONDecodeError:
                continue
    return out


def nodos(obj: Any) -> Iterator[dict]:
    """Recorre recursivamente todos los objetos con @type (incluye @graph y anidados)."""
    if isinstance(obj, list):
        for x in obj:
            yield from nodos(x)
    elif isinstance(obj, dict):
        if "@type" in obj:
            yield obj
        for v in obj.values():
            if isinstance(v, (list, dict)):
                yield from nodos(v)


def de_tipo(html: str, tipo: str) -> list[dict]:
    res = []
    for b in bloques(html):
        for n in nodos(b):
            t = n.get("@type")
            if t == tipo or (isinstance(t, list) and tipo in t):
                res.append(n)
    return res


def indice_por_id(html: str) -> dict[str, dict]:
    """@id → nodo, para resolver referencias {"@id": ...}."""
    idx: dict[str, dict] = {}
    for b in bloques(html):
        for n in nodos(b):
            if isinstance(n.get("@id"), str):
                idx.setdefault(n["@id"], {}).update(n)
    return idx


def resolver(ref: Any, idx: dict[str, dict]) -> dict:
    if isinstance(ref, dict):
        rid = ref.get("@id")
        if rid and rid in idx:
            return {**idx[rid], **ref}
        return ref
    if isinstance(ref, str):
        return idx.get(ref, {"@id": ref})
    return {}


def duracion_min(iso: str | None) -> int | None:
    """'PT110M' / 'PT1H50M' → 110."""
    if not iso or not isinstance(iso, str):
        return None
    m = re.fullmatch(r"P(?:T(?:(\d+)H)?(?:(\d+)M)?)", iso.strip())
    if not m:
        return None
    return int(m.group(1) or 0) * 60 + int(m.group(2) or 0) or None


def imagen(node: dict) -> str | None:
    img = node.get("image")
    if isinstance(img, list):
        img = img[0] if img else None
    if isinstance(img, dict):
        img = img.get("url") or img.get("contentUrl")
    return img if isinstance(img, str) else None
