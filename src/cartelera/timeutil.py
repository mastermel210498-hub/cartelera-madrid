from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9,
    "oct": 10, "nov": 11, "dic": 12,
}

_HHMM = re.compile(r"\b(\d{1,2})[:.h](\d{2})\b")


def today_madrid() -> date:
    return datetime.now(MADRID).date()


def to_madrid(dt: datetime) -> datetime:
    """Datetime con zona → naive en hora de Madrid."""
    return dt.astimezone(MADRID).replace(tzinfo=None)


def parse_iso(s: str) -> datetime:
    """ISO 8601 con o sin zona (acepta 'Z' y milisegundos)."""
    s = s.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    return to_madrid(dt) if dt.tzinfo else dt


def parse_hhmm(text: str) -> tuple[int, int] | None:
    m = _HHMM.search(text or "")
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 29 or mi > 59:
        return None
    return h, mi


def combine(d: date, hhmm: tuple[int, int]) -> datetime:
    """Fecha + hora. Horas >= 24 (sesiones golfas tipo '24:30') pasan al día siguiente."""
    h, m = hhmm
    extra = 0
    if h >= 24:
        h, extra = h - 24, 1
    return datetime(d.year, d.month, d.day, h, m) + timedelta(days=extra)


def infer_year(day: int, month: int, ref: date | None = None) -> date:
    """dd/mm sin año → la fecha más cercana hacia delante (cruce de año en dic→ene)."""
    ref = ref or today_madrid()
    cand = date(ref.year, month, day)
    if (ref - cand).days > 60:  # p.ej. hoy 20-dic y leemos 03/01 → año siguiente
        cand = date(ref.year + 1, month, day)
    return cand
