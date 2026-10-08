const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const submitBtn = loginForm ? loginForm.querySelector(".btn-primary") : null;

if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();

    if (!email || !password) {
      loginError.textContent = "Completá usuario y contraseña.";
      loginError.classList.add("show");
      return;
    }

    loginError.classList.remove("show");
    submitBtn.disabled = true;
    submitBtn.textContent = "Ingresando...";

    try {
      const data = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, rol_esperado: "usuario" }),
      });

      guardarSesion(data);
      window.location.href = "usuario/Usuario.html";
    } catch (err) {
      loginError.textContent = err.message || "No pudimos iniciar sesión.";
      loginError.classList.add("show");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Ingresar";
    }
  });
}
