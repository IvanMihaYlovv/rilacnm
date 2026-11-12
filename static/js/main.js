/* РИЛА-СНМ — interactions.
   Every feature is progressive: the page is fully usable without this file,
   without the CDN libraries, and with prefers-reduced-motion. */
(() => {
  'use strict';

  const root = document.documentElement;
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const animate = !reduceMotion && 'gsap' in window && 'ScrollTrigger' in window;

  if (!animate) root.classList.remove('js-anim');
  else gsap.registerPlugin(ScrollTrigger);

  const header = $('[data-header]');
  const headerOffset = () => -(header ? header.offsetHeight : 0);

  /* ------------------------------------------------------------------
     Smooth scroll (Lenis) — driven by GSAP's ticker so ScrollTrigger
     and Lenis never disagree about the scroll position.
  ------------------------------------------------------------------ */
  let lenis = null;
  if (!reduceMotion && 'Lenis' in window) {
    lenis = new Lenis({ lerp: 0.1, wheelMultiplier: 1, smoothWheel: true });
    if (animate) {
      lenis.on('scroll', ScrollTrigger.update);
      gsap.ticker.add((time) => lenis.raf(time * 1000));
      gsap.ticker.lagSmoothing(0);
    } else {
      const raf = (t) => { lenis.raf(t); requestAnimationFrame(raf); };
      requestAnimationFrame(raf);
    }
  }

  const scrollToEl = (el, onComplete) => {
    if (lenis) {
      lenis.scrollTo(el, { offset: headerOffset(), duration: 1.4, onComplete });
    } else {
      el.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth' });
      if (onComplete) setTimeout(onComplete, reduceMotion ? 0 : 700);
    }
  };

  /* ------------------------------------------------------------------
     Header: mobile menu, scrolled state, progress bar
  ------------------------------------------------------------------ */
  const burger = $('[data-burger]');
  const setMenu = (open) => {
    document.body.classList.toggle('nav-open', open);
    burger?.setAttribute('aria-expanded', String(open));
    if (lenis) open ? lenis.stop() : lenis.start();
  };
  burger?.addEventListener('click', () => setMenu(!document.body.classList.contains('nav-open')));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setMenu(false); });

  const progress = $('[data-progress]');
  let ticking = false;
  const onScroll = () => {
    const y = window.scrollY;
    const max = document.documentElement.scrollHeight - innerHeight;
    header?.classList.toggle('is-scrolled', y > 20);
    if (progress) progress.style.transform = `scaleX(${max > 0 ? y / max : 0})`;
    ticking = false;
  };
  addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  /* Dropdown: hover on desktop; tap and keyboard everywhere. */
  $$('[data-dropdown]').forEach((dropdown) => {
    const toggle = $('[data-dropdown-toggle]', dropdown);
    const setOpen = (open) => {
      dropdown.classList.toggle('is-open', open);
      toggle.setAttribute('aria-expanded', String(open));
    };
    toggle.addEventListener('click', (e) => {
      // e.detail is 0 for keyboard clicks; a mouse has already opened the menu by hovering.
      if (finePointer && e.detail) return;
      setOpen(!dropdown.classList.contains('is-open'));
    });
    if (finePointer) {
      dropdown.addEventListener('pointerenter', () => setOpen(true));
      dropdown.addEventListener('pointerleave', () => setOpen(false));
    }
    dropdown.addEventListener('focusout', (e) => {
      if (e.relatedTarget && !dropdown.contains(e.relatedTarget)) setOpen(false);
    });
    document.addEventListener('click', (e) => { if (!dropdown.contains(e.target)) setOpen(false); });
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape' || !dropdown.classList.contains('is-open')) return;
      setOpen(false);
      toggle.focus();
    });
  });

  /* ------------------------------------------------------------------
     In-page anchors + "request a quote" buttons that preselect a product
  ------------------------------------------------------------------ */
  document.addEventListener('click', (e) => {
    const link = e.target.closest('a[href*="#"]');
    if (!link) return;
    const url = new URL(link.href, location.href);
    if (url.pathname !== location.pathname || !url.hash) return;
    const target = document.getElementById(decodeURIComponent(url.hash.slice(1)));
    if (!target) return;

    e.preventDefault();
    setMenu(false);

    let focusAfter = null;
    if (link.hasAttribute('data-inquire')) {
      activateTab($('#tab-inquiry'));
      const select = $('#id_inq-product');
      if (select && link.dataset.inquire) select.value = link.dataset.inquire;
      focusAfter = $('#id_inq-name');
    }
    scrollToEl(target, () => focusAfter?.focus({ preventScroll: true }));
    history.replaceState(null, '', url.hash);
  });

  /* ------------------------------------------------------------------
     Tabs (WAI-ARIA pattern with arrow-key support)
  ------------------------------------------------------------------ */
  const tabs = $$('[data-tab]');
  function activateTab(tab) {
    if (!tab) return;
    tabs.forEach((t) => {
      const on = t === tab;
      t.classList.toggle('is-active', on);
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
    });
    if (animate) gsap.fromTo(`#${tab.getAttribute('aria-controls')}`, { autoAlpha: 0, y: 12 }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'power3.out' });
  }
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => activateTab(tab));
    tab.addEventListener('keydown', (e) => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      const next = tabs[(i + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length];
      next.focus();
      activateTab(next);
    });
  });

  /* ------------------------------------------------------------------
     File fields: list the chosen files with their sizes
  ------------------------------------------------------------------ */
  const formatSize = (bytes) => (bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} MB`);

  $$('[data-file-field]').forEach((field) => {
    const input = $('input[type="file"]', field);
    const list = $('[data-file-list]', field);
    const render = () => {
      list.replaceChildren(...Array.from(input.files, (file) => {
        const li = document.createElement('li');
        const name = document.createElement('span');
        const size = document.createElement('span');
        name.textContent = file.name;
        size.textContent = formatSize(file.size);
        li.append(name, size);
        return li;
      }));
    };
    input.addEventListener('change', render);
    input.closest('form')?.addEventListener('reset', () => setTimeout(render));
    ['dragenter', 'dragover'].forEach((t) => input.addEventListener(t, () => field.classList.add('is-dragover')));
    ['dragleave', 'drop'].forEach((t) => input.addEventListener(t, () => field.classList.remove('is-dragover')));
  });

  /* ------------------------------------------------------------------
     Product colours: the chosen swatch is named beside the legend and
     carried into the quote form's message as a "Цвят: …" line.
  ------------------------------------------------------------------ */
  $$('[data-color-picker]').forEach((picker) => {
    const name = $('[data-color-name]', picker);
    const note = $('[data-color-note]', picker);
    const chosen = () => $('input:checked', picker);
    picker.addEventListener('change', () => {
      const input = chosen();
      if (!input) return;
      if (name) name.textContent = input.value;
      if (note) note.textContent = input.dataset.note ? `— ${input.dataset.note}` : '';
    });
    $$('[data-color-quote]').forEach((link) => link.addEventListener('click', () => {
      const input = chosen();
      const message = $('#zapitvane textarea[name$="message"]');
      if (!input || !message) return;
      const line = `Цвят: ${input.value}`;
      const rest = message.value.split('\n').filter((l) => !l.startsWith('Цвят: '));
      message.value = [line, ...rest].join('\n').trimEnd();
      message.dispatchEvent(new Event('input', { bubbles: true }));
    }));
  });

  /* ------------------------------------------------------------------
     AJAX forms (fall back to a normal POST + redirect without JS)
  ------------------------------------------------------------------ */
  $$('[data-ajax-form]').forEach((form) => {
    const status = $('[data-form-status]', form);
    const button = $('button[type="submit"]', form);
    const prefix = form.dataset.prefix ? `${form.dataset.prefix}-` : '';

    const clearErrors = () => {
      $$('.field', form).forEach((f) => f.classList.remove('has-error'));
      $$('[data-error-for]', form).forEach((p) => { p.textContent = ''; });
      $$('[aria-invalid]', form).forEach((el) => el.removeAttribute('aria-invalid'));
    };

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearErrors();
      status.textContent = '';
      status.className = 'form__status';
      button.classList.add('is-loading');

      try {
        const res = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          headers: { Accept: 'application/json' },
          credentials: 'same-origin',
        });
        const data = await res.json();

        if (data.ok) {
          form.reset();
          status.textContent = data.message;
          status.classList.add('is-ok');
          if (animate) gsap.fromTo(status, { y: 10, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.5 });
          return;
        }

        let firstInvalid = null;
        Object.entries(data.errors || {}).forEach(([name, messages]) => {
          const slot = $(`[data-error-for="${prefix}${name}"]`, form);
          const input = form.elements[`${prefix}${name}`];
          if (slot) slot.textContent = messages.join(' ');
          if (input) {
            input.setAttribute('aria-invalid', 'true');
            input.setAttribute('aria-describedby', slot?.id || '');
            input.closest('.field')?.classList.add('has-error');
            firstInvalid ??= input;
          }
        });
        firstInvalid?.focus();
        status.textContent = data.message || 'Моля, проверете маркираните полета.';
        status.classList.add('is-error');
      } catch {
        status.textContent = 'Връзката прекъсна. Опитайте отново или ни се обадете.';
        status.classList.add('is-error');
      } finally {
        button.classList.remove('is-loading');
      }
    });
  });

  /* ------------------------------------------------------------------
     Product slider (Swiper) + category filter
  ------------------------------------------------------------------ */
  const sliderEl = $('[data-products-slider]');
  if (sliderEl && 'Swiper' in window) {
    const swiper = new Swiper(sliderEl, {
      slidesPerView: 1.08,
      spaceBetween: 16,
      speed: 750,
      grabCursor: true,
      watchSlidesProgress: true,
      keyboard: { enabled: true, onlyInViewport: true },
      mousewheel: { forceToAxis: true },
      navigation: { prevEl: '[data-slider-prev]', nextEl: '[data-slider-next]' },
      pagination: { el: '[data-slider-progress]', type: 'progressbar' },
      a11y: {
        prevSlideMessage: 'Предишен продукт',
        nextSlideMessage: 'Следващ продукт',
        firstSlideMessage: 'Това е първият продукт',
        lastSlideMessage: 'Това е последният продукт',
      },
      breakpoints: {
        640: { slidesPerView: 2.1, spaceBetween: 20 },
        1024: { slidesPerView: 3.15, spaceBetween: 24 },
        1440: { slidesPerView: 3.6, spaceBetween: 24 },
      },
    });

    const chips = $$('[data-filter]');
    chips.forEach((chip) => chip.addEventListener('click', () => {
      const filter = chip.dataset.filter;
      chips.forEach((c) => {
        c.classList.toggle('is-active', c === chip);
        c.setAttribute('aria-pressed', String(c === chip));
      });
      // Swiper skips slides whose computed display is "none".
      swiper.slides.forEach((slide) => {
        slide.style.display = filter === 'all' || slide.dataset.category === filter ? '' : 'none';
      });
      swiper.update();
      swiper.slideTo(0, 0);
      if (animate) {
        gsap.fromTo(swiper.slides.filter((s) => s.style.display !== 'none'),
          { autoAlpha: 0, y: 30 }, { autoAlpha: 1, y: 0, duration: 0.6, stagger: 0.06, ease: 'power3.out' });
      }
    }));
  }

  /* ------------------------------------------------------------------
     Product gallery (Swiper)
  ------------------------------------------------------------------ */
  const galleryEl = $('[data-gallery]');
  if (galleryEl && 'Swiper' in window) {
    const thumbs = new Swiper('[data-gallery-thumbs]', {
      slidesPerView: 4.5,
      spaceBetween: 8,
      watchSlidesProgress: true,
    });
    const gallery = new Swiper(galleryEl, {
      speed: 700,
      grabCursor: true,
      keyboard: { enabled: true, onlyInViewport: true },
      pagination: { el: '[data-gallery-pagination]', clickable: true },
      thumbs: { swiper: thumbs },
      a11y: { prevSlideMessage: 'Предишна снимка', nextSlideMessage: 'Следваща снимка' },
    });

    // Colour swatches <-> photos: picking a colour shows its photo, and
    // swiping to a photo of a colour selects that swatch.
    const picker = $('[data-color-picker]');
    if (picker) {
      const key = (s) => (s || '').trim().toLowerCase();
      const slides = gallery.slides;
      const slideFor = (color) => slides.findIndex((s) => key(s.dataset.color) === key(color));
      picker.addEventListener('change', (e) => {
        const index = slideFor(e.target.value);
        if (index >= 0 && index !== gallery.activeIndex) gallery.slideTo(index);
      });
      gallery.on('slideChange', () => {
        const color = key(slides[gallery.activeIndex]?.dataset.color);
        if (!color) return;
        const input = $$('input[type="radio"]', picker).find((i) => key(i.value) === color);
        if (input && !input.checked) {
          input.checked = true;
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
    }
  }

  /* ------------------------------------------------------------------
     Map facade: the Google iframe (and its cookies) loads only on request
  ------------------------------------------------------------------ */
  $$('[data-map]').forEach((map) => {
    $('[data-map-load]', map)?.addEventListener('click', () => {
      const iframe = document.createElement('iframe');
      iframe.src = map.dataset.src;
      iframe.title = 'Карта с местоположението на завода';
      iframe.loading = 'lazy';
      iframe.referrerPolicy = 'no-referrer-when-downgrade';
      iframe.allowFullscreen = true;
      map.append(iframe);
      iframe.addEventListener('load', () => $('.map__facade', map)?.remove(), { once: true });
    }, { once: true });
  });

  /* ------------------------------------------------------------------
     Motion (GSAP + ScrollTrigger)
  ------------------------------------------------------------------ */
  if (!animate) return;

  // Hero (home page only)
  const hero = $('[data-hero]');
  if (hero) {
    const intro = gsap.timeline({ defaults: { ease: 'expo.out' } });
    intro
      .to('.hero__line > span', { y: 0, duration: 1.4, stagger: 0.12 })
      .fromTo('[data-hero-fade]', { opacity: 0, y: 24 },
        { opacity: 1, y: 0, duration: 1.2, stagger: 0.08, clearProps: 'transform' }, '-=1.0');

    const path = $('[data-draw]');
    if (path) {
      const len = path.getTotalLength();
      gsap.fromTo(path, { strokeDasharray: len, strokeDashoffset: len },
        { strokeDashoffset: 0, duration: 2.6, ease: 'power2.inOut', delay: 0.3 });
    }

    // Parallax on the way out
    gsap.to('[data-hero-year]', {
      yPercent: -35, ease: 'none',
      scrollTrigger: { trigger: hero, start: 'top top', end: 'bottom top', scrub: true },
    });
    gsap.to('.hero__content', {
      y: -80, opacity: 0.2, ease: 'none',
      scrollTrigger: { trigger: hero, start: 'center top', end: 'bottom top', scrub: true },
    });

    // Glow follows the cursor (CSS transition does the easing)
    if (finePointer) {
      hero.addEventListener('pointermove', (e) => {
        const r = hero.getBoundingClientRect();
        hero.style.setProperty('--mx', `${((e.clientX - r.left) / r.width) * 100}%`);
        hero.style.setProperty('--my', `${((e.clientY - r.top) / r.height) * 100}%`);
      });
    }
  }

  // Counters
  $$('[data-count]').forEach((el) => {
    const end = Number(el.dataset.count);
    const counter = { v: end > 1000 ? end - 60 : 0 };
    gsap.to(counter, {
      v: end, duration: 2, ease: 'power2.out', delay: 0.6,
      onUpdate: () => { el.textContent = Math.round(counter.v); },
      scrollTrigger: { trigger: el, start: 'top 95%', once: true },
    });
  });

  // Generic reveals, batched so items entering together stagger nicely
  ScrollTrigger.batch('[data-reveal]', {
    start: 'top 88%',
    once: true,
    onEnter: (els) => gsap.to(els, { opacity: 1, y: 0, duration: 1, stagger: 0.08, ease: 'power3.out', overwrite: true }),
  });

  // Marquee: endless loop that speeds up and flips with scroll direction
  const marquee = $('[data-marquee]');
  if (marquee) {
    const loop = gsap.to(marquee, { xPercent: -50, duration: 40, ease: 'none', repeat: -1 });
    loop.totalTime(loop.duration() * 1000); // headroom so negative timeScale can run "backwards" forever
    ScrollTrigger.create({
      trigger: marquee, start: 'top bottom', end: 'bottom top',
      onUpdate: (self) => {
        const boost = gsap.utils.clamp(1, 6, Math.abs(self.getVelocity()) / 300);
        gsap.to(loop, { timeScale: boost * self.direction, duration: 0.2, overwrite: true });
        gsap.to(loop, { timeScale: self.direction, duration: 1.2, delay: 0.2, ease: 'power2.out' });
      },
    });
  }

  // About statement: words light up as you read
  $$('[data-split-words]').forEach((p) => {
    const words = p.textContent.trim().split(/\s+/);
    p.textContent = '';
    words.forEach((w, i) => {
      const span = document.createElement('span');
      span.className = 'word';
      span.textContent = w;
      p.append(span, i < words.length - 1 ? ' ' : '');
    });
    gsap.fromTo($$('.word', p), { opacity: 0.15 }, {
      opacity: 1, stagger: 0.05, ease: 'none',
      scrollTrigger: { trigger: p, start: 'top 80%', end: 'bottom 45%', scrub: true },
    });
  });

  // Services: pinned horizontal scroll on wide screens only
  const mm = gsap.matchMedia();
  mm.add('(min-width: 1024px)', () => {
    const section = $('[data-services]');
    const track = $('[data-services-track]');
    if (!section || !track) return;
    section.classList.add('is-horizontal');
    gsap.set($$('.service', track), { opacity: 1, y: 0 });
    const distance = () => Math.max(0, track.scrollWidth - innerWidth);
    const tween = gsap.to(track, {
      x: () => -distance(), ease: 'none',
      scrollTrigger: {
        trigger: section, pin: '[data-services-pin]', start: 'top top',
        end: () => `+=${distance()}`, scrub: 1, invalidateOnRefresh: true,
      },
    });
    return () => { tween.scrollTrigger?.kill(); tween.kill(); section.classList.remove('is-horizontal'); gsap.set(track, { clearProps: 'transform' }); };
  });

  // Magnetic buttons
  if (finePointer) {
    $$('[data-magnetic]').forEach((el) => {
      const xTo = gsap.quickTo(el, 'x', { duration: 0.6, ease: 'elastic.out(1, 0.4)' });
      const yTo = gsap.quickTo(el, 'y', { duration: 0.6, ease: 'elastic.out(1, 0.4)' });
      el.addEventListener('pointermove', (e) => {
        const r = el.getBoundingClientRect();
        xTo((e.clientX - r.left - r.width / 2) * 0.25);
        yTo((e.clientY - r.top - r.height / 2) * 0.35);
      });
      el.addEventListener('pointerleave', () => { xTo(0); yTo(0); });
    });
  }

  // Fonts change layout metrics; recompute trigger positions once they're in.
  document.fonts?.ready.then(() => ScrollTrigger.refresh());
})();
