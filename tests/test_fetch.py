from cartelera.fetch import HEADERS


def test_cabeceras_ascii():
    # httpx exige cabeceras ASCII: una tilde en el User-Agent rompe TODAS las peticiones
    for k, v in HEADERS.items():
        v.encode("ascii")
        k.encode("ascii")
