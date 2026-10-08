// k0lmenIA · comportamiento del sitio de documentación (tema, navegación, copiar código).
(function () {
  const raiz = document.documentElement;

  // ---------------------------------------------------------------- tema claro / oscuro
  const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* sin storage */ } };
  const leer = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const temaGuardado = leer('k0lmenia-tema');
  if (temaGuardado === 'light' || temaGuardado === 'dark') raiz.setAttribute('data-theme', temaGuardado);

  function temaActual() {
    const t = raiz.getAttribute('data-theme');
    if (t) return t;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function pintarBoton() {
    const b = document.getElementById('cambiar-tema');
    if (!b) return;
    const oscuro = temaActual() === 'dark';
    b.setAttribute('aria-label', oscuro ? 'Usar tema claro' : 'Usar tema oscuro');
    b.querySelector('.sol').style.display = oscuro ? 'block' : 'none';
    b.querySelector('.luna').style.display = oscuro ? 'none' : 'block';
  }

  document.addEventListener('DOMContentLoaded', () => {
    pintarBoton();
    document.getElementById('cambiar-tema')?.addEventListener('click', () => {
      const nuevo = temaActual() === 'dark' ? 'light' : 'dark';
      raiz.setAttribute('data-theme', nuevo);
      guardar('k0lmenia-tema', nuevo);
      pintarBoton();
    });

    // -------------------------------------------------------------- navegación móvil
    const body = document.body;
    document.getElementById('abrir-nav')?.addEventListener('click', () => body.classList.toggle('nav-abierta'));
    document.querySelectorAll('.lateral a').forEach((a) => a.addEventListener('click', () => body.classList.remove('nav-abierta')));
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') body.classList.remove('nav-abierta'); });
    document.addEventListener('click', (e) => {
      if (body.classList.contains('nav-abierta') && !e.target.closest('.lateral') && !e.target.closest('#abrir-nav')) body.classList.remove('nav-abierta');
    });

    // -------------------------------------------------------------- sección activa en el menú
    const enlaces = new Map();
    document.querySelectorAll('.lateral a[href^="#"]').forEach((a) => enlaces.set(a.getAttribute('href').slice(1), a));
    const observador = new IntersectionObserver((entradas) => {
      entradas.forEach((en) => {
        if (!en.isIntersecting) return;
        enlaces.forEach((a) => a.classList.remove('activo'));
        enlaces.get(en.target.id)?.classList.add('activo');
      });
    }, { rootMargin: '-20% 0px -70% 0px' });
    document.querySelectorAll('.seccion[id]').forEach((s) => observador.observe(s));

    // -------------------------------------------------------------- copiar bloques de código
    document.querySelectorAll('.codigo').forEach((bloque) => {
      const pre = bloque.querySelector('pre');
      if (!pre) return;
      const boton = document.createElement('button');
      boton.className = 'copiar';
      boton.type = 'button';
      boton.textContent = 'Copiar';
      boton.addEventListener('click', async () => {
        const texto = pre.innerText.replace(/\s+#.*$/gm, '').trim(); // sin los comentarios
        try {
          await navigator.clipboard.writeText(texto);
          boton.textContent = 'Copiado';
        } catch (e) {
          boton.textContent = 'No se pudo copiar';
        }
        setTimeout(() => { boton.textContent = 'Copiar'; }, 1600);
      });
      bloque.appendChild(boton);
    });
  });
})();
