// ── THEME ────────────────────────────────────────────────────────────────────
// Gestisce il toggle dark/light mode con persistenza su localStorage.

const themeToggle = document.getElementById('theme-toggle');

function setTheme(theme) {
  if (theme === 'light') {
    document.body.classList.add('light-mode');
    themeToggle.classList.add('light');
    localStorage.setItem('theme', 'light');
  } else {
    document.body.classList.remove('light-mode');
    themeToggle.classList.remove('light');
    localStorage.setItem('theme', 'dark');
  }
}

themeToggle.addEventListener('click', () => {
  const t = localStorage.getItem('theme') || 'dark';
  setTheme(t === 'dark' ? 'light' : 'dark');
});

setTheme(localStorage.getItem('theme') || 'dark');
