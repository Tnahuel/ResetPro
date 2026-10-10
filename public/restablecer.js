const token = new URLSearchParams(location.search).get("token") || "";
// El token no tiene por que quedar a la vista ni en el historial.
history.replaceState(null, "", location.pathname);

const cargando = document.getElementById("cargando");
const form = document.getElementById("resForm");
const invalido = document.getElementById("invalido");
const listo = document.getElementById("listo");
const errorEl = document.getElementById("resError");

function mostrarInvalido() {
  cargando.hidden = true;
  form.hidden = true;
  invalido.hidden = false;
}

async function iniciar() {
  if (!token) return mostrarInvalido();
  try {
    const r = await apiFetch("/auth/validar-recuperacion", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
    if (!r.valido) return mostrarInvalido();
    cargando.hidden = true;
    form.hidden = false;
  } catch (e) {
    mostrarInvalido();
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.classList.remove("show");
  const p1 = document.getElementById("pass1").value;
  const p2 = document.getElementById("pass2").value;

  if (p1.length < 6) {
    errorEl.textContent = "La contraseña debe tener al menos 6 caracteres.";
    errorEl.classList.add("show");
    return;
  }
  if (p1 !== p2) {
    errorEl.textContent = "Las contraseñas no coinciden.";
    errorEl.classList.add("show");
    return;
  }

  const btn = form.querySelector(".btn-primary");
  btn.disabled = true;
  try {
    const r = await apiFetch("/auth/restablecer-password", {
      method: "POST",
      body: JSON.stringify({ token, password_nueva: p1 }),
    });
    form.hidden = true;
    document.getElementById("irLogin").href = loginPara(r.rol === "usuario" ? "usuario" : "profesor");
    listo.hidden = false;
  } catch (err) {
    errorEl.textContent = err.message || "No se pudo guardar la contraseña.";
    errorEl.classList.add("show");
    btn.disabled = false;
  }
});

iniciar();
