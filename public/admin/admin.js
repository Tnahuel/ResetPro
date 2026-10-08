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
const estadoTexto = { confirmado: "Activo", completado: "Activo", pendiente: "Pendiente", cancelado: "Cancelado", sin_turnos: "Sin turnos" };

function fechaCorta(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-AR", { day: "2-digit", month: "short" }) + " " +
    d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
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

async function cargarEstudiantes() {
  const tbody = document.getElementById("tbodyEstudiantes");
  try {
    const lista = await apiFetch("/admin/estudiantes-detalle");
    tbody.innerHTML = lista.length ? "" : `<tr><td colspan="6">Todavía no hay alumnos registrados.</td></tr>`;
    lista.forEach((e) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="who-cell"><span class="avatar">${escapeHTML(iniciales(e.nombre))}</span>${escapeHTML(e.nombre)}</td>
        <td>${escapeHTML(e.grupo_muscular || "—")}</td>
        <td>${escapeHTML(e.profesor || "—")}</td>
        <td>${escapeHTML(e.ultimo_turno || "—")}</td>
        <td>${e.activo_semana ? "● " : ""}${escapeHTML(fechaCorta(e.ultimo_acceso))}</td>
        <td><span class="status ${estadoClase[e.estado] || "paused"}">${escapeHTML(estadoTexto[e.estado] || e.estado)}</span></td>`;
      tbody.appendChild(tr);
    });
    const opciones = lista.map((e) => ({ id: e.id, nombre: e.nombre }));
    llenarSelect(document.getElementById("turnoAlumno"), opciones, "No hay alumnos");
    llenarSelect(document.getElementById("macroAlumno"), opciones, "No hay alumnos");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6">No se pudo cargar la lista: ${escapeHTML(e.message)}</td></tr>`;
  }
}

async function cargarProfesores() {
  try {
    const profes = await apiFetch("/profesores");
    llenarSelect(document.getElementById("turnoProfesor"), profes, "No hay profesores");
  } catch (e) {
    agregarLog("No se pudieron cargar los profesores: " + escapeHTML(e.message), true);
  }
}

function refrescarTodo() {
  return Promise.all([cargarStats(), cargarEstudiantes(), cargarProfesores()]);
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
    await apiFetch("/turnos", {
      method: "POST",
      body: JSON.stringify({ usuario_id, profesor_id, fecha, rango_horario: hora, grupo_muscular: grupo || null }),
    });
    const item = document.createElement("div");
    item.className = "mini-item";
    item.innerHTML = `<span>${escapeHTML(alumno)} con ${escapeHTML(profe)}</span><span class="role-badge">${escapeHTML(fecha)} · ${escapeHTML(hora)}</span>`;
    turnosRecientes.appendChild(item);
    agregarLog(`Turno asignado: <b>${escapeHTML(alumno)}</b> con <b>${escapeHTML(profe)}</b>, ${escapeHTML(hora)} hs`);
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
      const limpio = JSON.parse(JSON.stringify(datos));
      await apiFetch("/dietas/usuario/" + usuario_id, { method: "POST", body: JSON.stringify(limpio) });
      hecho.push("macros y micros");
    }
    if (archivo) {
      await subirArchivo(usuario_id, tipo, archivo);
      hecho.push(tipo === "rutina" ? "rutina en PDF" : "dieta en PDF");
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
