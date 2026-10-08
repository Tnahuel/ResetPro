

const menuBtn = document.getElementById('menuBtn');
  const navLinks = document.getElementById('navLinks');
  const navAuth = document.getElementById('navAuth');
  const navCta = document.getElementById('navCta');
  menuBtn.addEventListener('click', () => {
    navLinks.classList.toggle('open');
    navAuth.classList.toggle('open');
    navCta.classList.toggle('open');
  });
  navLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
    navLinks.classList.remove('open');
    navAuth.classList.remove('open');
    navCta.classList.remove('open');
  }));
