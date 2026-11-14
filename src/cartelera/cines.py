"""Registro de cines (sustituye a cines.txt). Coordenadas WGS84."""

from __future__ import annotations

from .models import Cine

_C = Cine

CINES: list[Cine] = [
    # Odeon
    _C(id="odeon-alcala-norte", nombre="Odeon Alcalá Norte", cadena="Odeon",
       lat=40.437118, lon=-3.638281, web="https://odeonmulticines.com/odeon-alcala-norte"),
    _C(id="odeon-sambil", nombre="Odeon Sambil", cadena="Odeon",
       lat=40.359829, lon=-3.776500, web="https://odeonmulticines.com/odeon-sambil"),
    _C(id="odeon-gran-plaza-2", nombre="Odeon Gran Plaza 2", cadena="Odeon",
       lat=40.491032, lon=-3.896931, web="https://odeonmulticines.com/odeon-gran-plaza-2"),
    _C(id="odeon-tres-cantos", nombre="Odeon Tres Cantos", cadena="Odeon",
       lat=40.599904, lon=-3.708621, web="https://odeonmulticines.com/odeon-tres-cantos"),
    # Renoir (Floridablanca es Barcelona → fuera)
    _C(id="cines-princesa", nombre="Cines Princesa", cadena="Renoir",
       lat=40.425082, lon=-3.712890, web="https://www.cinesrenoir.com/cine/cines-princesa/cartelera/"),
    _C(id="renoir-retiro", nombre="Renoir Retiro", cadena="Renoir",
       lat=40.420249, lon=-3.676168, web="https://www.cinesrenoir.com/cine/renoir-retiro/cartelera/"),
    _C(id="renoir-plaza-de-espana", nombre="Renoir Plaza de España", cadena="Renoir",
       lat=40.424559, lon=-3.713306,
       web="https://www.cinesrenoir.com/cine/renoir-plaza-de-espana/cartelera/"),
    # Kinépolis
    _C(id="kinepolis-ciudad-de-la-imagen", nombre="Kinépolis Ciudad de la Imagen",
       cadena="Kinépolis", lat=40.393971, lon=-3.796443,
       web="https://kinepolis.es/movies/overview/?complex=KMAD"),
    _C(id="kinepolis-diversia", nombre="Kinépolis Diversia", cadena="Kinépolis",
       lat=40.530245, lon=-3.639238, web="https://kinepolis.es/movies/overview/?complex=KALCO"),
    # MK2
    _C(id="mk2-palacio-de-hielo", nombre="MK2 Palacio de Hielo", cadena="MK2",
       lat=40.463319, lon=-3.635767, web="https://www.mk2palaciodehielo.es/es/cartelera"),
    _C(id="mk2-cine-paz", nombre="MK2 Cine Paz", cadena="MK2",
       lat=40.430995, lon=-3.702535, web="https://www.cinepazmadrid.es/es/cartelera"),
    # Verdi
    _C(id="verdi-madrid", nombre="Cines Verdi Madrid", cadena="Verdi",
       lat=40.436681, lon=-3.703229, web="https://madrid.cines-verdi.com/"),
    # Cinesa (id = slug de la URL /cines/<slug>/)
    _C(id="cinesa-equinoccio", nombre="Cinesa Equinoccio", cadena="Cinesa",
       lat=40.455019, lon=-3.873877, web="https://www.cinesa.es/cines/equinoccio/"),
    _C(id="cinesa-xanadu", nombre="Cinesa Xanadú", cadena="Cinesa",
       lat=40.300321, lon=-3.922880, web="https://www.cinesa.es/cines/xanadu/"),
    _C(id="cinesa-la-gavia", nombre="Cinesa La Gavia", cadena="Cinesa",
       lat=40.368221, lon=-3.596682, web="https://www.cinesa.es/cines/la-gavia/"),
    _C(id="cinesa-la-moraleja", nombre="Cinesa La Moraleja", cadena="Cinesa",
       lat=40.518697, lon=-3.654512, web="https://www.cinesa.es/cines/la-moraleja/"),
    _C(id="cinesa-las-rosas", nombre="Cinesa Las Rosas", cadena="Cinesa",
       lat=40.418772, lon=-3.619492, web="https://www.cinesa.es/cines/las-rosas/"),
    _C(id="cinesa-heron-city-las-rozas", nombre="Cinesa Heron City Las Rozas", cadena="Cinesa",
       lat=40.515969, lon=-3.895843, web="https://www.cinesa.es/cines/heron-city-las-rozas/"),
    _C(id="cinesa-plaza-loranca-2", nombre="Cinesa Plaza Loranca 2", cadena="Cinesa",
       lat=40.303019, lon=-3.831457, web="https://www.cinesa.es/cines/plaza-loranca-2/"),
    _C(id="cinesa-manoteras", nombre="Cinesa Manoteras", cadena="Cinesa",
       lat=40.486224, lon=-3.664562, web="https://www.cinesa.es/cines/manoteras/"),
    _C(id="cinesa-mendez-alvaro", nombre="Cinesa Méndez Álvaro", cadena="Cinesa",
       lat=40.397282, lon=-3.673513, web="https://www.cinesa.es/cines/mendez-alvaro/"),
    _C(id="cinesa-nassica", nombre="Cinesa Nassica", cadena="Cinesa",
       lat=40.273140, lon=-3.695161, web="https://www.cinesa.es/cines/nassica/"),
    _C(id="cinesa-oasiz", nombre="Cinesa Oasiz", cadena="Cinesa",
       lat=40.472344, lon=-3.440985, web="https://www.cinesa.es/cines/oasiz/"),
    _C(id="cinesa-parquesur", nombre="Cinesa Parquesur", cadena="Cinesa",
       lat=40.338975, lon=-3.731113, web="https://www.cinesa.es/cines/parquesur/"),
    _C(id="cinesa-proyecciones", nombre="Cinesa Proyecciones", cadena="Cinesa",
       lat=40.431616, lon=-3.702536, web="https://www.cinesa.es/cines/proyecciones/"),
    _C(id="cinesa-principe-pio", nombre="Cinesa Príncipe Pío", cadena="Cinesa",
       lat=40.423054, lon=-3.720391, web="https://www.cinesa.es/cines/principe-pio/"),
    # Ocine (la cartelera vive en la taquilla tickets.<dominio>)
    _C(id="ocine-urban-xmadrid", nombre="Ocine Urban X-Madrid (Alcorcón)", cadena="Ocine",
       lat=40.340216, lon=-3.846967, web="https://www.ocineurbanxmadrid.es/"),
    _C(id="ocine-urban-caleido", nombre="Ocine Urban Caleido", cadena="Ocine",
       lat=40.476970, lon=-3.687880, web="https://www.ocineurbancaleido.es/"),
    _C(id="ocine-quadernillos", nombre="Ocine Quadernillos (Alcalá)", cadena="Ocine",
       lat=None, lon=None, web="https://www.ocinequadernillos.es/"),
    _C(id="ocine-plaza-eboli", nombre="Ocine Plaza Éboli (Pinto)", cadena="Ocine",
       lat=40.240284, lon=-3.689650, web="https://www.ocineplazaeboli.es/"),
]

POR_ID: dict[str, Cine] = {c.id: c for c in CINES}


def de_cadena(cadena: str) -> list[Cine]:
    return [c for c in CINES if c.cadena == cadena]
