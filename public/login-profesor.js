const roleButtons = document.querySelectorAll(".role-btn");
const loginTag = document.getElementById("loginTag");
const loginSub = document.getElementById("loginSub");
const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const submitBtn = loginForm ? loginForm.querySelector(".btn-primary") : null;

let selectedRole = "profesor";

const roleCopy = {
  profesor: {
    tag: "PROFESOR",
    sub: "Gestioná tus alumnos, horarios y rutinas.",
    redirect: "profesor/Profesor.html",
  },
  admin: {
    tag: "ADMINISTRADOR",
    sub: "Gestioná usuarios, profesores, turnos y planes nutricionales.",
    redirect: "admin/Admin.html",
  },
};

roleButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    roleButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    selectedRole = btn.dataset.role;

    const copy = roleCopy[selectedRole];
    loginTag.textContent = copy.tag;
    loginSub.textContent = copy.sub;
  });
});

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

    // El rol esperado por el backend es "admin", igual que el value del botón.
    const rolEsperado = selectedRole === "admin" ? "admin" : "profesor";

    try {
      const data = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, rol_esperado: rolEsperado }),
      });

      guardarSesion(data);
      window.location.href = roleCopy[selectedRole].redirect;
    } catch (err) {
      loginError.textContent = err.message || "No pudimos iniciar sesión.";
      loginError.classList.add("show");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Ingresar";
    }
  });
}
