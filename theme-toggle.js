const toggleBtn = document.getElementById('theme-toggle');
const sunIcon = document.getElementById('sun-icon');
const moonIcon = document.getElementById('moon-icon');
const body = document.body;

// Prüfe gespeicherte Einstellung
let themeStorage = null;
try {
  themeStorage = window.localStorage;
} catch (e) {
  themeStorage = null;
}
if (themeStorage && localStorage.getItem('theme') === 'dark') {
  body.classList.add('dark-mode');
  sunIcon.classList.add('hidden');
  moonIcon.classList.remove('hidden');
}

toggleBtn.addEventListener('click', () => {
  const isDark = body.classList.toggle('dark-mode');
  sunIcon.classList.toggle('hidden', isDark);
  moonIcon.classList.toggle('hidden', !isDark);
  if (themeStorage) {
    themeStorage.setItem('theme', isDark ? 'dark' : 'light');
  }
});
