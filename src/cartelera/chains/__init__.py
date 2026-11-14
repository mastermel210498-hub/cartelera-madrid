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

# Cadenas que bloquean el acceso automatizado (Cloudflare "you have been blocked" / 403
# desde nov-2026). No se scrapean: la web enlaza a sus horarios. Se reactivan quitándolas
# de aquí si dan permiso o un feed.
SOLO_ENLACE: dict[str, str] = {
    "Cinesa": "https://www.cinesa.es/peliculas/",
    "Kinépolis": "https://kinepolis.es/",
    "Odeon": "https://odeonmulticines.com/",
}

ACTIVAS: dict[str, type[Scraper]] = {
    k: v for k, v in TODAS.items() if v.cadena not in SOLO_ENLACE
}

__all__ = ["ACTIVAS", "Ctx", "SOLO_ENLACE", "Scraper", "TODAS"]
