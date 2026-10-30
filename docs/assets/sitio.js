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
    return 'dark'; // como k0lmena.com: oscuro salvo que la persona elija el claro
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

    // -------------------------------------------------------------- buscador (Ctrl K o /)
    iniciarBuscador();

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

  // ---------------------------------------------------------------- buscador
  // Índice armado al vuelo con el texto de cada sección (títulos, párrafos, listas, tablas y código);
  // sin dependencias. Ignora mayúsculas y acentos ("configuracion" encuentra "Configuración").
  const TEXTOS = {
    es: { ph: 'Buscar en la documentación…', vacio: 'Sin resultados para', ayuda: 'Escribí al menos 2 letras.',
      pie: ['↑↓ para moverte', 'Enter para ir', 'Esc para cerrar'] },
    en: { ph: 'Search the documentation…', vacio: 'No results for', ayuda: 'Type at least 2 letters.',
      pie: ['↑↓ to move', 'Enter to go', 'Esc to close'] },
  };
  const normalizar = (t) => (t || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const escapar = (t) => t.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  function iniciarBuscador() {
    const boton = document.getElementById('abrir-busqueda');
    if (!boton) return;
    const idioma = (document.documentElement.lang || 'es').slice(0, 2) === 'en' ? 'en' : 'es';
    const T = TEXTOS[idioma];
    const panel = document.createElement('div');
    panel.className = 'busqueda';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.innerHTML = `<div class="caja"><label class="campo"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
      <input type="search" autocomplete="off" spellcheck="false" placeholder="${T.ph}" aria-label="${T.ph}"><kbd>Esc</kbd></label>
      <ul class="resultados" role="listbox"></ul><div class="pie-b">${T.pie.map((x) => `<span>${x}</span>`).join('')}</div></div>`;
    document.body.appendChild(panel);
    const campo = panel.querySelector('input');
    const lista = panel.querySelector('.resultados');
    let indice = null;
    let actuales = [];
    let sel = 0;

    function armarIndice() {
      const items = [];
      document.querySelectorAll('.seccion[id]').forEach((sec) => {
        const titulo = (sec.querySelector('h2')?.textContent || '').trim();
        if (!titulo) return;
        items.push({ sec, titulo, el: sec.querySelector('h2'), texto: titulo, peso: 3 });
        sec.querySelectorAll('h3, h4, p, li, td, .pedido, pre, figcaption').forEach((el) => {
          if (el.closest('td') && el.tagName !== 'TD') return;
          const texto = el.textContent.replace(/\s+/g, ' ').trim();
          if (texto.length < 3) return;
          items.push({ sec, titulo, el, texto, peso: /^H[34]$/.test(el.tagName) ? 2 : 1 });
        });
      });
      items.forEach((it) => { it.norm = normalizar(it.texto); it.normTitulo = normalizar(it.titulo); });
      return items;
    }

    function fragmento(texto, terminos) {
      const norm = normalizar(texto);
      const pos = Math.max(0, norm.indexOf(terminos[0]));
      const ini = Math.max(0, pos - 60);
      let trozo = (ini > 0 ? '…' : '') + texto.slice(ini, ini + 180) + (texto.length > ini + 180 ? '…' : '');
      let html = escapar(trozo);
      terminos.forEach((t) => {
        if (!t) return;
        // resaltado ignorando acentos: se busca en la versión normalizada y se marca en el original
        const n = normalizar(html);
        let salida = '';
        let i = 0;
        let j;
        while ((j = n.indexOf(t, i)) >= 0) {
          salida += html.slice(i, j) + '<mark>' + html.slice(j, j + t.length) + '</mark>';
          i = j + t.length;
        }
        html = salida + html.slice(i);
      });
      return html;
    }

    function buscar(q) {
      indice = indice || armarIndice();
      const terminos = normalizar(q).split(/\s+/).filter((t) => t.length > 0);
      if (normalizar(q).replace(/\s/g, '').length < 2) {
        actuales = [];
        lista.innerHTML = `<li class="vacio">${T.ayuda}</li>`;
        return;
      }
      const vistos = new Set();
      actuales = indice
        .filter((it) => terminos.every((t) => it.norm.includes(t) || it.normTitulo.includes(t)) && terminos.some((t) => it.norm.includes(t)))
        .map((it) => ({ it, puntaje: it.peso * 10 + (it.normTitulo.includes(terminos[0]) ? 5 : 0) - Math.min(it.texto.length / 400, 3) }))
        .sort((a, b) => b.puntaje - a.puntaje)
        .filter(({ it }) => {
          const clave = it.sec.id + '|' + it.texto.slice(0, 80);
          if (vistos.has(clave)) return false;
          vistos.add(clave);
          return true;
        })
        .slice(0, 30)
        .map((x) => x.it);
      sel = 0;
      if (!actuales.length) {
        lista.innerHTML = `<li class="vacio">${T.vacio} “${escapar(q)}”.</li>`;
        return;
      }
      lista.innerHTML = actuales.map((it, i) => `<li><a href="#${it.sec.id}" data-i="${i}" role="option"${i === 0 ? ' class="sel" aria-selected="true"' : ''}>
        <span class="sec">${escapar(it.titulo)}</span><span class="frag">${fragmento(it.texto, terminos)}</span></a></li>`).join('');
    }

    function marcar(i) {
      const enlaces = lista.querySelectorAll('a');
      if (!enlaces.length) return;
      sel = (i + enlaces.length) % enlaces.length;
      enlaces.forEach((a, k) => { a.classList.toggle('sel', k === sel); a.setAttribute('aria-selected', k === sel ? 'true' : 'false'); });
      enlaces[sel].scrollIntoView({ block: 'nearest' });
    }

    function ir(i) {
      const it = actuales[i];
      if (!it) return;
      cerrar();
      it.el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      history.replaceState(null, '', '#' + it.sec.id);
      it.el.classList.add('resaltado-busqueda');
      setTimeout(() => it.el.classList.remove('resaltado-busqueda'), 2200);
    }

    function abrir() {
      panel.classList.add('abierta');
      campo.value = '';
      buscar('');
      setTimeout(() => campo.focus(), 0);
    }
    function cerrar() { panel.classList.remove('abierta'); }

    boton.addEventListener('click', abrir);
    campo.addEventListener('input', () => buscar(campo.value));
    campo.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); marcar(sel + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); marcar(sel - 1); }
      else if (e.key === 'Enter') { e.preventDefault(); ir(sel); }
      else if (e.key === 'Escape') cerrar();
    });
    lista.addEventListener('click', (e) => {
      const a = e.target.closest('a[data-i]');
      if (!a) return;
      e.preventDefault();
      ir(parseInt(a.dataset.i, 10));
    });
    panel.addEventListener('click', (e) => { if (e.target === panel) cerrar(); });
    document.addEventListener('keydown', (e) => {
      const escribiendo = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || '');
      if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !escribiendo)) { e.preventDefault(); abrir(); }
      else if (e.key === 'Escape' && panel.classList.contains('abierta')) cerrar();
    });
  }
})();
