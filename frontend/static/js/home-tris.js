// ── TRIS ─────────────────────────────────────────────────────────────────────
// Logica client-side del gioco Tris: gestione mosse, stato e rendering della board.

let trisSession = null;
let trisBoard   = Array(9).fill('');
let trisActive  = false;

function trisOpenModal() {
  document.getElementById('tris-overlay').style.display = 'flex';
  trisSession = null; trisActive = false;
  document.getElementById('tris-status').textContent = 'Scegli la difficoltà per iniziare.';
  document.getElementById('tris-reset').style.display = 'none';
  document.getElementById('tris-difficulty-select').style.display = 'flex';
  trisRenderBoard(Array(9).fill(''), null);
}

document.getElementById('tris-close').addEventListener('click', () => {
  document.getElementById('tris-overlay').style.display = 'none';
});
document.getElementById('tris-overlay').addEventListener('click', function (e) {
  if (e.target === this) this.style.display = 'none';
});

async function trisStartGame(difficulty) {
  document.getElementById('tris-difficulty-select').style.display = 'none';
  document.getElementById('tris-status').textContent = '⏳ Avvio partita…';
  try {
    const res = await fetch(`${API}/tris/new`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin', body: JSON.stringify({ difficulty }),
    });
    const data = await res.json();
    trisSession = data.sessionId; trisActive = true;
    trisApplyState(data);
  } catch {
    document.getElementById('tris-status').textContent = '⚠ Impossibile connettersi.';
  }
}

async function trisMove(cell) {
  if (!trisActive || !trisSession) return;
  if (trisBoard[cell] !== '') return;
  trisActive = false;
  try {
    const res = await fetch(`${API}/tris/move`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin', body: JSON.stringify({ sessionId: trisSession, cell }),
    });
    trisApplyState(await res.json());
  } catch {
    document.getElementById('tris-status').textContent = '⚠ Errore di rete.';
    trisActive = true;
  }
}

async function trisReset() {
  if (!trisSession) { trisOpenModal(); return; }
  document.getElementById('tris-status').textContent = '⏳ Reset…';
  document.getElementById('tris-reset').style.display = 'none';
  try {
    const res = await fetch(`${API}/tris/reset`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin', body: JSON.stringify({ sessionId: trisSession }),
    });
    const data = await res.json();
    trisSession = data.sessionId; trisActive = true;
    trisApplyState(data);
  } catch {
    document.getElementById('tris-status').textContent = '⚠ Errore di rete.';
  }
}

function trisApplyState(data) {
  trisBoard = data.board;
  const status = data.status;
  const statusMap = {
    ongoing:   '🟢 Il tuo turno — sei X',
    human_win: '🏆 Hai vinto!',
    ai_win:    "🤖 L'IA ha vinto.",
    draw:      '🤝 Pareggio!',
  };
  document.getElementById('tris-status').textContent = statusMap[status] || status;
  trisActive = status === 'ongoing';
  document.getElementById('tris-reset').style.display = status !== 'ongoing' ? 'inline-block' : 'none';
  trisRenderBoard(data.board, data.winnerCombo);
}

function trisRenderBoard(board, winnerCombo) {
  const boardEl = document.getElementById('tris-board');
  boardEl.innerHTML = '';
  board.forEach((cell, i) => {
    const btn = document.createElement('button');
    btn.style.cssText = `aspect-ratio:1;background:var(--darker-bg);border:1px solid var(--border);
      font-family:'Orbitron',sans-serif;font-size:1.6rem;cursor:pointer;
      color:${cell === 'X' ? 'var(--accent)' : 'var(--accent-purple,#a78bfa)'};transition:background 0.15s;
      ${winnerCombo && winnerCombo.includes(i) ? 'background:var(--accent);color:var(--darker-bg);' : ''}`;
    btn.textContent = cell;
    if (!cell && trisActive) {
      btn.addEventListener('click', () => trisMove(i));
      btn.addEventListener('mouseenter', () => btn.style.background = 'var(--card-hover-bg,#1a1f4a)');
      btn.addEventListener('mouseleave', () => btn.style.background = 'var(--darker-bg)');
    }
    boardEl.appendChild(btn);
  });
}
