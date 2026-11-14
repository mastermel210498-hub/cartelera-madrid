"""Tests de los parsers con HTML de ejemplo (calcado de las webs reales, nov-2026).

Si una web cambia, guarda su HTML con `cartelera --debug-html debug/`, copia el
fichero aquí y ajusta el parser hasta que el test vuelva a pasar.
"""

from datetime import date, datetime
from pathlib import Path

import pytest

from cartelera.chains import cinesa, kinepolis, mk2, ocine, odeon, renoir, verdi
from cartelera.cines import POR_ID

FX = Path(__file__).parent / "fixtures"


def html(name: str) -> str:
    return (FX / name).read_text(encoding="utf-8")


def test_odeon_listado():
    pelis = odeon.parse_listado(html("odeon_listado.html"), "https://odeonmulticines.com/x")
    assert [p["titulo"] for p in pelis] == ["HECHIZO: BIENVENIDOS A HEXE", "LA BOLA NEGRA"]
    assert pelis[0]["poster"].endswith("width=230")  # la mayor del srcset
    assert pelis[1]["url"].startswith("https://odeonmulticines.com/")


def test_odeon_ficha_jsonld():
    s = odeon.parse_ficha(html("odeon_ficha.html"), POR_ID["odeon-alcala-norte"], "poster.jpg")
    assert len(s) == 2
    assert s[0].inicio == datetime(2026, 11, 27, 16, 0)
    assert s[0].titulo == "HECHIZO: BIENVENIDOS A HEXE"
    assert s[0].duracion_min == 110
    assert s[0].formatos == ["Láser", "CINITY"]
    assert s[1].inicio.hour == 22


def test_verdi():
    pelis = verdi.parse_portada(html("verdi_portada.html"))
    assert {p["titulo"] for p in pelis} == {"Arriba Tutto", "Hamnet"}
    s = verdi.parse_eventos(html("verdi_portada.html"), POR_ID["verdi-madrid"])
    assert [x.version for x in s] == ["Castellano", "VOSE"]
    assert s[1].inicio == datetime(2026, 11, 14, 20, 15)


def test_verdi_ficha_real_con_referencias_id():
    # Ficha real (nov-2026): workPresented = {"@id": ...} sin nombre
    s = verdi.parse_eventos(html("verdi_ficha_real.html"), POR_ID["verdi-madrid"], None, "La bola negra")
    assert len(s) > 5
    assert {x.titulo for x in s} == {"La bola negra"}
    assert s[0].duracion_min == 159


def test_renoir_solo_bloque_escritorio():
    s = renoir.parse_dia(html("renoir_dia.html"), POR_ID["renoir-retiro"], date(2026, 11, 14))
    assert len(s) == 3  # no duplica el bloque md
    assert s[0].sala == "04" and s[0].duracion_min == 155
    assert s[0].version == "Castellano"  # "Versión Original Castellano" = peli española
    assert s[2].version == "VOSE" and s[2].inicio == datetime(2026, 11, 14, 22, 30)


def test_mk2_dias_y_poster():
    s = mk2.parse_cartelera(html("mk2_cartelera.html"), POR_ID["mk2-palacio-de-hielo"],
                            date(2026, 12, 20))
    assert len(s) == 4
    assert s[0].inicio == datetime(2026, 12, 20, 15, 45)
    assert s[0].poster == "https://www.mk2palaciodehielo.es/data/fotos/jpg004on.jpg"
    assert s[2].inicio.date() == date(2026, 12, 21)  # "Mañana"
    assert s[3].inicio.date() == date(2027, 1, 3)  # cruce de año


def test_kinepolis_filtra_madrid_y_convierte_utc():
    s = kinepolis.parse_programa(html("kinepolis.html"))
    assert {x.cine_id for x in s} == {"kinepolis-ciudad-de-la-imagen", "kinepolis-diversia"}
    imax = next(x for x in s if "IMAX" in x.formatos)
    assert imax.version == "VOSE" and imax.inicio == datetime(2026, 11, 14, 19, 0)
    d4 = next(x for x in s if x.cine_id == "kinepolis-diversia")
    assert set(d4.formatos) == {"3D", "4DX"} and d4.version == "Castellano"
    assert d4.poster == "https://cdn.kinepolis.es/ES/p.jpg"
    golfa = next(x for x in s if x.titulo == "Toni Pons")
    assert golfa.inicio == datetime(2026, 11, 15, 0, 30)  # 23:30 UTC → 00:30 Madrid


def test_cinesa():
    s = cinesa.parse_pagina(html("cinesa_cine.html"), POR_ID["cinesa-proyecciones"])
    assert len(s) == 2
    assert s[0].inicio == datetime(2026, 11, 14, 16, 0) and s[0].sala == "1"
    assert s[1].version == "VOSE"
    assert s[0].url == "https://www.cinesa.es/compra/butacas/?showtimeId=018-44427"


def test_ocine():
    pelis = ocine.parse_lista(html("ocine_lista.html"))
    assert pelis == [{"id": "10876", "titulo": "Clayface"}, {"id": "11084", "titulo": "La Bola Negra"}]
    s = ocine.parse_detalle(html("ocine_detalle.html"), POR_ID["ocine-urban-xmadrid"],
                            date(2026, 11, 14), "Clayface", "u")
    assert [(x.inicio.hour, x.sala, x.version) for x in s] == [
        (18, "5", None), (22, "5", None), (20, "2", "VOSE")
    ]
    assert ocine.taquilla(POR_ID["ocine-urban-xmadrid"]) == \
        "https://tickets.ocineurbanxmadrid.es/?nocap=1#/"


@pytest.mark.parametrize("raw,titulo,version,formatos", [
    ("WICKED PARTE II ATMOS VOSE", "Wicked parte ii", "VOSE", ["ATMOS"]),
    ("VOSE WICKED PARTE II", "Wicked parte ii", "VOSE", []),
    ("Avatar: Fuego y Ceniza (3D) (VOSE)", "Avatar: Fuego y Ceniza", "VOSE", ["3D"]),
    ("La bola negra (digital)", "La bola negra", None, []),
    ("Voy a pasármelo bien", "Voy a pasármelo bien", None, []),
    ("VOLVER", "Volver", None, []),
    ("Zootrópolis 2 - Sesión relajada", "Zootrópolis 2", None, ["Relajada"]),
    ("ESTRENO DRÁCULA de Luc Besson 129 minutos No recomendada para menores de 16 años",
     "Drácula", None, []),
    ("Bugonia de Yorgos Lanthimos 118 minutos No recomendada para menores de 16 años",
     "Bugonia", None, []),
    ("Wicked: Parte II (Canciones Ingles)", "Wicked: Parte II", None, ["Canciones en VO"]),
    ("El diablo viste de Prada 2", "El diablo viste de Prada 2", None, []),
])
def test_limpiar_titulo(raw, titulo, version, formatos):
    from cartelera.normalize import limpiar_titulo

    r = limpiar_titulo(raw)
    assert (r.titulo, r.version, r.formatos) == (titulo, version, formatos)


def test_unificar_agrupa_y_deduplica():
    from cartelera.models import Sesion
    from cartelera.pipeline import unificar

    t = datetime(2026, 11, 14, 18, 0)
    ses = [
        Sesion(cine_id="a", titulo="DUNE: PARTE TRES", inicio=t, poster="p1"),
        Sesion(cine_id="b", titulo="Dune: Parte tres", inicio=t),
        Sesion(cine_id="b", titulo="Dune: Parte tres", inicio=t),  # duplicada
        Sesion(cine_id="b", titulo="Dune Parte Tres VOSE", inicio=t),
    ]
    pelis, comp = unificar(ses)
    assert [p["id"] for p in pelis] == ["dune-parte-tres"]
    assert pelis[0]["titulo"] == "Dune: Parte tres" and pelis[0]["poster"] == "p1"
    assert len(comp) == 3 and comp[-1]["v"] == "VOSE"


def test_solo_enlace_fuera_del_run_y_en_el_indice(tmp_path):
    from cartelera.chains import ACTIVAS, SOLO_ENLACE
    from cartelera.pipeline import Resultado, escribir

    assert not {"cinesa", "kinepolis", "odeon"} & set(ACTIVAS)
    idx = escribir(Resultado(), tmp_path)
    enl = [c for c in idx["cines"] if c.get("enlace")]
    assert {c["cadena"] for c in enl} == set(SOLO_ENLACE)
    assert all(c.get("web") for c in enl)
    assert [o["cadena"] for o in idx["otras_cadenas"]] == list(SOLO_ENLACE)


@pytest.mark.parametrize("raw,titulo,eventos", [
    ("Sesión Teta: Wild Horse Nine", "Wild Horse Nine", ["Sesión TETA (con bebés)"]),
    ("EL MAL PADRE [PROYECTO VIRIDIANA]", "El mal padre", ["Ciclo Proyecto Viridiana"]),
    ("DERSU UZALA (EL CAZADOR) [WILDER CINEMA]", "Dersu uzala (el cazador)", ["Ciclo Wilder Cinema"]),
    ("Scrooge y los fantasmas de la navidad - Crochet & Cine", "Scrooge y los fantasmas de la navidad",
     ["Crochet & Cine"]),
    ("La bola negra + coloquio con el equipo", "La bola negra", ["Coloquio"]),
    ("Sirat (presentación con Oliver Laxe)", "Sirat", ["Presentación"]),
    ("CLÁSICOS AL DETALLE – TALLER [RENOIR]", "Clásicos al detalle – taller", ["Taller"]),
    ("Ballet El Cascanueces desde The Royal Ballet", "Ballet El Cascanueces desde The Royal Ballet",
     ["Ballet"]),
    ("Rigoletto (Festival Arena at St. Margarethen)", "Rigoletto (Festival Arena at St. Margarethen)",
     ["Ópera y zarzuela", "Festival"]),
    ("Encuentros en la tercera fase", "Encuentros en la tercera fase", []),
])
def test_eventos(raw, titulo, eventos):
    from cartelera.normalize import limpiar_titulo

    r = limpiar_titulo(raw)
    assert (r.titulo, r.eventos) == (titulo, eventos)


def test_evento_agrupa_con_la_peli_normal():
    from cartelera.models import Sesion
    from cartelera.pipeline import unificar

    t = datetime(2026, 11, 14, 12, 0)
    pelis, comp = unificar([
        Sesion(cine_id="verdi-madrid", titulo="Wild Horse Nine", inicio=t),
        Sesion(cine_id="verdi-madrid", titulo="Sesión Teta: Wild Horse Nine", inicio=t),
    ])
    assert [p["id"] for p in pelis] == ["wild-horse-nine"]
    assert comp[1]["e"] == ["Sesión TETA (con bebés)"]
