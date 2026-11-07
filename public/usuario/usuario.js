const sesion = exigirSesion("usuario");

document.getElementById("btnSalir").addEventListener("click", (e) => {
  e.preventDefault();
  cerrarSesion();
  window.location.href = "../index.html";
});

const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
const DIAS_LARGO = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];

function fechaLarga(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  const f = new Date(y, m - 1, d);
  return DIAS_LARGO[f.getDay()] + " " + d + " de " + MESES[m - 1];
}

function mostrarAviso(texto) {
  const aviso = document.getElementById("aviso");
  aviso.textContent = texto;
  aviso.hidden = false;
}

function pintarEncabezado(nombre) {
  document.getElementById("userName").textContent = nombre;
  document.getElementById("userAvatar").textContent = iniciales(nombre);
  document.getElementById("saludoNombre").textContent = nombre.split(" ")[0];
}

function pintarSemana(panel) {
  const strip = document.getElementById("weekStrip");
  strip.innerHTML = panel.semana.map((d) =>
    `<div class="day-chip${d.hoy ? " today" : ""}"><span class="d">${d.dia}</span><span class="m">${escapeHTML(d.grupo || "—")}</span></div>`
  ).join("");

  const grupo = panel.grupo_hoy;
  document.getElementById("hoyGrupo").textContent = grupo || "Día libre";
  document.getElementById("hoyNota").textContent = grupo
    ? "Rutina asignada por tu profesor"
    : "No tenés un turno asignado para hoy";

  const btn = document.getElementById("btnRutina");
  if (panel.rutina) {
    btn.disabled = false;
    btn.textContent = "Descargar rutina (PDF)";
    btn.onclick = () => descargarArchivo(panel.rutina.id, panel.rutina.nombre).catch((e) => mostrarAviso(e.message));
  }
}

function pintarTurno(panel) {
  const body = document.getElementById("turnoBody");
  const btnCancelar = document.getElementById("btnCancelar");
  const t = panel.proximo_turno;
  if (!t) {
    body.innerHTML = `<p class="empty">No tenés turnos próximos. Tu administrador puede asignarte uno.</p>`;
    btnCancelar.hidden = true;
    return;
  }
  const etiqueta = t.fecha === panel.hoy ? "Hoy" : fechaLarga(t.fecha);
  body.innerHTML = `
    <div class="turno-block">
      <div class="turno-time">
        <span class="hora">${escapeHTML(t.rango_horario)}</span>
        <span class="fecha">${escapeHTML(etiqueta)}</span>
      </div>
      <div class="turno-meta">
        <div><b>${escapeHTML(t.grupo_muscular || "A definir")}</b>Grupo muscular</div>
        <div><b>Chacabuco 472</b>Ubicación</div>
      </div>
      <div class="turno-prof">
        <div class="avatar">${escapeHTML(iniciales(t.profesor_nombre))}</div>
        <div class="info">
          <b>${escapeHTML(t.profesor_nombre)}</b>
          <span>Profesor asignado</span>
        </div>
      </div>
    </div>`;
  btnCancelar.hidden = false;
  btnCancelar.onclick = async () => {
    if (!confirm("¿Cancelar este turno?")) return;
    btnCancelar.disabled = true;
    try {
      await apiFetch("/turnos/" + t.id + "/cancelar", { method: "PATCH" });
      await cargar();
    } catch (e) {
      mostrarAviso(e.message);
    } finally {
      btnCancelar.disabled = false;
    }
  };
}

function pintarDieta(panel) {
  const body = document.getElementById("dietaBody");
  const d = panel.dieta;
  const btn = document.getElementById("btnDieta");

  if (!d) {
    body.innerHTML = `<p class="empty">Todavía no tenés un plan nutricional cargado.</p>`;
  } else {
    const p = d.proteina || 0, c = d.carbohidratos || 0, g = d.grasas || 0;
    const kcalP = p * 4, kcalC = c * 4, kcalG = g * 9;
    const total = kcalP + kcalC + kcalG;
    const pct = (k) => (total ? Math.round((k / total) * 100) : 0);
    const fila = (label, gramos, k) => `
      <div class="macro-row">
        <span class="macro-label">${label}</span>
        <div class="macro-bar"><div class="macro-fill" style="width:${pct(k)}%"></div></div>
        <span class="macro-val">${Math.round(gramos)} g <small>${pct(k)}%</small></span>
      </div>`;
    body.innerHTML =
      fila("Proteínas", p, kcalP) + fila("Carbohidratos", c, kcalC) + fila("Grasas", g, kcalG) +
      `<div class="cal-summary"><span class="label">Calorías del plan${d.tipo_dieta ? " · " + escapeHTML(d.tipo_dieta) : ""}</span><span class="kcal">${Math.round(total).toLocaleString("es-AR")} kcal</span></div>` +
      (d.micros ? `<p class="macro-note"><b>Micros:</b> ${escapeHTML(d.micros)}</p>` : "");
  }

  if (panel.dieta_pdf) {
    btn.disabled = false;
    btn.textContent = "Descargar plan completo (PDF)";
    btn.onclick = () => descargarArchivo(panel.dieta_pdf.id, panel.dieta_pdf.nombre).catch((e) => mostrarAviso(e.message));
  } else if (d && d.enlace_externo) {
    btn.disabled = false;
    btn.textContent = "Ver plan completo";
    btn.onclick = () => window.open(d.enlace_externo, "_blank", "noopener");
  }
}

// ---------- Encuesta de 1 a 5 estrellas por turno realizado ----------
function pintarValoraciones(panel) {
  const seccion = document.getElementById("valorarSeccion");
  const lista = document.getElementById("valorarLista");
  const pendientes = panel.por_valorar || [];
  lista.innerHTML = "";
  seccion.hidden = !pendientes.length;
  pendientes.forEach((t) => lista.appendChild(crearItemValoracion(t, panel.hoy)));
}

function crearItemValoracion(t, hoyIso) {
  let valor = 0;
  const cuando = t.fecha === hoyIso ? "Hoy" : fechaLarga(t.fecha);
  const item = document.createElement("div");
  item.className = "rate-item";
  item.innerHTML = `
    <div class="rate-info">
      <b>${escapeHTML(t.profesor_nombre)}</b>
      <span>${escapeHTML(cuando)} · ${escapeHTML(t.rango_horario)}${t.grupo_muscular ? " · " + escapeHTML(t.grupo_muscular) : ""}</span>
    </div>
    <div class="stars" role="radiogroup" aria-label="Calificación de 1 a 5 estrellas">
      ${[1, 2, 3, 4, 5].map((n) =>
        `<button type="button" class="star" role="radio" aria-checked="false" data-v="${n}" aria-label="${n} ${n === 1 ? "estrella" : "estrellas"}">★</button>`
      ).join("")}
    </div>
    <button type="button" class="card-cta solid rate-send" disabled>Enviar</button>
    <p class="rate-msg" role="status"></p>`;

  const estrellas = [...item.querySelectorAll(".star")];
  const enviar = item.querySelector(".rate-send");
  const msg = item.querySelector(".rate-msg");
  const pintar = (hasta) => estrellas.forEach((s) => s.classList.toggle("on", Number(s.dataset.v) <= hasta));

  estrellas.forEach((s) => {
    s.addEventListener("click", () => {
      valor = Number(s.dataset.v);
      pintar(valor);
      estrellas.forEach((x) => x.setAttribute("aria-checked", String(Number(x.dataset.v) === valor)));
      enviar.disabled = false;
      msg.textContent = "";
    });
    s.addEventListener("mouseenter", () => pintar(Number(s.dataset.v)));
  });
  item.querySelector(".stars").addEventListener("mouseleave", () => pintar(valor));

  enviar.addEventListener("click", async () => {
    if (!valor) return;
    enviar.disabled = true;
    enviar.textContent = "Enviando...";
    try {
      await apiFetch("/turnos/" + t.id + "/valorar", { method: "POST", body: JSON.stringify({ estrellas: valor }) });
      item.innerHTML = `<p class="rate-thanks">¡Gracias por tu calificación! ${"★".repeat(valor)}</p>`;
      setTimeout(() => {
        item.remove();
        if (!document.querySelector("#valorarLista .rate-item")) document.getElementById("valorarSeccion").hidden = true;
      }, 2200);
    } catch (e) {
      msg.textContent = e.message;
      msg.classList.add("err");
      enviar.disabled = false;
      enviar.textContent = "Enviar";
    }
  });
  return item;
}

async function cargar() {
  try {
    const panel = await apiFetch("/usuarios/" + sesion.id + "/panel");
    pintarEncabezado(panel.usuario.nombre);
    pintarSemana(panel);
    pintarTurno(panel);
    pintarDieta(panel);
    pintarValoraciones(panel);
  } catch (e) {
    mostrarAviso("No pudimos cargar tu panel: " + e.message);
  }
}

if (sesion) {
  pintarEncabezado(sesion.nombre);
  cargar();
}
