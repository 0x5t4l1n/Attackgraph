'use strict';

// ── Theme ──────────────────────────────────────────────────
function getTheme() { return localStorage.getItem('ag-theme') || 'light'; }

function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  localStorage.setItem('ag-theme', t);
  const label = t === 'dark' ? 'Light Mode' : 'Dark Mode';
  const short  = t === 'dark' ? 'Light' : 'Dark';
  const el1 = document.getElementById('theme-label');
  const el2 = document.getElementById('theme-label-mobile');
  if (el1) el1.textContent = label;
  if (el2) el2.textContent = short;
}

applyTheme(getTheme());

document.getElementById('theme-toggle')?.addEventListener('click', () => {
  applyTheme(getTheme() === 'dark' ? 'light' : 'dark');
});
document.getElementById('theme-toggle-mobile')?.addEventListener('click', () => {
  applyTheme(getTheme() === 'dark' ? 'light' : 'dark');
});

// Show mobile theme btn
function syncMobileBtn() {
  const m = document.getElementById('theme-toggle-mobile');
  if (m) m.style.display = window.innerWidth <= 768 ? 'flex' : 'none';
}
syncMobileBtn();
window.addEventListener('resize', syncMobileBtn);

// ── Mobile menu ────────────────────────────────────────────
const hamburger = document.getElementById('hamburger');
const mobileMenu = document.getElementById('mobile-menu');
if (hamburger && mobileMenu) {
  hamburger.addEventListener('click', () => {
    const open = mobileMenu.classList.toggle('open');
    hamburger.setAttribute('aria-expanded', String(open));
  });
  mobileMenu.querySelectorAll('a').forEach(a =>
    a.addEventListener('click', () => {
      mobileMenu.classList.remove('open');
      hamburger.setAttribute('aria-expanded', 'false');
    })
  );
  document.addEventListener('click', e => {
    if (!hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
      mobileMenu.classList.remove('open');
      hamburger.setAttribute('aria-expanded', 'false');
    }
  });
}

// ── Install tabs ───────────────────────────────────────────
document.querySelectorAll('.install-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.install-tab').forEach(t => { t.classList.remove('active'); t.setAttribute('aria-selected','false'); });
    document.querySelectorAll('.install-pane').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    tab.setAttribute('aria-selected','true');
    const pane = document.getElementById('tab-' + tab.dataset.tab);
    if (pane) pane.classList.add('active');
  });
  tab.addEventListener('keydown', e => {
    const all = [...document.querySelectorAll('.install-tab')];
    const i = all.indexOf(tab);
    if (e.key === 'ArrowRight') { e.preventDefault(); all[(i+1) % all.length].focus(); }
    if (e.key === 'ArrowLeft')  { e.preventDefault(); all[(i-1+all.length) % all.length].focus(); }
  });
});

// ── Scroll fade-in ─────────────────────────────────────────
if ('IntersectionObserver' in window) {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
    });
  }, { threshold: 0.06 });
  document.querySelectorAll('.fade-in').forEach(el => obs.observe(el));
}

// ── Active nav on scroll ───────────────────────────────────
if ('IntersectionObserver' in window) {
  const secObs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        document.querySelectorAll('.nav-links a[href^="#"]').forEach(l => l.style.color = '');
        const a = document.querySelector(`.nav-links a[href="#${e.target.id}"]`);
        if (a) a.style.color = 'var(--gold)';
      }
    });
  }, { rootMargin: '-30% 0px -60% 0px' });
  document.querySelectorAll('section[id]').forEach(s => secObs.observe(s));
}
