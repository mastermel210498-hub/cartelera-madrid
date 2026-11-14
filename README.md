# Cartelera Madrid

Horarios de los cines de Madrid en una sola página. Scrapers por cadena → JSON → web estática.
Coste 0: **GitHub Actions** lo actualiza dos veces al día y **GitHub Pages** sirve la web.

```
src/cartelera/
  models.py        Sesion / Cine (pydantic): el contrato común
  cines.py         registro de cines con coordenadas (antes cines.txt)
  normalize.py     limpia títulos: "WICKED PARTE II ATMOS VOSE" → "Wicked parte ii" + VOSE + ATMOS
  fetch.py         httpx (reintentos, límite por host) + Playwright perezoso
  jsonld.py        parser genérico schema.org ScreeningEvent
  chains/          una clase por cadena (ver tabla)
  pipeline.py      ejecutar en paralelo → unificar películas → docs/data/
  cli.py           python -m cartelera …
docs/              web (HTML + JS + CSS, sin build) y docs/data/ generado
tests/             tests de parsers con HTML de ejemplo
```

| Cadena | Fuente | Técnica |
|---|---|---|
| Odeon (4) | ficha de cada peli | JSON-LD `ScreeningEvent` (httpx) |
| Verdi | portada + fichas | JSON-LD `ItemList` + `ScreeningEvent` (httpx) |
| Renoir + Princesa (3) | `/cine/<x>/cartelera/?fecha=` | HTML estático (httpx) |
| MK2 (2) | `/es/cartelera` (todos los días en una página) | HTML estático (httpx) |
| Kinépolis (2) | `Drupal.settings` incrustado en el HTML público | JSON (httpx) |
| Ocine (4) | taquilla `tickets.<dominio>` | Playwright |
| Cinesa (14), Kinépolis (2), Odeon (4) | **bloquean el acceso automatizado** (nov-2026) | sólo enlace a su web (`SOLO_ENLACE` en `chains/__init__.py`); el scraper se conserva por si dan permiso |
| ~~Yelmo~~ | ahora cineyelmo.com (Cinépolis) | **pendiente** |

Regla: sólo páginas públicas, nada de APIs internas; User-Agent identificable; concurrencia limitada.

## Uso local

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[browser,dev]" && python -m playwright install chromium
pytest -q
python -m cartelera                     # todas, 7 días → docs/data
python -m cartelera -c odeon,mk2 -d 2   # sólo algunas
python -m cartelera --debug-html debug/ # guarda el HTML para depurar
cd docs && python -m http.server 8000   # http://localhost:8000
```

## Despliegue (una vez)

1. Repo **público** en GitHub (minutos de Actions ilimitados) y subir esto a `main`.
2. *Settings → Pages*: Branch `main`, carpeta `/docs`.
3. *Settings → Actions → General → Workflow permissions*: **Read and write**.
4. *Actions → Actualizar cartelera → Run workflow* para la primera carga.

## Cuando una web cambia (pasará)

- El run sale en rojo y GitHub te manda un email, pero los datos de las cadenas que sí
  funcionan se publican igual, y la cadena rota **reutiliza sus pases de la ejecución anterior**
  (la web lo marca con ⚠ y borde discontinuo).
- Descarga el artefacto `debug-html` del run, copia el HTML a `tests/fixtures/`, escribe el test
  que falla y arregla el parser de esa cadena. Nada más se toca.

## Formato de datos

`docs/data/index.json` → `generado`, `dias`, `estado` (por cadena), `cines`, `peliculas`
`docs/data/dias/YYYY-MM-DD.json` → `[{p, c, t, v?, f?, s?, u?, prev?}]`
(película, cine, `YYYY-MM-DDTHH:MM` hora de Madrid, versión, formatos, sala, url, reutilizada)
