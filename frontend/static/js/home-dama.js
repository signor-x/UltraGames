// ── DAMA ─────────────────────────────────────────────────────────────────────
// Logica client-side della Dama: selezione pezzi, mosse legali e rendering della scacchiera.

let damaSession  = null;
let damaLegal    = [];
let damaSelected = null;

// Traccia delle celle percorse dalla mossa AI (per evidenziazione temporanea)
// Struttura: [ { r, c, type: 'from'|'to'|'capture' } ]
let damaAiTrail  = [];
let damaAiTrailTimer = null;

function damaOpenModal() {
  document.getElementById('dama-overlay').style.display = 'flex';
  damaSession = null; damaLegal = []; damaSelected = null;
  damaAiTrail = [];
  document.getElementById('dama-status').textContent = 'Scegli la difficoltà per iniziare.';
  document.getElementById('dama-reset').style.display = 'none';
  document.getElementById('dama-difficulty-select').style.display = 'flex';
  document.getElementById('dama-board').innerHTML = '';
}

document.getElementById('dama-close').addEventListener('click', () => {
  document.getElementById('dama-overlay').style.display = 'none';
});
document.getElementById('dama-overlay').addEventListener('click', function (e) {
  if (e.target === this) this.style.display = 'none';
});

async function damaStartGame(difficulty) {
  document.getElementById('dama-difficulty-select').style.display = 'none';
  document.getElementById('dama-status').textContent = '⏳ Avvio partita…';
  try {
    const res = await fetch(`${API}/dama/new`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin', body: JSON.stringify({ difficulty }),
    });
    const data = await res.json();
    damaSession = data.sessionId;
    damaLegal   = data.legalMoves || [];
    damaRenderState(data);
  } catch {
    document.getElementById('dama-status').textContent = '⚠ Impossibile connettersi.';
  }
}

async function damaReset() {
  if (!damaSession) { damaOpenModal(); return; }
  document.getElementById('dama-reset').style.display = 'none';
  damaAiTrail = [];
  if (damaAiTrailTimer) { clearTimeout(damaAiTrailTimer); damaAiTrailTimer = null; }
  try {
    const res = await fetch(`${API}/dama/reset`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin', body: JSON.stringify({ sessionId: damaSession }),
    });
    const data = await res.json();
    damaSession  = data.sessionId;
    damaLegal    = data.legalMoves || [];
    damaSelected = null;
    damaRenderState(data);
  } catch {
    document.getElementById('dama-status').textContent = '⚠ Errore di rete.';
  }
}

// Calcola la traccia visiva dalla mossa AI (path + captures)
function damaSetAiTrail(aiMove) {
  if (!aiMove) { damaAiTrail = []; return; }

  const trail = [];
  if (aiMove.path && aiMove.path.length > 0) {
    // Cella di partenza
    trail.push({ r: aiMove.path[0][0], c: aiMove.path[0][1], type: 'ai-from' });
    // Celle intermedie (se rafla)
    for (let i = 1; i < aiMove.path.length - 1; i++) {
      trail.push({ r: aiMove.path[i][0], c: aiMove.path[i][1], type: 'ai-mid' });
    }
    // Cella di arrivo
    const last = aiMove.path[aiMove.path.length - 1];
    trail.push({ r: last[0], c: last[1], type: 'ai-to' });
  }
  // Celle catturate
  if (aiMove.captures) {
    for (const cap of aiMove.captures) {
      trail.push({ r: cap[0], c: cap[1], type: 'ai-capture' });
    }
  }
  damaAiTrail = trail;
}

function damaRenderState(data) {
  const statusMap = {
    ongoing:    '🟢 Il tuo turno (bianco)',
    white_wins: '🏆 Hai vinto!',
    black_wins: "🤖 L'IA ha vinto.",
  };
  document.getElementById('dama-status').textContent = statusMap[data.status] || data.status;
  const gameOver = data.status !== 'ongoing';
  document.getElementById('dama-reset').style.display = gameOver ? 'inline-block' : 'none';

  // Imposta la traccia AI e cancella il timer precedente
  if (damaAiTrailTimer) { clearTimeout(damaAiTrailTimer); damaAiTrailTimer = null; }
  damaSetAiTrail(data.aiMove);
  damaRenderBoard(data.board, data.legalMoves || [], gameOver);

  // Dopo 2 secondi, cancella la traccia e ri-renderizza
  if (damaAiTrail.length > 0) {
    damaAiTrailTimer = setTimeout(() => {
      damaAiTrail = [];
      damaRenderBoard(data.board, data.legalMoves || [], gameOver);
    }, 2000);
  }
}

function damaRenderBoard(board, legal, gameOver) {
  const el = document.getElementById('dama-board');
  el.innerHTML = '';
  el.style.cssText = [
    'display:grid',
    'grid-template-columns:repeat(8,1fr)',
    'gap:0',
    'max-width:420px',
    'margin:0 auto 1rem',
    'border:5px solid #c8960a',
    'box-shadow:0 0 0 2px #4a2e10,0 0 28px rgba(212,160,23,0.22),inset 0 0 18px rgba(0,0,0,0.5)',
  ].join(';');

  const legalFromSelected = damaSelected
    ? legal.filter(m => m.path[0][0] === damaSelected[0] && m.path[0][1] === damaSelected[1])
    : [];
  const legalDestinations = legalFromSelected.map(m => m.path[m.path.length - 1]);

  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const cell      = document.createElement('div');
      const isDark    = (r + c) % 2 === 1;
      const piece     = board[r][c];
      const isSel     = damaSelected && damaSelected[0] === r && damaSelected[1] === c;
      const isDest    = legalDestinations.some(d => d[0] === r && d[1] === c);
      const isLegalFrom = !gameOver && legal.some(m => m.path[0][0] === r && m.path[0][1] === c);

      // Tipo di traccia AI su questa cella (se presente)
      const trailCell = damaAiTrail.find(t => t.r === r && t.c === c);

      let cellBg;
      if (isSel)                          cellBg = '#3a6e1a';
      else if (isDest)                    cellBg = '#7a5a0a';
      else if (trailCell?.type === 'ai-from')    cellBg = '#1a3a6a';
      else if (trailCell?.type === 'ai-to')      cellBg = '#1a5a3a';
      else if (trailCell?.type === 'ai-mid')     cellBg = '#2a3a5a';
      else if (trailCell?.type === 'ai-capture') cellBg = '#6a1a1a';
      else if (isDark)                    cellBg = '#5c3210';
      else                               cellBg = '#c8a060';

      let cellBorder;
      if (isSel)                          cellBorder = '2px solid #7ec850';
      else if (isDest)                    cellBorder = '2px solid #d4a017';
      else if (trailCell?.type === 'ai-from')    cellBorder = '2px solid #4a8adf';
      else if (trailCell?.type === 'ai-to')      cellBorder = '2px solid #4adf8a';
      else if (trailCell?.type === 'ai-capture') cellBorder = '2px solid #df4a4a';
      else if (trailCell?.type === 'ai-mid')     cellBorder = '2px solid #4a6aaf';
      else                               cellBorder = '1px solid rgba(0,0,0,0.2)';

      cell.style.cssText = [
        'width:100%', 'aspect-ratio:1', 'display:flex', 'align-items:center',
        'justify-content:center', 'position:relative',
        `background:${cellBg}`, `border:${cellBorder}`,
        `cursor:${(isLegalFrom || isDest) && !gameOver ? 'pointer' : 'default'}`,
        'transition:background 0.3s,border 0.3s',
      ].join(';');

      // Pallino destinazione mossa
      if (isDest && !piece) {
        const dot = document.createElement('div');
        dot.style.cssText = 'width:28%;height:28%;border-radius:50%;background:rgba(212,160,23,0.55);pointer-events:none;';
        cell.appendChild(dot);
      }

      // Indicatore traccia AI (freccia/simbolo) sulle celle vuote della traccia
      if (trailCell && !piece) {
        const marker = document.createElement('div');
        const icons = { 'ai-from': '●', 'ai-to': '●', 'ai-mid': '·', 'ai-capture': '✕' };
        const colors = { 'ai-from': 'rgba(74,138,223,0.7)', 'ai-to': 'rgba(74,223,138,0.7)', 'ai-mid': 'rgba(74,106,175,0.5)', 'ai-capture': 'rgba(223,74,74,0.7)' };
        marker.textContent = icons[trailCell.type] || '·';
        marker.style.cssText = `font-size:1.1em;color:${colors[trailCell.type]};pointer-events:none;`;
        cell.appendChild(marker);
      }

      if (piece) {
        const isWhite = piece.color === 'white';
        const isKing  = piece.is_king;
        const disc    = document.createElement('div');
        const bg      = isWhite
          ? 'radial-gradient(circle at 35% 35%, #fff9f0, #d4b88a 60%, #8c6030)'
          : 'radial-gradient(circle at 35% 35%, #4a3020, #1a1008 60%, #0a0804)';
        const border  = isWhite ? '2px solid #a07830' : '2px solid #5a4020';
        const shadow  = isWhite
          ? '0 3px 8px rgba(0,0,0,0.55), inset 0 1px 2px rgba(255,255,255,0.4)'
          : '0 3px 8px rgba(0,0,0,0.8), inset 0 1px 2px rgba(255,255,255,0.08)';
        disc.style.cssText = [
          'width:76%', 'height:76%', 'border-radius:50%',
          `background:${bg}`, `border:${border}`, `box-shadow:${shadow}`,
          'display:flex', 'align-items:center', 'justify-content:center',
          'pointer-events:none', 'flex-shrink:0', 'flex-direction:column', 'gap:0',
        ].join(';');

        if (isKing) {
          // Corona
          const crown = document.createElement('span');
          crown.textContent = isWhite ? '♔' : '♚';
          crown.style.cssText = `font-size:0.75em;line-height:1;color:${isWhite ? '#c8960a' : '#d4a017'};text-shadow:0 1px 3px rgba(0,0,0,0.7);`;
          disc.appendChild(crown);
          // ID breve del damone (ultime 4 cifre hex)
          const idTag = document.createElement('span');
          const shortId = piece.id ? piece.id.replace(/-/g, '').slice(-4).toUpperCase() : '';
          idTag.textContent = shortId;
          idTag.style.cssText = [
            'font-size:0.30em',
            'line-height:1',
            `color:${isWhite ? 'rgba(100,60,0,0.85)' : 'rgba(220,180,80,0.85)'}`,
            'letter-spacing:0.04em',
            'font-family:monospace',
            'margin-top:1px',
          ].join(';');
          disc.appendChild(idTag);
        }
        cell.appendChild(disc);
      }

      if (!gameOver) {
        if (piece && piece.color === 'white' && isLegalFrom) {
          cell.addEventListener('click', () => {
            damaSelected = [r, c];
            damaRenderBoard(board, legal, false);
          });
        } else if (isDest) {
          cell.addEventListener('click', () => damaMove(damaSelected, [r, c], legal, board));
        }
      }

      el.appendChild(cell);
    }
  }
}

async function damaMove(from, to, legal, board) {
  const move = legal.find(m =>
    m.path[0][0] === from[0] && m.path[0][1] === from[1] &&
    m.path[m.path.length - 1][0] === to[0] && m.path[m.path.length - 1][1] === to[1]
  );
  if (!move) return;
  damaSelected = null;
  document.getElementById('dama-status').textContent = '⏳ Mossa…';
  try {
    const res = await fetch(`${API}/dama/move`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ sessionId: damaSession, move }),
    });
    const data = await res.json();
    damaLegal = data.legalMoves || [];
    damaRenderState(data);
  } catch {
    document.getElementById('dama-status').textContent = '⚠ Errore di rete.';
  }
}
