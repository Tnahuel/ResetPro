// Helpers compartidos para hablar con la API de ResetPro.
// En Vercel (y en local con "uvicorn backend.main:app") el front y la API comparten
// dominio, asi que la base es siempre "/api".

const API_BASE_URL = "/api";

function guardarSesion({ access_token, rol, nombre, id }) {
  localStorage.setItem("resetpro_token", access_token);
  localStorage.setItem("resetpro_rol", rol);
  localStorage.setItem("resetpro_nombre", nombre);
  localStorage.setItem("resetpro_id", id);
}

function obtenerSesion() {
  const token = localStorage.getItem("resetpro_token");
  if (!token) return null;
  return {
    token,
    rol: localStorage.getItem("resetpro_rol"),
    nombre: localStorage.getItem("resetpro_nombre"),
    id: parseInt(localStorage.getItem("resetpro_id"), 10),
  };
}

function cerrarSesion() {
  ["token", "rol", "nombre", "id"].forEach((k) => localStorage.removeItem("resetpro_" + k));
}

// Prefijo para llegar a la raiz del sitio desde las paginas dentro de subcarpetas.
function prefijoRaiz() {
  return /\/(usuario|profesor|admin)\//.test(location.pathname) ? "../" : "";
}

function loginPara(rol) {
  return prefijoRaiz() + (rol === "usuario" ? "login-usuario.html" : "login-profesor.html");
}

// Redirige al login si no hay sesion o si el rol no es el esperado en esta pagina.
function exigirSesion(rolEsperado) {
  const sesion = obtenerSesion();
  if (!sesion || sesion.rol !== rolEsperado) {
    window.location.href = loginPara(rolEsperado);
    return null;
  }
  return sesion;
}

function mensajeError(detail, status) {
  if (Array.isArray(detail)) {
    return detail.map((d) => (d.loc ? d.loc.slice(1).join(".") + ": " : "") + d.msg).join(" | ");
  }
  return detail || "Error " + status;
}

async function apiRequest(path, options = {}) {
  const sesion = obtenerSesion();
  const headers = { ...(options.headers || {}) };
  const esFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (!esFormData && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  if (sesion) headers["Authorization"] = "Bearer " + sesion.token;

  let res;
  try {
    res = await fetch(API_BASE_URL + path, { ...options, headers });
  } catch (e) {
    throw new Error("No se pudo conectar con el servidor.");
  }

  if (!res.ok) {
    // Sesion vencida: volver al login (salvo en el propio login, donde 401 = clave incorrecta).
    if (res.status === 401 && sesion && !path.startsWith("/auth/login")) {
      const rol = sesion.rol;
      cerrarSesion();
      window.location.href = loginPara(rol);
    }
    const error = await res.json().catch(() => ({}));
    throw new Error(mensajeError(error.detail, res.status));
  }
  return res;
}

async function apiFetch(path, options = {}) {
  const res = await apiRequest(path, options);
  return res.status === 204 ? null : res.json();
}

// Descarga un archivo protegido (el header Authorization no viaja en un <a href>).
async function descargarArchivo(id, nombre) {
  const res = await apiRequest("/archivos/" + id);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre || "documento.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function subirArchivo(usuarioId, tipo, file) {
  const fd = new FormData();
  fd.append("usuario_id", usuarioId);
  fd.append("tipo", tipo);
  fd.append("archivo", file);
  return apiFetch("/archivos", { method: "POST", body: fd });
}

function iniciales(nombre) {
  return (nombre || "?").split(" ").filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
}

function escapeHTML(s) {
  return String(s ?? "").replace(/[&<>"\x27]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "\x27": "&#39;" }[c]));
}
