'use strict';

// ── Theme toggle ──────────────────────────────────────────
const THEMES = ['dark', 'light'];

function getTheme() {
  return localStorage.getItem('ag-theme') || 'dark';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('ag-theme', theme);

  const icons = { dark: '☀', light: '🌑' };
  const labels = { dark: 'LIGHT', light: 'DARK' };

  ['theme-icon', 'theme-icon-mobile'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = icons[theme];
  });
  const lbl = document.getElementById('theme-label');
  if (lbl) lbl.textContent = labels[theme];
}

function toggleTheme() {
  const current = getTheme();
  const next = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
}

// Apply on load (also handled by inline script to prevent flash)
applyTheme(getTheme());

document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);
document.getElementById('theme-toggle-mobile')?.addEventListener('click', toggleTheme);

// Show mobile theme button on small screens
function checkMobileTheme() {
  const mob = document.getElementById('theme-toggle-mobile');
  if (mob) mob.style.display = window.innerWidth <= 768 ? 'flex' : 'none';
}
checkMobileTheme();
window.addEventListener('resize', checkMobileTheme);

// ── Mobile hamburger menu ─────────────────────────────────
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

// ── Install tabs ──────────────────────────────────────────
document.querySelectorAll('.install-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.install-tab').forEach(t => {
      t.classList.remove('active');
      t.setAttribute('aria-selected', 'false');
    });
    document.querySelectorAll('.install-pane').forEach(p => p.classList.remove('active'));

    tab.classList.add('active');
    tab.setAttribute('aria-selected', 'true');
    const pane = document.getElementById('tab-' + tab.dataset.tab);
    if (pane) pane.classList.add('active');
  });

  tab.addEventListener('keydown', e => {
    const tabs = [...document.querySelectorAll('.install-tab')];
    const i = tabs.indexOf(tab);
    if (e.key === 'ArrowRight') { e.preventDefault(); tabs[(i + 1) % tabs.length].focus(); }
    if (e.key === 'ArrowLeft')  { e.preventDefault(); tabs[(i - 1 + tabs.length) % tabs.length].focus(); }
  });
});

// ── Scroll-in cards ───────────────────────────────────────
if ('IntersectionObserver' in window) {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.opacity = '1';
        e.target.style.transform = 'translateY(0)';
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.08 });

  document.querySelectorAll('.card, .step, .roadmap-item').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(12px)';
    el.style.transition = 'opacity 350ms ease, transform 350ms ease';
    obs.observe(el);
  });
}

// ── Active nav link on scroll ─────────────────────────────
const sections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');

if ('IntersectionObserver' in window) {
  const navObs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        navLinks.forEach(l => l.style.color = '');
        const active = document.querySelector(`.nav-links a[href="#${entry.target.id}"]`);
        if (active) active.style.color = 'var(--accent)';
      }
    });
  }, { rootMargin: '-30% 0px -60% 0px' });

  sections.forEach(s => navObs.observe(s));
}

// ── Typewriter effect for hero tagline (dark only) ────────
function typewriter(el, text, speed = 40) {
  el.textContent = '';
  let i = 0;
  const timer = setInterval(() => {
    if (i < text.length) {
      el.textContent += text[i++];
    } else {
      clearInterval(timer);
    }
  }, speed);
}

window.addEventListener('DOMContentLoaded', () => {
  if (getTheme() === 'dark') {
    const tagline = document.querySelector('.hero-tagline');
    if (tagline) {
      const orig = tagline.textContent;
      typewriter(tagline, orig, 35);
    }
  }
});
