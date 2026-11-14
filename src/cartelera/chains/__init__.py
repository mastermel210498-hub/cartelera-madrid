from .base import Ctx, Scraper
from .cinesa import Cinesa
from .kinepolis import Kinepolis
from .mk2 import MK2
from .ocine import Ocine
from .odeon import Odeon
from .renoir import Renoir
from .verdi import Verdi

# Yelmo: yelmocines.es redirige a cineyelmo.com (Cinépolis, nov-2026). Los horarios
# sólo salen tras un flujo interactivo (ciudad → cine → aplicar). Pendiente.
TODAS: dict[str, type[Scraper]] = {
    "odeon": Odeon,
    "verdi": Verdi,
    "renoir": Renoir,
    "mk2": MK2,
    "kinepolis": Kinepolis,
    "cinesa": Cinesa,
    "ocine": Ocine,
}

__all__ = ["Ctx", "Scraper", "TODAS"]
