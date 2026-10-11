'use strict';

// ── Theme ───────────────────────────────────────────────────
function getTheme() { return localStorage.getItem('ag-theme') || 'dark'; }

function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  localStorage.setItem('ag-theme', t);
  const el = document.getElementById('theme-label');
  if (el) el.textContent = t === 'dark' ? 'Light' : 'Dark';
}

applyTheme(getTheme());

document.getElementById('theme-toggle')?.addEventListener('click', () => {
  applyTheme(getTheme() === 'dark' ? 'light' : 'dark');
});

// ── Mobile menu ──────────────────────────────────────────────
const hamburger = document.getElementById('hamburger');
const mobileMenu = document.getElementById('mobile-menu');

if (hamburger && mobileMenu) {
  hamburger.addEventListener('click', () => {
    const open = mobileMenu.classList.toggle('open');
    hamburger.setAttribute('aria-expanded', String(open));
    hamburger.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  });
  mobileMenu.querySelectorAll('a').forEach(a =>
    a.addEventListener('click', () => {
      mobileMenu.classList.remove('open');
      hamburger.setAttribute('aria-expanded', 'false');
      hamburger.setAttribute('aria-label', 'Open menu');
    })
  );
  document.addEventListener('click', e => {
    if (!hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
      mobileMenu.classList.remove('open');
      hamburger.setAttribute('aria-expanded', 'false');
    }
  });
}

// ── Install tabs ─────────────────────────────────────────────
document.querySelectorAll('.install-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.install-tab').forEach(t => {
      t.classList.remove('active'); t.setAttribute('aria-selected', 'false');
    });
    document.querySelectorAll('.install-pane').forEach(p => p.classList.remove('active'));
    tab.classList.add('active'); tab.setAttribute('aria-selected', 'true');
    const pane = document.getElementById('tab-' + tab.dataset.tab);
    if (pane) pane.classList.add('active');
  });
  tab.addEventListener('keydown', e => {
    const all = [...document.querySelectorAll('.install-tab')];
    const i = all.indexOf(tab);
    if (e.key === 'ArrowRight') { e.preventDefault(); all[(i + 1) % all.length].focus(); }
    if (e.key === 'ArrowLeft')  { e.preventDefault(); all[(i - 1 + all.length) % all.length].focus(); }
  });
});

// ── FAQ accordion ────────────────────────────────────────────
document.querySelectorAll('.faq-q').forEach(btn => {
  btn.addEventListener('click', () => {
    const answer = btn.closest('.faq-item').querySelector('.faq-a');
    const open   = btn.getAttribute('aria-expanded') === 'true';

    // Close all
    document.querySelectorAll('.faq-q').forEach(b => {
      b.setAttribute('aria-expanded', 'false');
      b.closest('.faq-item').querySelector('.faq-a').classList.remove('open');
    });

    // Toggle this
    if (!open) {
      btn.setAttribute('aria-expanded', 'true');
      answer.classList.add('open');
    }
  });
  btn.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      btn.setAttribute('aria-expanded', 'false');
      btn.closest('.faq-item').querySelector('.faq-a').classList.remove('open');
    }
  });
});

// ── Fade-in ──────────────────────────────────────────────────
const fadeEls = document.querySelectorAll('.fade-in');
if ('IntersectionObserver' in window) {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
    });
  }, { threshold: 0.05, rootMargin: '0px 0px -30px 0px' });
  fadeEls.forEach(el => obs.observe(el));
} else {
  fadeEls.forEach(el => el.classList.add('visible'));
}
// Safety net
setTimeout(() => fadeEls.forEach(el => el.classList.add('visible')), 1000);

// ── Active nav highlight ─────────────────────────────────────
if ('IntersectionObserver' in window) {
  const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');
  const secObs   = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        navLinks.forEach(l => l.removeAttribute('aria-current'));
        const a = document.querySelector(`.nav-links a[href="#${e.target.id}"]`);
        if (a) a.setAttribute('aria-current', 'true');
      }
    });
  }, { rootMargin: '-30% 0px -60% 0px' });
  document.querySelectorAll('section[id], div[id]').forEach(s => secObs.observe(s));
}
