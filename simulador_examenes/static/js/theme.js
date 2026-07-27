/* ==========================================================
   Theme Toggle — Radioaficion Chile
   Default theme is dark (the instrument-panel identity).
   Applies saved theme immediately to prevent flash.
   ========================================================== */

(function () {
  'use strict';

  var KEY = 'ra-theme';

  var saved = localStorage.getItem(KEY) || 'dark';
  document.documentElement.setAttribute('data-theme', saved);

  window.toggleTheme = function () {
    var current = document.documentElement.getAttribute('data-theme');
    var next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem(KEY, next);
    updateIcon(next);
  };

  function updateIcon(theme) {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    var icon = btn.querySelector('i');
    if (!icon) return;
    icon.classList.remove('bi-sun-fill', 'bi-moon-fill');
    icon.classList.add(theme === 'dark' ? 'bi-sun-fill' : 'bi-moon-fill');
    btn.setAttribute('aria-label', theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      updateIcon(document.documentElement.getAttribute('data-theme'));
    });
  } else {
    updateIcon(document.documentElement.getAttribute('data-theme'));
  }
})();
