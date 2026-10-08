const sesion = exigirSesion("profesor");

document.getElementById("btnSalir").addEventListener("click", (e) => {
  e.preventDefault();
  cerrarSesion();
  window.location.href = "../index.html";
});

const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
const DIAS_LARGO = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];

function etiquetaDia(iso, hoyIso) {
  const [y, m, d] = iso.split("-").map(Number);
  const f = new Date(y, m - 1, d);
  const base = DIAS_LARGO[f.getDay()] + " " + d + " de " + MESES[m - 1];
  if (iso === hoyIso) return "Hoy · " + base;
  const man = new Date(hoyIso + "T00:00:00");
  man.setDate(man.getDate() + 1);
  const manIso = man.getFullYear() + "-" + String(man.getMonth() + 1).padStart(2, "0") + "-" + String(man.getDate()).padStart(2, "0");
  return (iso === manIso ? "Mañana · " : "") + base;
}

function mostrarAviso(texto) {
  const a = document.getElementById("aviso");
  a.textContent = texto;
  a.hidden = !texto;
}

document.getElementById("userName").textContent = sesion ? sesion.nombre : "";
if (sesion) {
  document.getElementById("userAvatar").textContent = iniciales(sesion.nombre);
  document.getElementById("saludoNombre").textContent = sesion.nombre.split(" ")[0];
}

const fileInput = document.getElementById("fileInput");
let alumnoParaSubir = null;

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  const alumno = alumnoParaSubir;
  fileInput.value = "";
  if (!file || !alumno) return;
  mostrarAviso("");
  try {
    await subirArchivo(alumno, "rutina", file);
    await cargar();
  } catch (e) {
    mostrarAviso("No se pudo subir la rutina: " + e.message);
  }
});

function pintar(data) {
  const lista = document.getElementById("alumnosList");
  const turnos = data.turnos;

  document.getElementById("statHoy").textContent = turnos.filter((t) => t.fecha === data.hoy).length;
  document.getElementById("statSemana").textContent = turnos.length;
  document.getElementById("statSinRutina").textContent = new Set(turnos.filter((t) => !t.rutina).map((t) => t.usuario_id)).size;

  if (!turnos.length) {
    lista.innerHTML = `<p class="empty">No tenés turnos asignados en los próximos días.</p>`;
    return;
  }

  let html = "";
  let diaActual = null;
  turnos.forEach((t, i) => {
    if (t.fecha !== diaActual) {
      diaActual = t.fecha;
      html += `<h3 class="day-title">${escapeHTML(etiquetaDia(t.fecha, data.hoy))}</h3>`;
    }
    const acciones = t.rutina
      ? `<button type="button" class="btn-cta solid" data-accion="descargar" data-i="${i}">Descargar PDF</button>
         <button type="button" class="btn-cta" data-accion="subir" data-i="${i}">Actualizar rutina</button>`
      : `<span class="badge-pending">Sin PDF cargado</span>
         <button type="button" class="btn-cta" data-accion="subir" data-i="${i}">Cargar rutina</button>`;
    html += `
      <article class="alumno-row${t.rutina ? "" : " pending"}">
        <div class="alumno-main">
          <div class="avatar">${escapeHTML(iniciales(t.usuario_nombre))}</div>
          <div class="info">
            <b>${escapeHTML(t.usuario_nombre)}</b>
            <span>${escapeHTML(t.grupo_muscular || "Grupo a definir")}</span>
          </div>
        </div>
        <div class="alumno-time">${escapeHTML(t.rango_horario)} hs</div>
        <div class="alumno-actions">${acciones}</div>
      </article>`;
  });
  lista.innerHTML = html;

  lista.querySelectorAll("button[data-accion]").forEach((btn) => {
    const t = turnos[Number(btn.dataset.i)];
    btn.addEventListener("click", async () => {
      if (btn.dataset.accion === "subir") {
        alumnoParaSubir = t.usuario_id;
        fileInput.click();
        return;
      }
      btn.disabled = true;
      try {
        await descargarArchivo(t.rutina.id, t.rutina.nombre);
      } catch (e) {
        mostrarAviso(e.message);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

async function cargar() {
  try {
    pintar(await apiFetch("/profesores/" + sesion.id + "/agenda?dias=7"));
  } catch (e) {
    document.getElementById("alumnosList").innerHTML = "";
    mostrarAviso("No pudimos cargar tu agenda: " + e.message);
  }
}

if (sesion) cargar();
