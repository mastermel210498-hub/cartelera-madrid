"""Limpieza de títulos: separar la película de la versión/formato.

Las cadenas meten "VOSE", "3D", "ATMOS", "(digital)"... dentro del título. Aquí lo
extraemos para que "WICKED PARTE II ATMOS VOSE" y "Wicked: Parte II" sean la
misma película (clave `slug`) con distintos atributos de sesión.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import unicodedata


def unidecode(s: str) -> str:
    """Quita tildes/diacríticos (á→a, ñ→n) sin dependencias externas."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")

# (regex, tipo, valor normalizado). El orden importa: lo más largo primero.
_TOKENS: list[tuple[str, str, str]] = [
    (r"\(\s*canciones\s+(?:en\s+)?(?:v\.?o\.?s\.?e\.?|versi[oó]n\s+original|ingl[eé]s)\s*\)",
     "formato", "Canciones en VO"),
    (r"v\.?\s?o\.?\s?s\.?\s?e\.?", "version", "VOSE"),
    (r"versi[oó]n\s+original\s+subtitulada", "version", "VOSE"),
    (r"versi[oó]n\s+original", "version", "VO"),
    (r"v\.?\s?o\.?\s?s\.?", "version", "VOSE"),
    (r"v\.o\.?", "version", "VO"),
    (r"vo", "version", "VO"),
    (r"castellano|espa[nñ]ol|doblada", "version", "Castellano"),
    (r"dolby\s+atmos|atmos", "formato", "ATMOS"),
    (r"imax", "formato", "IMAX"),
    (r"4\s?dx", "formato", "4DX"),
    (r"screen\s?x", "formato", "ScreenX"),
    (r"3\s?d", "formato", "3D"),
    (r"2\s?d", "formato", None),  # ruido: se quita sin guardar
    (r"isens|i-sens", "formato", "iSens"),
    (r"laser(\s?ultra)?|l[aá]ser", "formato", "Láser"),
    (r"cinity", "formato", "CINITY"),
    (r"urban", "formato", "Urban"),
    (r"xl", "formato", "XL"),
    (r"sesi[oó]n\s+relajada", "formato", "Relajada"),
    (r"digital", "formato", None),
    (r"preestreno", "formato", "Preestreno"),
    (r"venta\s+anticipada|anticipada", "formato", None),
]

_TOKEN_RES = [
    (re.compile(rf"(?<![\w])(?:\(|\[)?\s*(?:{pat})\s*(?:\)|\])?(?![\w])", re.I), kind, val)
    for pat, kind, val in _TOKENS
]


@dataclass
class TituloLimpio:
    titulo: str
    slug: str
    version: str | None = None
    formatos: list[str] = field(default_factory=list)


def slugify(text: str) -> str:
    t = unidecode(text or "").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    return t.strip("-")


def _bonito(t: str) -> str:
    """TODO EN MAYÚSCULAS → Tipo frase (las cadenas que gritan, no las que no)."""
    letters = [c for c in t if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.8:
        t = t.lower()
        t = t[:1].upper() + t[1:]
        # Mayúscula tras ':' o '.'  ("Dune: parte tres" → "Dune: Parte tres")
        t = re.sub(r"([:.]\s+)(\w)", lambda m: m.group(1) + m.group(2).upper(), t)
    return t


# Ruido que algunas webs pegan al título: "ESTRENO ...", "... de Fulano 112 minutos No recomendada..."
_PREFIJOS = re.compile(r"^(?:estreno|preestreno|reestreno)\s+", re.I)
_COLA_FICHA = re.compile(
    r"\s+(?:de\s+[^()]+?\s+)?\d{2,3}\s*(?:min|minutos)\b.*$|\s+(?:no\s+recomendada|apta\s+para|tp)\b.*$",
    re.I,
)


def limpiar_titulo(raw: str) -> TituloLimpio:
    t = " ".join((raw or "").split())
    t = _COLA_FICHA.sub("", t)
    t = _PREFIJOS.sub("", t)
    version: str | None = None
    formatos: list[str] = []

    # Quitar sufijos de cadena tipo "Ideal - Madrid" no aplican aquí; solo título.
    changed = True
    while changed:
        changed = False
        for rx, kind, val in _TOKEN_RES:
            m = rx.search(t)
            # Sólo tokens al final o entre paréntesis: "VO" en mitad del título
            # ("Voy a pasármelo bien") no debe tocarse.
            if not m:
                continue
            tail = t[m.end():].strip(" -–:·|,")
            in_parens = m.group(0).strip().startswith(("(", "["))
            # Prefijo de versión: "VOSE WICKED PARTE II" (pero no "VO" a secas).
            prefijo = m.start() == 0 and kind == "version" and val == "VOSE" and bool(tail)
            if tail and not in_parens and not prefijo and not _solo_tokens(tail):
                continue
            t = (t[: m.start()] + " " + t[m.end():]).strip()
            if kind == "version" and val and not version:
                version = val
            elif kind == "formato" and val and val not in formatos:
                formatos.append(val)
            changed = True

    t = re.sub(r"\(\s*\)|\[\s*\]", "", t)
    t = re.sub(r"\s*[-–:·|,]+\s*$", "", t).strip()
    t = " ".join(t.split())
    if not t:  # el "título" era sólo un token: mejor dejarlo como venía
        t = " ".join((raw or "").split())
    t = _bonito(t)
    return TituloLimpio(titulo=t, slug=slugify(t), version=version, formatos=formatos)


def _solo_tokens(s: str) -> bool:
    """¿El resto del título son sólo más tokens? ('ATMOS VOSE' → sí)."""
    rest = s
    for rx, _k, _v in _TOKEN_RES:
        rest = rx.sub(" ", rest)
    return not re.sub(r"[\s\-–:·|,()\[\]]+", "", rest)


def version_desde_texto(texto: str) -> str | None:
    """Detecta versión en textos sueltos ('Versión Original Subtitulada', 'English,es')."""
    t = unidecode(texto or "").lower()
    if re.search(r"\bv\.?o\.?s\.?e?\b|subtitulad|original subt", t):
        return "VOSE"
    if re.search(r"version original|\bv\.?o\.?\b", t):
        return "VO"
    if re.search(r"castellano|espanol|doblad", t):
        return "Castellano"
    return None
