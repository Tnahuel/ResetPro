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

// ---------- Calificar al profesor (1 a 5 estrellas) ----------
const TEXTO_ESTRELLAS = ["", "Malo", "Regular", "Bueno", "Muy bueno", "Excelente"];

function itemValoracion(t) {
  const id = t.turno_id;
  const radios = [5, 4, 3, 2, 1].map((n) =>
    `<input type="radio" name="est-${id}" id="est-${id}-${n}" value="${n}">` +
    `<label for="est-${id}-${n}" title="${n} estrella${n > 1 ? "s" : ""}" aria-label="${n} estrella${n > 1 ? "s" : ""}">★</label>`
  ).join("");
  const detalle = [fechaLarga(t.fecha), t.rango_horario + " hs", t.grupo_muscular].filter(Boolean).join(" · ");
  return `
    <article class="rate-item" data-turno="${id}">
      <div class="rate-info">
        <b>${escapeHTML(t.profesor_nombre)}</b>
        <span>${escapeHTML(detalle)}</span>
      </div>
      <div class="rate-controls">
        <fieldset class="stars"><legend>Calificación de ${escapeHTML(t.profesor_nombre)}</legend>${radios}</fieldset>
        <span class="stars-text" aria-live="polite"></span>
        <button type="button" class="card-cta solid" disabled>Enviar calificación</button>
      </div>
    </article>`;
}

function pintarValoraciones(pendientes) {
  const card = document.getElementById("cardValoracion");
  const lista = document.getElementById("valoracionLista");
  if (!pendientes.length) {
    card.hidden = true;
    lista.innerHTML = "";
    return;
  }
  lista.innerHTML = pendientes.map(itemValoracion).join("");
  card.hidden = false;

  lista.querySelectorAll(".rate-item").forEach((item) => {
    const turnoId = Number(item.dataset.turno);
    const btn = item.querySelector("button");
    const texto = item.querySelector(".stars-text");

    item.querySelectorAll("input[type=radio]").forEach((r) =>
      r.addEventListener("change", () => {
        texto.textContent = TEXTO_ESTRELLAS[Number(r.value)];
        btn.disabled = false;
      })
    );

    btn.addEventListener("click", async () => {
      const elegida = item.querySelector("input[type=radio]:checked");
      if (!elegida) return;
      btn.disabled = true;
      try {
        await apiFetch("/valoraciones", {
          method: "POST",
          body: JSON.stringify({ turno_id: turnoId, estrellas: Number(elegida.value) }),
        });
        item.innerHTML = `<p class="rate-done">¡Gracias! Enviaste tu calificación (${elegida.value} ★).</p>`;
        setTimeout(() => {
          item.remove();
          if (!lista.querySelector(".rate-item")) card.hidden = true;
        }, 2200);
      } catch (e) {
        // Si ya estaba calificado (409), simplemente se refresca la lista.
        if (/ya calific/i.test(e.message)) {
          cargarValoraciones();
        } else {
          mostrarAviso("No pudimos enviar tu calificación: " + e.message);
          btn.disabled = false;
        }
      }
    });
  });
}

async function cargarValoraciones() {
  try {
    pintarValoraciones(await apiFetch("/valoraciones/pendientes"));
  } catch (e) {
    // La calificación es secundaria: si falla, no se muestra y el resto del panel sigue andando.
    document.getElementById("cardValoracion").hidden = true;
  }
}

async function cargar() {
  try {
    const panel = await apiFetch("/usuarios/" + sesion.id + "/panel");
    pintarEncabezado(panel.usuario.nombre);
    pintarSemana(panel);
    pintarTurno(panel);
    pintarDieta(panel);
  } catch (e) {
    mostrarAviso("No pudimos cargar tu panel: " + e.message);
  }
}

if (sesion) {
  pintarEncabezado(sesion.nombre);
  cargar();
  cargarValoraciones();
}
