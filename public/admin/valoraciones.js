const sesion = exigirSesion("admin");

document.getElementById("btnSalir").addEventListener("click", (e) => {
  e.preventDefault();
  cerrarSesion();
  window.location.href = "../index.html";
});

if (sesion) {
  document.getElementById("userName").textContent = sesion.nombre;
  document.getElementById("userAvatar").textContent = iniciales(sesion.nombre);
}

const selProfe = document.getElementById("fProfe");
const inDesde = document.getElementById("fDesde");
const inHasta = document.getElementById("fHasta");
const aviso = document.getElementById("aviso");
let selectListo = false;

function estrellasHTML(n) {
  const r = Math.max(0, Math.min(5, Math.round(n)));
  return `<span class="stars-static" role="img" aria-label="${r} de 5 estrellas"><span class="on">${"★".repeat(r)}</span><span class="off">${"★".repeat(5 - r)}</span></span>`;
}

function fechaTurno(iso, hora) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("es-AR", { day: "2-digit", month: "short", year: "numeric" }) + " · " + hora;
}

function fechaHora(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-AR", { day: "2-digit", month: "short" }) + " " +
    d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
}

function pintarRanking(profesores) {
  const cont = document.getElementById("ranking");
  if (!profesores.length) {
    cont.innerHTML = `<p class="hint">Todavía no hay profesores registrados.</p>`;
    return;
  }
  cont.innerHTML = profesores.map((p) => {
    const sel = String(p.id) === selProfe.value ? " sel" : "";
    const filas = [5, 4, 3, 2, 1].map((n) => {
      const c = p.distribucion[String(n)] || 0;
      const pct = p.cantidad ? Math.round((c / p.cantidad) * 100) : 0;
      return `<div class="dist-row"><span class="n">${n} ★</span><div class="dist-bar"><div class="dist-fill" style="width:${pct}%"></div></div><span class="c">${c}</span></div>`;
    }).join("");
    const cuerpo = p.cantidad
      ? `<div class="rank-score"><span class="rank-num">${p.promedio.toFixed(1)}</span>${estrellasHTML(p.promedio)}</div>${filas}`
      : `<p class="sin-votos">Todavía sin votos</p>`;
    return `<button type="button" class="rank-card${sel}" data-id="${p.id}">
      <div class="rank-head"><span class="avatar">${escapeHTML(iniciales(p.nombre))}</span>
        <div><b>${escapeHTML(p.nombre)}</b><small>${p.cantidad} voto${p.cantidad === 1 ? "" : "s"}</small></div></div>
      ${cuerpo}</button>`;
  }).join("");

  cont.querySelectorAll(".rank-card").forEach((card) => {
    card.addEventListener("click", () => {
      selProfe.value = selProfe.value === card.dataset.id ? "" : card.dataset.id;   // tocar de nuevo = quitar filtro
      cargar();
    });
  });
}

function pintarVotos(data) {
  const tbody = document.getElementById("tbodyVotos");
  const lista = data.valoraciones;
  tbody.innerHTML = lista.length ? "" : `<tr><td colspan="6">No hay votos con estos filtros.</td></tr>`;
  lista.forEach((v) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHTML(fechaTurno(v.fecha_turno, v.hora))}</td>
      <td class="who-cell"><div class="who-flex"><span class="avatar">${escapeHTML(iniciales(v.alumno))}</span>${escapeHTML(v.alumno)}</div></td>
      <td>${escapeHTML(v.profesor)}</td>
      <td>${escapeHTML(v.grupo_muscular || "—")}</td>
      <td>${estrellasHTML(v.estrellas)} <span class="cell-sub" style="display:inline">${v.estrellas}/5</span></td>
      <td>${escapeHTML(fechaHora(v.votado_en))}</td>`;
    tbody.appendChild(tr);
  });
  document.getElementById("detalleSub").textContent = data.truncado
    ? "Se muestran los 500 votos más recientes. Usá los filtros para acotar."
    : "Del más reciente al más antiguo.";
}

async function cargar() {
  aviso.hidden = true;
  const params = new URLSearchParams();
  if (selProfe.value) params.set("profesor_id", selProfe.value);
  if (inDesde.value) params.set("desde", inDesde.value);
  if (inHasta.value) params.set("hasta", inHasta.value);
  const qs = params.toString();

  try {
    const data = await apiFetch("/admin/valoraciones" + (qs ? "?" + qs : ""));

    if (!selectListo) {   // el listado de profesores se carga una sola vez
      data.profesores.slice().sort((a, b) => a.nombre.localeCompare(b.nombre, "es")).forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = p.nombre;
        selProfe.appendChild(opt);
      });
      selectListo = true;
    }

    document.getElementById("statPromedio").textContent = data.general.promedio === null ? "–" : data.general.promedio.toFixed(1) + " ★";
    document.getElementById("statVotos").textContent = data.general.cantidad;
    document.getElementById("statProfes").textContent = data.profesores.filter((p) => p.cantidad > 0).length;
    pintarRanking(data.profesores);
    pintarVotos(data);
  } catch (e) {
    aviso.textContent = "No se pudieron cargar las valoraciones: " + e.message;
    aviso.hidden = false;
    document.getElementById("ranking").innerHTML = "";
    document.getElementById("tbodyVotos").innerHTML = `<tr><td colspan="6">—</td></tr>`;
  }
}

document.getElementById("filtros").addEventListener("submit", (e) => { e.preventDefault(); cargar(); });
document.getElementById("btnLimpiar").addEventListener("click", () => {
  selProfe.value = "";
  inDesde.value = "";
  inHasta.value = "";
  cargar();
});
selProfe.addEventListener("change", cargar);

if (sesion) cargar();
