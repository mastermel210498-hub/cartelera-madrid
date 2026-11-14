from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, timedelta

from ..cines import de_cadena
from ..fetch import Fetcher
from ..models import Cine, Sesion
from ..timeutil import today_madrid


@dataclass
class Ctx:
    fetch: Fetcher
    dias: int = 7
    hoy: date = field(default_factory=today_madrid)

    def fechas(self) -> list[date]:
        return [self.hoy + timedelta(days=i) for i in range(self.dias)]

    def en_rango(self, d: date) -> bool:
        return self.hoy <= d < self.hoy + timedelta(days=self.dias)


class Scraper(ABC):
    """Una cadena de cines. Implementa `scrape` y devuelve sesiones de todos sus cines."""

    cadena: str = ""
    usa_navegador: bool = False

    def __init__(self) -> None:
        self.log = logging.getLogger(f"cartelera.{self.cadena.lower()}")

    @property
    def cines(self) -> list[Cine]:
        return de_cadena(self.cadena)

    @abstractmethod
    async def scrape(self, ctx: Ctx) -> list[Sesion]: ...
