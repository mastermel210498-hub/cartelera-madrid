"""Modelo de datos común a todas las cadenas.

Cada scraper devuelve una lista de `Sesion`. Todo lo demás (agrupar por película,
deduplicar, generar el JSON de la web) se hace después, en `pipeline.py`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class Cine(BaseModel):
    id: str  # slug estable, p.ej. "odeon-alcala-norte"
    nombre: str
    cadena: str
    lat: float | None = None
    lon: float | None = None
    web: str | None = None
    zona: str | None = None  # slug de ZONAS en cines.py
    localidad: str | None = None


class Sesion(BaseModel):
    """Un pase concreto: película + cine + fecha/hora local (Europe/Madrid)."""

    cine_id: str
    titulo: str  # título tal cual lo publica la cadena (se limpia después)
    inicio: datetime  # naive, hora local de Madrid
    version: str | None = None  # "VOSE", "VO", "Castellano"... si la cadena lo indica
    formatos: list[str] = Field(default_factory=list)  # "3D", "IMAX", "4DX", "ATMOS"...
    eventos: list[str] = Field(default_factory=list)  # "Coloquio", "Sesión TETA", "Ciclo X"...
    sala: str | None = None
    url: str | None = None  # compra o ficha
    poster: str | None = None
    duracion_min: int | None = None

    @field_validator("titulo")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = " ".join((v or "").split())
        if not v:
            raise ValueError("titulo vacío")
        return v

    @field_validator("inicio")
    @classmethod
    def _naive_local(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            from .timeutil import to_madrid

            v = to_madrid(v)
        return v.replace(second=0, microsecond=0)
