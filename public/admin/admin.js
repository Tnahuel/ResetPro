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

// ---------- Helpers ----------
const logList = document.getElementById("logList");

function horaActual() {
  const d = new Date();
  return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
}

function agregarLog(html, esError = false) {
  const vacio = logList.querySelector(".log-empty");
  if (vacio) vacio.remove();
  const li = document.createElement("li");
  if (esError) li.className = "err";
  li.innerHTML = `<span class="log-time">${horaActual()}</span> ${html}`;
  logList.prepend(li);
}

const estadoClase = { confirmado: "active", completado: "active", pendiente: "pending", cancelado: "paused", sin_turnos: "paused" };
const estadoTexto = { confirmado: "Confirmado", completado: "Completado", pendiente: "Pendiente", cancelado: "Cancelado", sin_turnos: "Sin turnos" };
const tipoTurnoTexto = { proximo: "Próximo", ultimo: "Último", cancelado: "Cancelado" };
const rolTexto = { usuario: "Alumno", profesor: "Profesor", admin: "Administrador" };

function fechaCorta(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-AR", { day: "2-digit", month: "short" }) + " " +
    d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
}

function fechaTurno(iso, hora) {
  const [y, m, d] = iso.split("-").map(Number);
  const f = new Date(y, m - 1, d);
  return f.toLocaleDateString("es-AR", { day: "2-digit", month: "short" }) + " " + hora;
}

function haceCuanto(iso) {
  const min = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (min < 1) return "recién";
  if (min < 60) return "hace " + min + " min";
  if (min < 1440) return "hace " + Math.round(min / 60) + " h";
  return "hace " + Math.round(min / 1440) + " días";
}

function celdaArchivo(a) {
  if (!a) return "—";
  return `<button type="button" class="file-link" data-archivo="${a.id}" data-nombre="${escapeHTML(a.nombre)}">${escapeHTML(a.nombre)}</button>` +
         `<span class="cell-sub">Subido ${escapeHTML(fechaCorta(a.creado_en))}</span>`;
}

function celdaDieta(e) {
  const m = e.macros;
  const macros = m ? `P ${Math.round(m.proteina)} · C ${Math.round(m.carbohidratos)} · G ${Math.round(m.grasas)} g` : "";
  const pdf = e.dieta_pdf ? celdaArchivo(e.dieta_pdf) : "";
  if (!macros && !pdf) return "—";
  return (macros ? `<span>${escapeHTML(macros)}</span>` : "") + (pdf ? `<span class="cell-sub">${pdf}</span>` : "");
}

function llenarSelect(select, items, vacioTexto) {
  select.innerHTML = "";
  if (!items.length) {
    select.innerHTML = `<option value="">${vacioTexto}</option>`;
    return;
  }
  items.forEach((it) => {
    const opt = document.createElement("option");
    opt.value = it.id;
    opt.textContent = it.nombre;
    select.appendChild(opt);
  });
}

function botonesAccion(rol, id, nombre, aviso) {
  return `<div class="acciones">
    <button type="button" class="act-btn" data-accion="enlace" data-rol="${rol}" data-id="${id}" data-nombre="${escapeHTML(nombre)}">Enlace de clave</button>
    <button type="button" class="act-btn danger" data-accion="eliminar" data-rol="${rol}" data-id="${id}" data-nombre="${escapeHTML(nombre)}" data-aviso="${escapeHTML(aviso || "")}">Eliminar</button>
  </div>`;
}

// ---------- Recuperacion de contrasenas ----------
function mostrarEnlace(titulo, token) {
  const url = location.origin + "/restablecer.html?token=" + encodeURIComponent(token);
  document.getElementById("enlaceTitulo").textContent = titulo;
  document.getElementById("enlaceInput").value = url;
  const box = document.getElementById("enlaceBox");
  box.hidden = false;
  box.scrollIntoView({ behavior: "smooth", block: "center" });
}

document.getElementById("btnCopiar").addEventListener("click", async () => {
  const input = document.getElementById("enlaceInput");
  const btn = document.getElementById("btnCopiar");
  try {
    await navigator.clipboard.writeText(input.value);
  } catch (e) {
    input.select();
    document.execCommand("copy");
  }
  btn.textContent = "¡Copiado!";
  setTimeout(() => (btn.textContent = "Copiar enlace"), 1800);
});

async function generarEnlace(rol, id, nombre, boton) {
  if (boton) boton.disabled = true;
  try {
    const r = await apiFetch("/admin/enlace-recuperacion", { method: "POST", body: JSON.stringify({ rol, id: Number(id) }) });
    mostrarEnlace(`Enlace para ${r.nombre} (${r.email}) · válido 24 horas`, r.token);
    agregarLog(`Enlace de recuperación generado para <b>${escapeHTML(r.nombre)}</b>`);
    await cargarSolicitudes();
  } catch (err) {
    agregarLog("No se pudo generar el enlace: " + escapeHTML(err.message), true);
  } finally {
    if (boton) boton.disabled = false;
  }
}

async function cargarSolicitudes() {
  const cont = document.getElementById("listaSolicitudes");
  try {
    const lista = await apiFetch("/admin/recuperaciones");
    if (!lista.length) {
      cont.innerHTML = `<p class="hint">No hay solicitudes pendientes.</p>`;
      return;
    }
    cont.innerHTML = lista.map((s, i) => `
      <div class="solicitud">
        <span><b>${escapeHTML(s.nombre)}</b> · ${escapeHTML(s.email)}
          <span class="cell-sub">${escapeHTML(rolTexto[s.rol] || s.rol)} · ${escapeHTML(haceCuanto(s.creado_en))}</span></span>
        <button type="button" class="act-btn" data-sol="${i}">Generar enlace</button>
      </div>`).join("");
    cont.querySelectorAll("button[data-sol]").forEach((b) => {
      const s = lista[Number(b.dataset.sol)];
      b.addEventListener("click", () => generarEnlace(s.rol, s.perfil_id, s.nombre, b));
    });
  } catch (e) {
    cont.innerHTML = `<p class="hint">No se pudieron cargar las solicitudes: ${escapeHTML(e.message)}</p>`;
  }
}

// ---------- Eliminar ----------
async function eliminar(rol, id, nombre, aviso, boton) {
  const tipo = rol === "usuario" ? "al alumno" : "al profesor";
  const detalle = rol === "usuario"
    ? "Se borrarán también su cuenta, turnos, plan nutricional y PDFs."
    : "Se borrarán también su cuenta y los turnos que tenía asignados." + (aviso ? "\n" + aviso : "");
  if (!confirm(`¿Eliminar ${tipo} ${nombre}?\n\n${detalle}\n\nEsta acción no se puede deshacer.`)) return;

  boton.disabled = true;
  try {
    const ruta = rol === "usuario" ? "/admin/usuarios/" : "/admin/profesores/";
    const r = await apiFetch(ruta + id, { method: "DELETE" });
    const t = r.eliminados && r.eliminados.turnos ? ` (y ${r.eliminados.turnos} turno${r.eliminados.turnos > 1 ? "s" : ""})` : "";
    agregarLog(`Se eliminó ${rol === "usuario" ? "al alumno" : "al profesor"} <b>${escapeHTML(r.nombre)}</b>${t}`);
    await refrescarTodo();
  } catch (err) {
    agregarLog("No se pudo eliminar: " + escapeHTML(err.message), true);
    boton.disabled = false;
  }
}

// Un solo manejador para los botones de ambas tablas
document.addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-accion]");
  if (!btn) return;
  const { accion, rol, id, nombre, aviso } = btn.dataset;
  if (accion === "enlace") generarEnlace(rol, id, nombre, btn);
  if (accion === "eliminar") eliminar(rol, id, nombre, aviso, btn);
});

document.addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-archivo]");
  if (!b) return;
  descargarArchivo(b.dataset.archivo, b.dataset.nombre)
    .catch((err) => agregarLog("No se pudo descargar: " + escapeHTML(err.message), true));
});

// ---------- Carga de datos ----------
async function cargarStats() {
  try {
    const s = await apiFetch("/admin/stats");
    document.getElementById("statUsuarios").textContent = s.usuarios;
    document.getElementById("statActivos").textContent = s.activos_semana;
    document.getElementById("statProfesores").textContent = s.profesores;
    document.getElementById("statTurnos").textContent = s.turnos_hoy;
    document.getElementById("statPendientes").textContent = s.rutinas_pendientes;
  } catch (e) {
    agregarLog("No se pudieron cargar las estadísticas: " + escapeHTML(e.message), true);
  }
}

let estudiantesCache = [];

function actualizarHintArchivos() {
  const hint = document.getElementById("archivosActuales");
  const id = parseInt(document.getElementById("macroAlumno").value, 10);
  const e = estudiantesCache.find((x) => x.id === id);
  if (!e) { hint.textContent = ""; return; }
  hint.textContent =
    "Rutina actual: " + (e.rutina ? e.rutina.nombre : "ninguna") +
    " · Dieta actual: " + (e.dieta_pdf ? e.dieta_pdf.nombre : "ninguna");
}

async function cargarEstudiantes() {
  const tbody = document.getElementById("tbodyEstudiantes");
  try {
    const lista = await apiFetch("/admin/estudiantes-detalle");
    estudiantesCache = lista;
    tbody.innerHTML = lista.length ? "" : `<tr><td colspan="9">Todavía no hay alumnos registrados.</td></tr>`;
    lista.forEach((e) => {
      const t = e.turno;
      const turnoHTML = t
        ? `${escapeHTML(fechaTurno(t.fecha, t.hora))}<span class="cell-sub">${escapeHTML(tipoTurnoTexto[t.tipo] || "")}</span>`
        : "—";
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="who-cell"><span class="avatar">${escapeHTML(iniciales(e.nombre))}</span>
          <span>${escapeHTML(e.nombre)}<span class="cell-sub">${escapeHTML(e.email || "")}</span></span></td>
        <td>${escapeHTML(e.grupo_muscular || "—")}</td>
        <td>${escapeHTML((t && t.profesor) || "—")}</td>
        <td>${turnoHTML}</td>
        <td>${celdaArchivo(e.rutina)}</td>
        <td>${celdaDieta(e)}</td>
        <td>${e.activo_semana ? "● " : ""}${escapeHTML(fechaCorta(e.ultimo_acceso))}</td>
        <td><span class="status ${estadoClase[e.estado] || "paused"}">${escapeHTML(estadoTexto[e.estado] || e.estado)}</span></td>
        <td>${botonesAccion("usuario", e.id, e.nombre)}</td>`;
      tbody.appendChild(tr);
    });

    const opciones = lista.map((e) => ({ id: e.id, nombre: e.nombre }));
    const selTurno = document.getElementById("turnoAlumno");
    const selMacro = document.getElementById("macroAlumno");
    const prevTurno = selTurno.value, prevMacro = selMacro.value;
    llenarSelect(selTurno, opciones, "No hay alumnos");
    llenarSelect(selMacro, opciones, "No hay alumnos");
    if (prevTurno && opciones.some((o) => String(o.id) === prevTurno)) selTurno.value = prevTurno;
    if (prevMacro && opciones.some((o) => String(o.id) === prevMacro)) selMacro.value = prevMacro;
    actualizarHintArchivos();
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="9">No se pudo cargar la lista: ${escapeHTML(e.message)}</td></tr>`;
  }
}

async function cargarProfesores() {
  const tbody = document.getElementById("tbodyProfesores");
  try {
    const profes = await apiFetch("/admin/profesores-detalle");
    tbody.innerHTML = profes.length ? "" : `<tr><td colspan="5">Todavía no hay profesores registrados.</td></tr>`;
    profes.forEach((p) => {
      const aviso = p.turnos_total
        ? `Tiene ${p.turnos_total} turno${p.turnos_total > 1 ? "s" : ""} en total (${p.turnos_proximos} próximo${p.turnos_proximos === 1 ? "" : "s"}) que se van a borrar.`
        : "";
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="who-cell"><span class="avatar">${escapeHTML(iniciales(p.nombre))}</span>
          <span>${escapeHTML(p.nombre)}<span class="cell-sub">${escapeHTML(p.email || "")}</span></span></td>
        <td>${escapeHTML(p.especialidad || "—")}</td>
        <td>${p.turnos_proximos}<span class="cell-sub">${p.alumnos_proximos} alumno${p.alumnos_proximos === 1 ? "" : "s"}</span></td>
        <td>${p.activo_semana ? "● " : ""}${escapeHTML(fechaCorta(p.ultimo_acceso))}</td>
        <td>${botonesAccion("profesor", p.id, p.nombre, aviso)}</td>`;
      tbody.appendChild(tr);
    });
    const selProfe = document.getElementById("turnoProfesor");
    const prev = selProfe.value;
    llenarSelect(selProfe, profes.map((p) => ({ id: p.id, nombre: p.nombre })), "No hay profesores");
    if (prev && profes.some((p) => String(p.id) === prev)) selProfe.value = prev;
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5">No se pudo cargar la lista: ${escapeHTML(e.message)}</td></tr>`;
  }
}

function refrescarTodo() {
  return Promise.all([cargarStats(), cargarEstudiantes(), cargarProfesores(), cargarSolicitudes()]);
}

if (sesion) refrescarTodo();

// ---------- Alta de cuentas ----------
const formAlta = document.getElementById("formAlta");
const altaRol = document.getElementById("altaRol");
const altaDetalleLabel = document.getElementById("altaDetalleLabel");
const altaDetalle = document.getElementById("altaDetalle");
const altaRecientes = document.getElementById("altaRecientes");

const rolLabels = {
  usuario: { label: "Grupo muscular inicial", placeholder: "Ej: Espalda", tag: "Usuario" },
  profesor: { label: "Especialidad", placeholder: "Ej: Hipertrofia, rehabilitación", tag: "Profesor" },
  admin: { label: "Permisos adicionales", placeholder: "Ej: Backups, reportes", tag: "Administrador" },
};

altaRol.addEventListener("change", () => {
  const cfg = rolLabels[altaRol.value];
  altaDetalleLabel.textContent = cfg.label;
  altaDetalle.placeholder = cfg.placeholder;
});

formAlta.addEventListener("submit", async (e) => {
  e.preventDefault();
  const nombre = document.getElementById("altaNombre").value.trim();
  const email = document.getElementById("altaEmail").value.trim();
  const password = document.getElementById("altaPass").value;
  const rol = altaRol.value;
  const detalle = altaDetalle.value.trim();

  if (!nombre || !email || password.length < 6) {
    agregarLog("Completá nombre, email y una contraseña de al menos 6 caracteres.", true);
    return;
  }

  const btn = formAlta.querySelector(".btn-primary");
  btn.disabled = true;
  try {
    await apiFetch("/admin/cuentas", {
      method: "POST",
      body: JSON.stringify({ nombre, email, password, rol, detalle: detalle || null }),
    });
    const cfg = rolLabels[rol];
    const item = document.createElement("div");
    item.className = "mini-item";
    item.innerHTML = `<span>${escapeHTML(nombre)} — ${escapeHTML(email)}</span><span class="role-badge">${cfg.tag}</span>`;
    altaRecientes.appendChild(item);
    agregarLog(`Se creó la cuenta de <b>${escapeHTML(nombre)}</b> (${cfg.tag})`);
    formAlta.reset();
    altaDetalleLabel.textContent = rolLabels.usuario.label;
    await refrescarTodo();
  } catch (err) {
    agregarLog("Error al crear la cuenta: " + escapeHTML(err.message), true);
  } finally {
    btn.disabled = false;
  }
});

// ---------- Asignar turno ----------
const formTurno = document.getElementById("formTurno");
const turnosRecientes = document.getElementById("turnosRecientes");

formTurno.addEventListener("submit", async (e) => {
  e.preventDefault();
  const selAlumno = document.getElementById("turnoAlumno");
  const selProfe = document.getElementById("turnoProfesor");
  const usuario_id = parseInt(selAlumno.value, 10);
  const profesor_id = parseInt(selProfe.value, 10);
  const fecha = document.getElementById("turnoFecha").value;
  const hora = document.getElementById("turnoHora").value;
  const grupo = document.getElementById("turnoGrupo").value;

  if (!usuario_id || !profesor_id || !fecha || !hora) {
    agregarLog("Completá alumno, profesor, fecha y horario para asignar el turno.", true);
    return;
  }

  const alumno = selAlumno.selectedOptions[0].textContent;
  const profe = selProfe.selectedOptions[0].textContent;
  const btn = formTurno.querySelector(".btn-primary");
  btn.disabled = true;
  try {
    const reemplazar = document.getElementById("turnoReemplazar").checked;
    const resp = await apiFetch("/turnos", {
      method: "POST",
      body: JSON.stringify({ usuario_id, profesor_id, fecha, rango_horario: hora, grupo_muscular: grupo || null, reemplazar }),
    });
    const item = document.createElement("div");
    item.className = "mini-item";
    item.innerHTML = `<span>${escapeHTML(alumno)} con ${escapeHTML(profe)}</span><span class="role-badge">${escapeHTML(fecha)} · ${escapeHTML(hora)}</span>`;
    turnosRecientes.appendChild(item);
    agregarLog(`Turno asignado: <b>${escapeHTML(alumno)}</b> con <b>${escapeHTML(profe)}</b>, ${escapeHTML(hora)} hs` +
      (resp.reemplazados ? ` (reemplazó ${resp.reemplazados} turno${resp.reemplazados > 1 ? "s" : ""} próximo${resp.reemplazados > 1 ? "s" : ""})` : ""));
    formTurno.reset();
    await Promise.all([cargarStats(), cargarEstudiantes(), cargarProfesores()]);
  } catch (err) {
    agregarLog("Error al asignar el turno: " + escapeHTML(err.message), true);
  } finally {
    btn.disabled = false;
  }
});

// ---------- Macros, micros y PDF ----------
const formMacros = document.getElementById("formMacros");
const macroPdf = document.getElementById("macroPdf");
const fileLabel = document.getElementById("fileLabel");

macroPdf.addEventListener("change", () => {
  fileLabel.textContent = macroPdf.files.length ? macroPdf.files[0].name : "Elegir archivo PDF";
});

formMacros.addEventListener("submit", async (e) => {
  e.preventDefault();
  const sel = document.getElementById("macroAlumno");
  const usuario_id = parseInt(sel.value, 10);
  if (!usuario_id) {
    agregarLog("Elegí un alumno.", true);
    return;
  }
  const alumno = sel.selectedOptions[0].textContent;

  const num = (id) => {
    const v = document.getElementById(id).value;
    return v === "" ? undefined : parseFloat(v);
  };
  const datos = { proteina: num("macroProt"), carbohidratos: num("macroCarb"), grasas: num("macroGrasa") };
  const micros = document.getElementById("micros").value.trim();
  if (micros) datos.micros = micros;
  const hayMacros = Object.values(datos).some((v) => v !== undefined);
  const archivo = macroPdf.files[0];
  const tipo = document.getElementById("pdfTipo").value;

  if (!hayMacros && !archivo) {
    agregarLog("Ingresá macros/micros o adjuntá un PDF.", true);
    return;
  }
  if (archivo && archivo.size > 4 * 1024 * 1024) {
    agregarLog("El PDF supera los 4 MB.", true);
    return;
  }

  const btn = formMacros.querySelector(".btn-primary");
  btn.disabled = true;
  const hecho = [];
  try {
    if (hayMacros) {
      await apiFetch("/dietas/usuario/" + usuario_id, { method: "POST", body: JSON.stringify(datos) });
      hecho.push("macros y micros");
    }
    if (archivo) {
      const r = await subirArchivo(usuario_id, tipo, archivo);
      hecho.push((tipo === "rutina" ? "rutina en PDF" : "dieta en PDF") +
        (r.reemplazo ? ` (reemplazó a ${escapeHTML(r.reemplazo)})` : ""));
    }
    agregarLog(`Guardado para <b>${escapeHTML(alumno)}</b>: ${hecho.join(" y ")}`);
    formMacros.reset();
    fileLabel.textContent = "Elegir archivo PDF";
    await Promise.all([cargarStats(), cargarEstudiantes()]);
  } catch (err) {
    agregarLog("Error al guardar: " + escapeHTML(err.message), true);
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("macroAlumno").addEventListener("change", actualizarHintArchivos);
