"""CLI.

  cartelera                       # todas las cadenas, 7 días → docs/data
  cartelera -c odeon,mk2 -d 3     # sólo algunas cadenas / días
  cartelera --debug-html debug/   # guarda el HTML descargado (para arreglar selectores)
  cartelera --check               # falla (exit 1) si alguna cadena devuelve 0 sesiones
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from .chains import ACTIVAS, TODAS
from .pipeline import ejecutar, escribir
from .sitio import generar


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cartelera", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-c", "--cadenas", default=",".join(ACTIVAS),
                    help=f"lista separada por comas (por defecto: {','.join(ACTIVAS)})")
    ap.add_argument("-d", "--dias", type=int, default=7)
    ap.add_argument("-o", "--out", type=Path, default=Path("docs/data"))
    ap.add_argument("--debug-html", type=Path, default=None)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 si alguna cadena falla (para que Actions avise)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S",
    )
    for ruidoso in ("httpx", "httpcore"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)

    cadenas = [c.strip().lower() for c in args.cadenas.split(",") if c.strip()]
    desconocidas = [c for c in cadenas if c not in TODAS]
    if desconocidas:
        ap.error(f"cadenas desconocidas: {desconocidas}")

    res = asyncio.run(ejecutar(cadenas, dias=args.dias, debug_dir=args.debug_html))
    index = escribir(res, args.out)
    if args.out.name == "data":  # docs/data → generar también las páginas estáticas de docs/
        print("páginas:", generar(args.out.parent))

    print(json.dumps(index["estado"], ensure_ascii=False, indent=1))
    total = sum(e["sesiones"] for e in index["estado"].values())
    print(f"\n{total} sesiones · {len(index['peliculas'])} películas · "
          f"{len(index['cines'])} cines · días {index['dias'][:1]}…{index['dias'][-1:]}")

    if args.check and any(not e.get("ok") for e in index["estado"].values()):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
