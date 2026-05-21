// ── NAVIGATION ──────────────────────────────────────────────────────────────
// Gestisce la navigazione tra le sezioni (sidebar links + service cards).

document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', function (e) {
    e.preventDefault();
    const section = this.dataset.section;
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    this.classList.add('active');
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(`${section}-section`).classList.add('active');
    if (section === 'games') loadGamesTab(currentGamesTab);
  });
});

document.querySelectorAll('.service-card[data-section]').forEach(card => {
  card.style.cursor = 'pointer';
  card.addEventListener('click', () => {
    const section = card.dataset.section;
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    const navLink = document.querySelector(`.nav-link[data-section="${section}"]`);
    if (navLink) navLink.classList.add('active');
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(`${section}-section`).classList.add('active');
    if (section === 'games') loadGamesTab(currentGamesTab);
  });
});
