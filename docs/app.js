/* Cartelera Madrid — web estática sin build.
 * Datos: data/index.json (cines, películas, días, estado) + data/dias/YYYY-MM-DD.json
 * Sesión compacta: {p: película, c: cine, t: "YYYY-MM-DDTHH:MM", v: versión, f: [formatos], s: sala, u: url, prev: 1}
 */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const DIAS_SEM = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
const MAX_PASES_COLAPSADO = 12;

const st = {
  vista: "peliculas", dia: null, q: "", cine: "", cadenas: new Set(),
  vose: false, ocultarPasadas: true, desde: 10, hasta: 24, pos: null,
};
let IDX = null, PELIS = new Map(), CINES = new Map(), CADENAS = [];
const cacheDias = new Map();
let mapa = null, capaMarcadores = null;

// ------------------------------------------------------------------ utilidades
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const urlSegura = (u) => (/^https?:\/\//i.test(u || "") ? u : null);
const norm = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const hoyISO = () => {
  const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
};
const ahoraISO = () => {
  const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
};
const hora = (t) => t.slice(11, 16);
const minutos = (t) => +t.slice(11, 13) * 60 + +t.slice(14, 16);

function km(a, b) {
  const R = 6371, r = Math.PI / 180;
  const dLat = (b.lat - a.lat) * r, dLon = (b.lon - a.lon) * r;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
}

function etiquetaDia(iso) {
  const d = new Date(iso + "T12:00:00");
  const hoy = hoyISO();
  const man = new Date(hoy + "T12:00:00"); man.setDate(man.getDate() + 1);
  if (iso === hoy) return ["Hoy", d.getDate()];
  if (iso === man.toISOString().slice(0, 10)) return ["Mañana", d.getDate()];
  return [DIAS_SEM[d.getDay()], d.getDate()];
}

// ------------------------------------------------------------------ estado ↔ URL
function leerHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get("vista")) st.vista = h.get("vista");
  if (h.get("dia")) st.dia = h.get("dia");
  st.q = h.get("q") || "";
  st.cine = h.get("cine") || "";
  st.cadenas = new Set((h.get("cadenas") || "").split(",").filter(Boolean));
  st.vose = h.get("vose") === "1";
}
function escribirHash() {
  const h = new URLSearchParams();
  if (st.vista !== "peliculas") h.set("vista", st.vista);
  if (st.dia) h.set("dia", st.dia);
  if (st.q) h.set("q", st.q);
  if (st.cine) h.set("cine", st.cine);
  if (st.cadenas.size) h.set("cadenas", [...st.cadenas].join(","));
  if (st.vose) h.set("vose", "1");
  history.replaceState(null, "", "#" + h.toString());
}

// ------------------------------------------------------------------ datos
async function cargarIndice() {
  const r = await fetch("data/index.json", { cache: "no-cache" });
  if (!r.ok) throw new Error("No hay data/index.json");
  IDX = await r.json();
  IDX.peliculas.forEach((p) => PELIS.set(p.id, p));
  IDX.cines.forEach((c) => CINES.set(c.id, c));
  CADENAS = [...new Set(IDX.cines.map((c) => c.cadena))].sort();
}
async function cargarDia(dia) {
  if (!cacheDias.has(dia)) {
    cacheDias.set(dia, fetch(`data/dias/${dia}.json`).then((r) => (r.ok ? r.json() : [])));
  }
  return cacheDias.get(dia);
}

function filtrar(sesiones) {
  const q = norm(st.q.trim());
  const ahora = ahoraISO();
  const dMin = st.desde * 60, hMax = st.hasta * 60;
  return sesiones.filter((s) => {
    const cine = CINES.get(s.c), peli = PELIS.get(s.p);
    if (!cine || !peli) return false;
    if (st.cine && s.c !== st.cine) return false;
    if (st.cadenas.size && !st.cadenas.has(cine.cadena)) return false;
    if (st.vose && !(s.v === "VOSE" || s.v === "VO")) return false;
    if (st.ocultarPasadas && s.t < ahora) return false;
    const m = minutos(s.t);
    // pases de madrugada (00:00–05:59) cuentan como "tarde" para el filtro horario
    const mm = m < 360 ? m + 1440 : m;
    if (mm < dMin || mm > hMax) return false;
    if (q && !norm(peli.titulo).includes(q)) return false;
    return true;
  });
}

// ------------------------------------------------------------------ pintar
function htmlPase(s) {
  const tags = [];
  if (s.v) tags.push(`<span class="tag v">${esc(s.v)}</span>`);
  (s.f || []).forEach((f) => tags.push(`<span class="tag">${esc(f)}</span>`));
  const pasada = s.t < ahoraISO() ? " pasada" : "";
  const prev = s.prev ? " prev" : "";
  const title = [s.s ? `Sala ${s.s}` : "", s.prev ? "dato de la ejecución anterior" : ""]
    .filter(Boolean).join(" · ");
  const u = urlSegura(s.u);
  const tag = u ? "a" : "span";
  const href = u ? ` href="${esc(u)}" target="_blank" rel="noopener"` : "";
  return `<${tag} class="pase${pasada}${prev}"${href} title="${esc(title)}">${hora(s.t)}${tags.join("")}</${tag}>`;
}

function htmlPases(lista) {
  lista.sort((a, b) => a.t.localeCompare(b.t));
  if (lista.length <= MAX_PASES_COLAPSADO) return lista.map(htmlPase).join("");
  const vis = lista.slice(0, MAX_PASES_COLAPSADO).map(htmlPase).join("");
  const resto = lista.slice(MAX_PASES_COLAPSADO).map(htmlPase).join("");
  return `${vis}<details class="mas"><summary>+${lista.length - MAX_PASES_COLAPSADO} más</summary><div class="pases">${resto}</div></details>`;
}

function ordenCines(ids) {
  return ids.sort((a, b) => {
    const A = CINES.get(a), B = CINES.get(b);
    if (st.pos && A.lat && B.lat) return km(st.pos, A) - km(st.pos, B);
    return A.nombre.localeCompare(B.nombre, "es");
  });
}
const distTxt = (c) => (st.pos && c.lat ? ` · ${km(st.pos, c).toFixed(1)} km` : "");

function agrupar(lista, clave) {
  const m = new Map();
  for (const s of lista) {
    if (!m.has(s[clave])) m.set(s[clave], []);
    m.get(s[clave]).push(s);
  }
  return m;
}

function pintarPorPelicula(lista) {
  const porPeli = agrupar(lista, "p");
  const ids = [...porPeli.keys()].sort((a, b) => porPeli.get(b).length - porPeli.get(a).length
    || PELIS.get(a).titulo.localeCompare(PELIS.get(b).titulo, "es"));
  return ids.map((pid) => {
    const p = PELIS.get(pid), ses = porPeli.get(pid);
    const porCine = agrupar(ses, "c");
    const grupos = ordenCines([...porCine.keys()]).map((cid) => {
      const c = CINES.get(cid);
      return `<div class="grupo"><div class="quien">${esc(c.nombre)}<small>${esc(c.cadena)}${distTxt(c)}</small></div>
        <div class="pases">${htmlPases(porCine.get(cid))}</div></div>`;
    }).join("");
    const poster = urlSegura(p.poster);
    const meta = [p.duracion ? `${p.duracion} min` : "", `${porCine.size} cine${porCine.size > 1 ? "s" : ""}`,
      `${ses.length} pase${ses.length > 1 ? "s" : ""}`].filter(Boolean).join(" · ");
    return `<article class="card${poster ? "" : " sin-poster"}">
      ${poster ? `<img class="poster" loading="lazy" src="${esc(poster)}" alt="" onerror="this.closest('.card').classList.add('sin-poster');this.remove()">` : ""}
      <div><h2>${esc(p.titulo)}</h2><div class="meta">${meta}</div>${grupos}</div></article>`;
  }).join("");
}

function pintarPorCine(lista) {
  const porCine = agrupar(lista, "c");
  return ordenCines([...porCine.keys()]).map((cid) => {
    const c = CINES.get(cid), ses = porCine.get(cid);
    const porPeli = agrupar(ses, "p");
    const grupos = [...porPeli.keys()]
      .sort((a, b) => PELIS.get(a).titulo.localeCompare(PELIS.get(b).titulo, "es"))
      .map((pid) => `<div class="grupo"><div class="quien">${esc(PELIS.get(pid).titulo)}</div>
        <div class="pases">${htmlPases(porPeli.get(pid))}</div></div>`).join("");
    const web = urlSegura(c.web);
    return `<article class="card sin-poster"><div>
      <h2>${web ? `<a href="${esc(web)}" target="_blank" rel="noopener">${esc(c.nombre)}</a>` : esc(c.nombre)}</h2>
      <div class="meta">${esc(c.cadena)}${distTxt(c)} · ${porPeli.size} películas · ${ses.length} pases</div>
      ${grupos}</div></article>`;
  }).join("");
}

function pintarMapa(lista) {
  if (!window.L) return;
  if (!mapa) {
    mapa = L.map("map", { zoomControl: true, attributionControl: true }).setView([40.42, -3.70], 10);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 18, attribution: "© OpenStreetMap · © CARTO",
    }).addTo(mapa);
    capaMarcadores = L.layerGroup().addTo(mapa);
  }
  capaMarcadores.clearLayers();
  const cuenta = new Map();
  lista.forEach((s) => cuenta.set(s.c, (cuenta.get(s.c) || 0) + 1));
  const pts = [];
  for (const [cid, n] of cuenta) {
    const c = CINES.get(cid);
    if (!c?.lat) continue;
    pts.push([c.lat, c.lon]);
    const sel = st.cine === cid;
    const m = L.circleMarker([c.lat, c.lon], {
      radius: Math.min(6 + Math.sqrt(n), 16), weight: sel ? 3 : 1,
      color: sel ? "#f5b942" : "#5eead4", fillColor: sel ? "#f5b942" : "#5eead4", fillOpacity: .55,
    });
    const div = document.createElement("div");
    div.innerHTML = `<strong>${esc(c.nombre)}</strong><br>${esc(c.cadena)} · ${n} pases<br>`;
    const b = document.createElement("button");
    b.className = "secundario";
    b.textContent = sel ? "Ver todos los cines" : "Ver sólo este cine";
    b.onclick = () => { st.cine = sel ? "" : cid; $("#cine").value = st.cine; mapa.closePopup(); render(); };
    div.appendChild(b);
    m.bindPopup(div).addTo(capaMarcadores);
  }
  if (st.pos) L.circleMarker([st.pos.lat, st.pos.lon], { radius: 5, color: "#fff", fillOpacity: 1 })
    .bindTooltip("Tú").addTo(capaMarcadores);
  if (pts.length && !st.cine) mapa.fitBounds(pts, { padding: [20, 20], maxZoom: 12 });
}

async function render() {
  escribirHash();
  const ses = await cargarDia(st.dia);
  const lista = filtrar(ses);
  const cont = $("#resultados");
  if (!ses.length) cont.innerHTML = `<p class="vacio">No hay datos para este día.</p>`;
  else if (!lista.length) cont.innerHTML = `<p class="vacio">Nada con estos filtros. Prueba a quitar alguno.</p>`;
  else cont.innerHTML = st.vista === "cines" ? pintarPorCine(lista) : pintarPorPelicula(lista);
  pintarMapa(lista);
}

// ------------------------------------------------------------------ UI
function montarUI() {
  // días
  const hoy = hoyISO();
  const dias = IDX.dias.filter((d) => d >= hoy);
  if (!st.dia || !dias.includes(st.dia)) st.dia = dias[0] || IDX.dias[IDX.dias.length - 1];
  $("#dias").innerHTML = dias.map((d) => {
    const [a, b] = etiquetaDia(d);
    return `<button class="dia" data-dia="${d}" aria-pressed="${d === st.dia}"><small>${a}</small><strong>${b}</strong></button>`;
  }).join("");
  $("#dias").onclick = (e) => {
    const b = e.target.closest(".dia"); if (!b) return;
    st.dia = b.dataset.dia;
    document.querySelectorAll(".dia").forEach((x) => x.setAttribute("aria-pressed", x === b));
    render();
  };

  // cines y cadenas
  $("#cine").innerHTML = `<option value="">Todos los cines</option>` +
    [...CINES.values()].sort((a, b) => a.nombre.localeCompare(b.nombre, "es"))
      .map((c) => `<option value="${esc(c.id)}">${esc(c.nombre)}</option>`).join("");
  $("#cine").value = st.cine;
  $("#cadenas").innerHTML = CADENAS.map((c) =>
    `<button class="chip" data-cadena="${esc(c)}" aria-pressed="${st.cadenas.has(c)}">${esc(c)}</button>`).join("");
  $("#cadenas").onclick = (e) => {
    const b = e.target.closest(".chip"); if (!b) return;
    const c = b.dataset.cadena;
    st.cadenas.has(c) ? st.cadenas.delete(c) : st.cadenas.add(c);
    b.setAttribute("aria-pressed", st.cadenas.has(c));
    render();
  };

  // vista
  document.querySelectorAll(".vista button").forEach((b) => {
    b.setAttribute("aria-selected", b.dataset.vista === st.vista);
    b.onclick = () => {
      st.vista = b.dataset.vista;
      document.querySelectorAll(".vista button").forEach((x) => x.setAttribute("aria-selected", x === b));
      render();
    };
  });

  // filtros
  let t;
  $("#q").value = st.q;
  $("#q").oninput = (e) => { clearTimeout(t); t = setTimeout(() => { st.q = e.target.value; render(); }, 150); };
  $("#cine").onchange = (e) => { st.cine = e.target.value; render(); };
  $("#vose").checked = st.vose;
  $("#vose").onchange = (e) => { st.vose = e.target.checked; render(); };
  $("#pasadas").onchange = (e) => { st.ocultarPasadas = e.target.checked; render(); };
  const franja = () => {
    let d = +$("#desde").value, h = +$("#hasta").value;
    if (d > h) [d, h] = [h, d];
    st.desde = d; st.hasta = h;
    $("#franja").textContent = `${String(d).padStart(2, "0")}:00 – ${h === 24 ? "24:00+" : String(h).padStart(2, "0") + ":00"}`;
  };
  $("#desde").oninput = $("#hasta").oninput = () => { franja(); clearTimeout(t); t = setTimeout(render, 120); };
  franja();
  $("#limpiar").onclick = () => {
    Object.assign(st, { q: "", cine: "", vose: false, desde: 10, hasta: 24 });
    st.cadenas.clear();
    $("#q").value = ""; $("#cine").value = ""; $("#vose").checked = false;
    $("#desde").value = 10; $("#hasta").value = 24; franja();
    document.querySelectorAll(".chip").forEach((x) => x.setAttribute("aria-pressed", false));
    render();
  };
  $("#cerca").onclick = () => {
    if (!navigator.geolocation) return;
    $("#cerca").textContent = "Buscando tu ubicación…";
    navigator.geolocation.getCurrentPosition(
      (p) => { st.pos = { lat: p.coords.latitude, lon: p.coords.longitude }; $("#cerca").textContent = "📍 Ordenado por cercanía"; render(); },
      () => { $("#cerca").textContent = "No pude obtener tu ubicación"; },
      { timeout: 10000 },
    );
  };

  // cabecera + estado de las cadenas
  const gen = new Date(IDX.generado);
  $("#actualizado").textContent = `${IDX.peliculas.length} películas · ${CINES.size} cines · actualizado ${gen.toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" })}`;
  $("#estado").innerHTML = Object.entries(IDX.estado || {}).sort().map(([cad, e]) => {
    const ok = e.ok;
    const txt = ok ? `${e.sesiones} pases` : (e.reutilizadas ? `sin actualizar (uso ${e.reutilizadas} pases de ayer)` : "sin datos hoy");
    return `<div class="${ok ? "" : "ko"}">${ok ? "✔" : "⚠"} ${esc(cad)}: ${esc(txt)}</div>`;
  }).join("");
}

(async function init() {
  try {
    leerHash();
    await cargarIndice();
    montarUI();
    await render();
  } catch (e) {
    console.error(e);
    $("#resultados").innerHTML = `<p class="vacio">No se pudieron cargar los datos (${esc(e.message)}).</p>`;
  }
})();
