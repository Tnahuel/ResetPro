const params = new URLSearchParams(location.search);
const rolLogin = params.get("rol") === "profesor" ? "profesor" : "usuario";
document.getElementById("linkLogin").href = loginPara(rolLogin);

const form = document.getElementById("recForm");
const errorEl = document.getElementById("recError");
const okEl = document.getElementById("recOk");
const infoEl = document.getElementById("recInfo");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("email").value.trim();
  errorEl.classList.remove("show");

  if (!email || !email.includes("@")) {
    errorEl.textContent = "Ingresá un email válido.";
    errorEl.classList.add("show");
    return;
  }

  const btn = form.querySelector(".btn-primary");
  btn.disabled = true;
  btn.textContent = "Enviando...";
  try {
    const r = await apiFetch("/auth/olvide-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
    form.hidden = true;
    if (r.canal === "email") {
      okEl.textContent =
        "Si ese email está registrado, te enviamos un enlace para crear una contraseña nueva. " +
        "Puede tardar unos minutos: revisá también la carpeta de spam. El enlace vence en 60 minutos.";
      okEl.hidden = false;
    } else {
      infoEl.textContent =
        "Registramos tu solicitud. Avisale a tu administrador para que te envíe un enlace de recuperación.";
      infoEl.hidden = false;
    }
  } catch (err) {
    errorEl.textContent = err.message || "No pudimos procesar la solicitud.";
    errorEl.classList.add("show");
    btn.disabled = false;
    btn.textContent = "Enviar enlace";
  }
});
