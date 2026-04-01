const toggleBtn = document.getElementById('theme-toggle');
const sunIcon = document.getElementById('sun-icon');
const moonIcon = document.getElementById('moon-icon');
const statsDark = document.getElementById('stats-dark');
const statsLight = document.getElementById('stats-light');
const body = document.body;
const header = document.body.querySelector('header');
//const nav = document.body.querySelector('nav');

// Prüfe gespeicherte Einstellung
let themeStorage = null;
try {
  themeStorage = window.localStorage;
} catch (e) {
  themeStorage = null;
}

if (themeStorage && localStorage.getItem('theme') === 'dark') {
  body.classList.add('dark-mode');
  if (header) header.classList.add('dark-mode');
  if (sunIcon) sunIcon.classList.add('hidden');
  if (moonIcon) moonIcon.classList.remove('hidden');
}

if (toggleBtn) {
  toggleBtn.addEventListener('click', () => {
    const isDark = body.classList.toggle('dark-mode');
    if (header) header.classList.toggle('dark-mode');
    if (sunIcon) sunIcon.classList.toggle('hidden', isDark);
    if (moonIcon) moonIcon.classList.toggle('hidden', !isDark);
    if (statsLight) statsLight.classList.toggle('hidden', isDark);
    if (statsDark) statsDark.classList.toggle('hidden', !isDark);
    if (themeStorage) {
      themeStorage.setItem('theme', isDark ? 'dark' : 'light');
    }
  });
}
