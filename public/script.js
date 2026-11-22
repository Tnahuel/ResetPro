const header = document.querySelector('header');
const menuBtn = document.getElementById('menuBtn');
const navMenu = document.getElementById('navMenu');
const nombre = document.getElementById("nombre").value;
const mensaje = `Hola mi nombre es ${nombre}, me gustaría sumarme a Reset Pro`;

function setMenu(open){
  navMenu.classList.toggle('open', open);
  header.classList.toggle('menu-open', open);
  menuBtn.setAttribute('aria-expanded', String(open));
  menuBtn.setAttribute('aria-label', open ? 'Cerrar menú' : 'Abrir menú');
  menuBtn.textContent = open ? '✕' : '☰';
}

menuBtn.addEventListener('click', () => setMenu(!navMenu.classList.contains('open')));

// Cerrar al tocar cualquier link o botón del menú
navMenu.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setMenu(false)));

// Cerrar al tocar fuera del menú o con Escape
document.addEventListener('click', e => {
  if (navMenu.classList.contains('open') && !navMenu.contains(e.target) && !menuBtn.contains(e.target)) setMenu(false);
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') setMenu(false); });

// Si se agranda la pantalla, resetear el estado
window.addEventListener('resize', () => { if (window.innerWidth > 860) setMenu(false); });

//Mensaje de usuario 
const whatsappUrl = `https://wa.me/5493517668913?text=${encodeURIComponent(mensaje)}`;