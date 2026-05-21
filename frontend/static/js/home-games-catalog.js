// ── GAMES CATALOG ────────────────────────────────────────────────────────────
// Definisce il catalogo giochi e renderizza la griglia nella tab "Gioca".

let currentGamesTab   = 'play';
let currentRankingGame = 'tris';

// ── Tab switching ────────────────────────────────────────────────────────────
document.querySelectorAll('.games-tab').forEach(btn => {
  btn.addEventListener('click', function () {
    document.querySelectorAll('.games-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.games-tab-panel').forEach(p => p.classList.remove('active'));
    this.classList.add('active');
    const tab = this.dataset.tab;
    currentGamesTab = tab;
    document.getElementById(`tab-${tab}`).classList.add('active');
    loadGamesTab(tab);
  });
});

function loadGamesTab(tab) {
  if (tab === 'play')    renderGamesGrid();
  if (tab === 'mystats') loadMyStats();
  if (tab === 'ranking') loadRanking(currentRankingGame);
}

// ── Ranking game selector ────────────────────────────────────────────────────
document.querySelectorAll('.ranking-pick').forEach(btn => {
  btn.addEventListener('click', function () {
    document.querySelectorAll('.ranking-pick').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    currentRankingGame = this.dataset.game;
    loadRanking(currentRankingGame);
  });
});

// Ranking search filter
document.getElementById('ranking-search').addEventListener('input', function () {
  const q = this.value.toLowerCase();
  document.querySelectorAll('#ranking-content tbody tr').forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
});

// ── Le mie statistiche ───────────────────────────────────────────────────────
async function loadMyStats() {
  const el = document.getElementById('mystats-content');
  el.innerHTML = '<p style="color:var(--text-muted);font-size:0.75rem;">Caricamento…</p>';
  try {
    const res = await fetch(`${API}/api/stats/me`, { credentials: 'same-origin' });
    if (!res.ok) { el.innerHTML = '<p style="color:#ff3333;">Errore nel caricamento delle statistiche.</p>'; return; }
    const s = await res.json();

    el.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1.25rem;">
        <div class="settings-panel" style="text-align:center;">
          <h3>⊞ Tris</h3>
          <table class="stats-table" style="margin-top:0.5rem;">
            <thead><tr><th>Vinte</th><th>Perse</th><th>Pareggiate</th></tr></thead>
            <tbody><tr>
              <td style="color:var(--primary);font-weight:700;">${s.tris.wins}</td>
              <td style="color:#ff5555;">${s.tris.losses}</td>
              <td style="color:var(--accent);">${s.tris.draws}</td>
            </tr></tbody>
          </table>
        </div>
        <div class="settings-panel" style="text-align:center;">
          <h3>♟️ Dama</h3>
          <table class="stats-table" style="margin-top:0.5rem;">
            <thead><tr><th>Vinte</th><th>Perse</th></tr></thead>
            <tbody><tr>
              <td style="color:var(--primary);font-weight:700;">${s.dama.wins}</td>
              <td style="color:#ff5555;">${s.dama.losses}</td>
            </tr></tbody>
          </table>
        </div>
        <div class="settings-panel" style="text-align:center;">
          <h3>🚦 Reazione</h3>
          <table class="stats-table" style="margin-top:0.5rem;">
            <thead><tr><th>Miglior tempo</th><th>Tentativi</th></tr></thead>
            <tbody><tr>
              <td style="color:var(--primary);font-weight:700;">
                ${s.reaction.best_ms != null ? s.reaction.best_ms + ' ms' : '—'}
              </td>
              <td style="color:var(--accent);">${s.reaction.attempts}</td>
            </tr></tbody>
          </table>
        </div>
      </div>`;
  } catch {
    el.innerHTML = '<p style="color:#ff3333;">Errore di rete.</p>';
  }
}

// ── Ranking ──────────────────────────────────────────────────────────────────
async function loadRanking(game) {
  const el = document.getElementById('ranking-content');
  el.innerHTML = '<p style="color:var(--text-muted);font-size:0.75rem;">Caricamento…</p>';
  document.getElementById('ranking-search').value = '';
  try {
    const res = await fetch(`${API}/api/stats/ranking/${game}`, { credentials: 'same-origin' });
    if (!res.ok) { el.innerHTML = '<p style="color:#ff3333;">Errore nel caricamento.</p>'; return; }
    const { ranking } = await res.json();

    if (!ranking.length) {
      el.innerHTML = '<p style="color:var(--text-muted);font-size:0.75rem;">Nessun dato ancora.</p>';
      return;
    }

    const myName = currentUser?.name || '';
    let thead = '', rowFn;

    if (game === 'tris') {
      thead = '<tr><th>#</th><th>Giocatore</th><th>Vinte</th><th>Perse</th><th>Pareggiate</th></tr>';
      rowFn = (r, i) => `<td>${i + 1}</td><td>${r.name}</td><td>${r.wins}</td><td>${r.losses}</td><td>${r.draws}</td>`;
    } else if (game === 'dama') {
      thead = '<tr><th>#</th><th>Giocatore</th><th>Vinte</th><th>Perse</th></tr>';
      rowFn = (r, i) => `<td>${i + 1}</td><td>${r.name}</td><td>${r.wins}</td><td>${r.losses}</td>`;
    } else {
      thead = '<tr><th>#</th><th>Giocatore</th><th>Miglior tempo (ms)</th><th>Tentativi</th></tr>';
      rowFn = (r, i) => `<td>${i + 1}</td><td>${r.name}</td><td>${r.best_ms}</td><td>${r.attempts}</td>`;
    }

    const ranks = { 0: 'rank-1', 1: 'rank-2', 2: 'rank-3' };
    const rows = ranking.map((r, i) => {
      const cls = [ranks[i] || '', r.name === myName ? 'rank-me' : ''].filter(Boolean).join(' ');
      return `<tr class="${cls}">${rowFn(r, i)}</tr>`;
    }).join('');

    el.innerHTML = `
      <div style="overflow-x:auto;">
        <table class="stats-table">
          <thead>${thead}</thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  } catch {
    el.innerHTML = '<p style="color:#ff3333;">Errore di rete.</p>';
  }
}

// ── Griglia giochi ───────────────────────────────────────────────────────────
const GAMES_CATALOG = [
  {
    icon: '⊞',
    title: 'Tris',
    description: "Sfida l'intelligenza artificiale al classico Tris. Scegli la difficoltà: casuale o Minimax imbattibile.",
    available: true,
    action: () => trisOpenModal(),
  },
  {
    icon: '♟️',
    title: 'Dama',
    description: "Sfida l'intelligenza artificiale in una partita classica di dama. Ogni mossa conta!",
    available: true,
    action: () => damaOpenModal(),
  },
  {
    icon: '🚦',
    title: 'Test di Reazione',
    description: "Metti alla prova i tuoi riflessi. Clicca appena il semaforo diventa verde — più veloce sei, meglio è!",
    available: true,
    action: () => reactionOpenModal(),
  },
  {
    icon: '🧠',
    title: 'Memo',
    description: 'Work in progress: modalità Memo in sviluppo, presto allenamenti per la memoria con sfide dedicate.',
    available: false,
    action: null,
  },
];

function renderGamesGrid() {
  const grid = document.getElementById('games-grid');
  grid.innerHTML = '';
  GAMES_CATALOG.forEach(game => {
    const card = document.createElement('div');
    card.className = 'game-card';
    if (!game.available) card.style.cssText = 'opacity:0.35;pointer-events:none;border-style:dashed;';
    const btn = document.createElement('button');
    btn.className = 'btn-game';
    btn.textContent = game.available ? '▶ Gioca Ora' : 'In Arrivo';
    if (game.available && game.action) btn.addEventListener('click', game.action);
    card.innerHTML = `<span class="game-icon">${game.icon}</span><h3>${game.title}</h3><p>${game.description}</p>`;
    card.appendChild(btn);
    grid.appendChild(card);
  });
}

document.addEventListener('DOMContentLoaded', renderGamesGrid);
