"""Generación de páginas estáticas para SEO/AdSense a partir de docs/data.

  docs/pelicula/<slug>/index.html   ficha con horarios por cine (7 días)
  docs/cine/<id>/index.html         cartelera del cine (7 días)
  docs/aviso-legal/ · privacidad/ · cookies/ · sobre/
  docs/sitemap.xml · robots.txt · ads.txt (si hay ADSENSE_CLIENT)

Configuración por variables de entorno (en GitHub: Settings → Secrets and variables →
Actions → Variables):
  SITIO_DOMINIO     carteleramadrid.es
  ADSENSE_CLIENT    ca-pub-XXXXXXXXXXXXXXXX   (vacío = sin anuncios)
  SITIO_TITULAR     nombre que aparece en el aviso legal
  SITIO_CONTACTO    email de contacto público
"""

from __future__ import annotations

import html
import json
import os
import shutil
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def e(s: object) -> str:
    return html.escape(str(s or ""), quote=True)


def cfg() -> dict:
    return {
        "dominio": os.getenv("SITIO_DOMINIO", "carteleramadrid.es"),
        "adsense": os.getenv("ADSENSE_CLIENT", "").strip(),
        "titular": os.getenv("SITIO_TITULAR", "[TITULAR]"),
        "contacto": os.getenv("SITIO_CONTACTO", "[EMAIL DE CONTACTO]"),
    }


def fecha_larga(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month]}"


# --------------------------------------------------------------------------- plantilla
def pagina(c: dict, titulo: str, descripcion: str, cuerpo: str, ruta: str,
           jsonld: dict | None = None, raiz: str = "../../") -> str:
    url = f"https://{c['dominio']}/{ruta}"
    ads = (
        f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
        f'?client={e(c["adsense"])}" crossorigin="anonymous"></script>'
        if c["adsense"] else ""
    )
    ld = (f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>'
          if jsonld else "")
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title>
<meta name="description" content="{e(descripcion)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(descripcion)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎬</text></svg>">
<link rel="stylesheet" href="{raiz}styles.css">
<link rel="stylesheet" href="{raiz}sitio.css">
{ads}
{ld}
</head>
<body class="estatica">
<header class="top"><div class="marca"><h1><a href="{raiz}">Cartelera Madrid</a></h1>
<p class="muted">Horarios de cine en Madrid, en una sola página</p></div></header>
<main class="contenido">
{cuerpo}
</main>
{pie(raiz)}
</body>
</html>
"""


def pie(raiz: str) -> str:
    return f"""<footer class="muted pie">
<nav><a href="{raiz}">Cartelera</a> · <a href="{raiz}sobre/">Sobre el proyecto</a> ·
<a href="{raiz}aviso-legal/">Aviso legal</a> · <a href="{raiz}privacidad/">Privacidad</a> ·
<a href="{raiz}cookies/">Cookies</a></nav>
<p>Horarios obtenidos de las webs públicas de cada cine. Pueden cambiar: confirma siempre en la web del cine.</p>
</footer>"""


def pases_html(ses: list[dict]) -> str:
    out = []
    for s in sorted(ses, key=lambda x: x["t"]):
        tags = f'<span class="tag v">{e(s["v"])}</span>' if s.get("v") else ""
        tags += "".join(f'<span class="tag e">{e(x)}</span>' for x in s.get("e", []))
        tags += "".join(f'<span class="tag">{e(x)}</span>' for x in s.get("f", []))
        u = s.get("u") if str(s.get("u", "")).startswith("http") else None
        h = s["t"][11:16]
        out.append(f'<a class="pase" href="{e(u)}" rel="nofollow noopener" target="_blank">{h}{tags}</a>'
                   if u else f'<span class="pase">{h}{tags}</span>')
    return "".join(out)


# --------------------------------------------------------------------------- generar
def generar(docs: Path) -> dict:
    c = cfg()
    data = docs / "data"
    idx = json.loads((data / "index.json").read_text("utf-8"))
    pelis = {p["id"]: p for p in idx["peliculas"]}
    cines = {x["id"]: x for x in idx["cines"]}
    hoy = date.today().isoformat()
    dias = [d for d in idx["dias"] if d >= hoy][:7] or idx["dias"][-7:]

    por_peli: dict[str, dict[str, dict[str, list]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    por_cine: dict[str, dict[str, dict[str, list]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for d in dias:
        f = data / "dias" / f"{d}.json"
        if not f.exists():
            continue
        for s in json.loads(f.read_text("utf-8")):
            if s["p"] in pelis and s["c"] in cines:
                por_peli[s["p"]][d][s["c"]].append(s)
                por_cine[s["c"]][d][s["p"]].append(s)

    for sub in ("pelicula", "cine"):
        shutil.rmtree(docs / sub, ignore_errors=True)
    urls = [""]

    # ---- películas
    for pid, porDia in por_peli.items():
        p = pelis[pid]
        ncines = len({cid for d in porDia.values() for cid in d})
        desc = (f"Horarios de {p['titulo']} en {ncines} cine{'s' if ncines > 1 else ''} de Madrid: "
                f"sesiones de hoy y de los próximos días, versión original (VOSE) y salas.")
        bloques = []
        for d in dias:
            if d not in porDia:
                continue
            filas = "".join(
                f'<div class="grupo"><div class="quien"><a href="../../cine/{e(cid)}/">{e(cines[cid]["nombre"])}</a>'
                f'<small>{e(cines[cid]["cadena"])}</small></div><div class="pases">{pases_html(ss)}</div></div>'
                for cid, ss in sorted(porDia[d].items(), key=lambda kv: cines[kv[0]]["nombre"])
            )
            bloques.append(f"<section><h3>{e(fecha_larga(d)).capitalize()}</h3>{filas}</section>")
        poster = (f'<img class="poster grande" src="{e(p["poster"])}" alt="Cartel de {e(p["titulo"])}" loading="lazy" onerror="this.remove()">'
                  if str(p.get("poster", "")).startswith("http") else "")
        meta = " · ".join(x for x in [f"{p['duracion']} min" if p.get("duracion") else "",
                                      f"{ncines} cines en Madrid"] if x)
        cuerpo = f"""<article class="card ficha">{poster}<div>
<h2>{e(p['titulo'])}: horarios en cines de Madrid</h2><p class="meta">{e(meta)}</p>
<p>Dónde ver <strong>{e(p['titulo'])}</strong> en Madrid esta semana. Pulsa una hora para ir a la compra de entradas en la web del cine.</p>
{''.join(bloques)}
<p class="volver"><a href="../../#q={e(p['titulo'])}">Ver en la cartelera interactiva →</a></p>
</div></article>"""
        ld = {"@context": "https://schema.org", "@type": "Movie", "name": p["titulo"],
              "url": f"https://{c['dominio']}/pelicula/{pid}/"}
        if p.get("poster"):
            ld["image"] = p["poster"]
        out = docs / "pelicula" / pid
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(
            pagina(c, f"{p['titulo']} — horarios en cines de Madrid", desc, cuerpo, f"pelicula/{pid}/", ld),
            "utf-8")
        urls.append(f"pelicula/{pid}/")

    # ---- cines (incluye los de sólo enlace, con su enlace)
    for cid, cine in cines.items():
        porDia = por_cine.get(cid, {})
        if cine.get("enlace") or not porDia:
            web = cine.get("web", "")
            cuerpo = f"""<article class="card ficha"><div><h2>{e(cine['nombre'])}</h2>
<p class="meta">{e(cine['cadena'])}</p>
<p>Consulta la cartelera y los horarios de {e(cine['nombre'])} directamente en
<a href="{e(web)}" rel="noopener" target="_blank">la web de {e(cine['cadena'])} ↗</a>.</p></div></article>"""
            desc = f"Cartelera y horarios de {cine['nombre']} ({cine['cadena']}) en Madrid."
        else:
            bloques = []
            for d in dias:
                if d not in porDia:
                    continue
                filas = "".join(
                    f'<div class="grupo"><div class="quien"><a href="../../pelicula/{e(pid)}/">{e(pelis[pid]["titulo"])}</a></div>'
                    f'<div class="pases">{pases_html(ss)}</div></div>'
                    for pid, ss in sorted(porDia[d].items(), key=lambda kv: pelis[kv[0]]["titulo"].lower())
                )
                bloques.append(f"<section><h3>{e(fecha_larga(d)).capitalize()}</h3>{filas}</section>")
            npel = len({pid for d in porDia.values() for pid in d})
            desc = (f"Cartelera de {cine['nombre']} ({cine['cadena']}): {npel} películas, horarios de hoy "
                    f"y de los próximos días, sesiones en VOSE.")
            web = cine.get("web", "")
            cuerpo = f"""<article class="card ficha"><div><h2>Cartelera de {e(cine['nombre'])}</h2>
<p class="meta">{e(cine['cadena'])} · {npel} películas · <a href="{e(web)}" rel="noopener" target="_blank">web del cine ↗</a></p>
{''.join(bloques)}</div></article>"""
        ld = {"@context": "https://schema.org", "@type": "MovieTheater", "name": cine["nombre"],
              "url": f"https://{c['dominio']}/cine/{cid}/"}
        if cine.get("lat"):
            ld["geo"] = {"@type": "GeoCoordinates", "latitude": cine["lat"], "longitude": cine["lon"]}
        out = docs / "cine" / cid
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(
            pagina(c, f"{cine['nombre']} — cartelera y horarios", desc, cuerpo, f"cine/{cid}/", ld), "utf-8")
        urls.append(f"cine/{cid}/")

    # ---- páginas fijas
    for ruta, (titulo, cuerpo) in paginas_fijas(c).items():
        out = docs / ruta
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(
            pagina(c, titulo, titulo, f'<article class="card ficha legal"><div>{cuerpo}</div></article>',
                   f"{ruta}/", raiz="../"), "utf-8")
        urls.append(f"{ruta}/")

    # ---- sitemap, robots, ads.txt
    lastmod = idx.get("generado", datetime.now().isoformat())[:10]
    (docs / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>https://{c['dominio']}/{u}</loc><lastmod>{lastmod}</lastmod></url>\n" for u in urls)
        + "</urlset>\n", "utf-8")
    (docs / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nDisallow: /data/\nSitemap: https://{c['dominio']}/sitemap.xml\n", "utf-8")
    ads = docs / "ads.txt"
    if c["adsense"]:
        pub = c["adsense"].removeprefix("ca-")
        ads.write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", "utf-8")
    elif ads.exists():
        ads.unlink()

    # La app lee la configuración de anuncios desde aquí
    (data / "sitio.json").write_text(json.dumps({"adsense": c["adsense"]}), "utf-8")
    return {"paginas": len(urls), "peliculas": len(por_peli), "cines": len(cines)}


def paginas_fijas(c: dict) -> dict[str, tuple[str, str]]:
    t, m, dom = e(c["titular"]), e(c["contacto"]), e(c["dominio"])
    return {
        "sobre": ("Sobre Cartelera Madrid", f"""
<h2>Sobre Cartelera Madrid</h2>
<p>Cartelera Madrid reúne en una sola página los horarios de varios cines de Madrid para que encuentres
rápido dónde y cuándo ver una película: por película o por cine, en versión original (VOSE), por franja
horaria, cerca de ti o a medio camino entre dos personas.</p>
<p>Los horarios se actualizan automáticamente varias veces al día a partir de la información pública de
cada cine. Pueden cambiar sin aviso: confirma siempre en la web del cine antes de ir. Cada sesión enlaza a
la compra de entradas en la web oficial.</p>
<p>Algunas cadenas no permiten que mostremos sus horarios; para ellas enlazamos directamente a su web.</p>
<p>Contacto: <a href="mailto:{m}">{m}</a></p>"""),
        "aviso-legal": ("Aviso legal", f"""
<h2>Aviso legal</h2>
<p>En cumplimiento de la Ley 34/2002 de Servicios de la Sociedad de la Información y de Comercio
Electrónico (LSSI-CE) se informa:</p>
<ul><li>Titular: {t}</li><li>Contacto: <a href="mailto:{m}">{m}</a></li><li>Sitio web: {dom}</li></ul>
<p>Los horarios, títulos y carteles se muestran con fines informativos y pertenecen a sus respectivos
titulares. Los horarios pueden contener errores o cambiar sin previo aviso; el titular no se hace
responsable de las decisiones tomadas en base a ellos. Los enlaces a webs de terceros no implican
relación ni responsabilidad sobre sus contenidos.</p>
<p>Si eres titular de algún contenido y deseas que se retire, escribe a <a href="mailto:{m}">{m}</a> y se
atenderá a la mayor brevedad.</p>"""),
        "privacidad": ("Política de privacidad", f"""
<h2>Política de privacidad</h2>
<p><strong>Responsable:</strong> {t} (<a href="mailto:{m}">{m}</a>).</p>
<p><strong>Datos que tratamos:</strong> esta web no tiene registro de usuarios ni formularios. Si usas
«cerca de mí» o «quedar a medio camino», tu ubicación se procesa sólo en tu navegador y no se envía a
ningún servidor.</p>
<p><strong>Publicidad:</strong> esta web puede mostrar anuncios de Google AdSense. Google y sus socios
pueden usar cookies e identificadores para mostrar anuncios, personalizados o no según tu consentimiento,
y para medir su rendimiento. Más información en
<a href="https://policies.google.com/technologies/partner-sites" rel="noopener">cómo usa Google los datos</a>.
Puedes gestionar tu consentimiento en cualquier momento desde el enlace de preferencias de privacidad.</p>
<p><strong>Alojamiento:</strong> la web se sirve desde GitHub Pages (GitHub, Inc.), que puede registrar la
IP de las visitas por motivos de seguridad.</p>
<p><strong>Derechos:</strong> puedes ejercer tus derechos de acceso, rectificación, supresión, oposición,
limitación y portabilidad escribiendo a <a href="mailto:{m}">{m}</a>, y reclamar ante la Agencia Española
de Protección de Datos (aepd.es).</p>"""),
        "cookies": ("Política de cookies", f"""
<h2>Política de cookies</h2>
<p>Esta web no usa cookies propias. Usa cookies de terceros sólo si das tu consentimiento:</p>
<ul><li><strong>Google AdSense</strong> (publicidad): para mostrar y medir anuncios, personalizados o no.</li>
<li><strong>Mapa</strong> (OpenStreetMap/CARTO): carga teselas del mapa; no instala cookies de seguimiento.</li></ul>
<p>Al entrar se muestra un aviso de consentimiento (CMP certificada por Google) donde puedes aceptar,
rechazar o configurar las cookies. Puedes cambiar tu elección en cualquier momento desde el enlace de
preferencias del aviso, o borrar las cookies desde la configuración de tu navegador.</p>
<p>Contacto: <a href="mailto:{m}">{m}</a></p>"""),
    }
