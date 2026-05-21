// ── REACTION TEST ─────────────────────────────────────────────────────────────
// Logica client-side del Test di Reazione: polling fase, timer live, registrazione click.

let reactionSession = null;
let reactionPhase   = 'idle';
let reactionPollId  = null;
let reactionLiveRaf = null;
let reactionGreenAt = null;

// ── Timer live ───────────────────────────────────────────────────────────────
function reactionStartLiveTimer() {
  reactionGreenAt = Date.now();
  const el = document.getElementById('reaction-live-timer');
  el.style.visibility = 'visible';
  function tick() {
    el.textContent = Math.max(0, Date.now() - reactionGreenAt) + ' ms';
    reactionLiveRaf = requestAnimationFrame(tick);
  }
  reactionLiveRaf = requestAnimationFrame(tick);
}

function reactionStopLiveTimer(frozenMs) {
  if (reactionLiveRaf) { cancelAnimationFrame(reactionLiveRaf); reactionLiveRaf = null; }
  const el = document.getElementById('reaction-live-timer');
  if (frozenMs !== undefined) {
    el.textContent = frozenMs + ' ms';
    el.style.visibility = 'visible';
  } else {
    el.style.visibility = 'hidden';
    el.textContent = '0 ms';
  }
}

// ── Bottone stato ────────────────────────────────────────────────────────────
function reactionBtnEnable() {
  const btn = document.getElementById('reaction-btn');
  btn.disabled = false;
  btn.style.opacity = '1';
  btn.style.cursor = 'pointer';
}
function reactionBtnDisable() {
  const btn = document.getElementById('reaction-btn');
  btn.disabled = true;
  btn.style.opacity = '0.4';
  btn.style.cursor = 'not-allowed';
}

// ── Apertura modale ──────────────────────────────────────────────────────────
function reactionOpenModal() {
  document.getElementById('reaction-overlay').style.display = 'flex';
  reactionSession = null; reactionPhase = 'idle';
  clearInterval(reactionPollId);
  reactionStopLiveTimer();
  reactionRenderIdle();
  reactionStartSession();
}

document.getElementById('reaction-close').addEventListener('click', () => {
  clearInterval(reactionPollId);
  reactionStopLiveTimer();
  document.getElementById('reaction-overlay').style.display = 'none';
});
document.getElementById('reaction-overlay').addEventListener('click', function (e) {
  if (e.target === this) {
    clearInterval(reactionPollId);
    reactionStopLiveTimer();
    this.style.display = 'none';
  }
});

// ── Stato UI ─────────────────────────────────────────────────────────────────
function reactionRenderIdle() {
  document.getElementById('reaction-light').style.background = '#333';
  document.getElementById('reaction-status').textContent = 'Connessione in corso…';
  reactionBtnDisable();
  const startBtn = document.getElementById('reaction-start-btn');
  startBtn.style.display = 'inline-block';
  startBtn.disabled = true;
  startBtn.style.opacity = '0.4';
  startBtn.textContent = '⏳ Caricamento…';
}

function reactionRenderReady() {
  document.getElementById('reaction-light').style.background = '#ff4444';
  document.getElementById('reaction-status').textContent = 'Pronto? Clicca ▶ START per iniziare.';
  reactionBtnDisable();
  const startBtn = document.getElementById('reaction-start-btn');
  startBtn.style.display = 'inline-block';
  startBtn.disabled = false;
  startBtn.style.opacity = '1';
  startBtn.textContent = '▶ START';
}

// ── Sessione ─────────────────────────────────────────────────────────────────
async function reactionStartSession() {
  try {
    const res = await fetch(`${API}/reaction/new`, {
      method: 'POST', credentials: 'same-origin',
    });
    const data = await res.json();
    reactionSession = data.sessionId;
    reactionRenderReady();
  } catch {
    document.getElementById('reaction-status').textContent = '⚠ Errore connessione.';
  }
}

// ── Start round ──────────────────────────────────────────────────────────────
document.getElementById('reaction-start-btn').addEventListener('click', async () => {
  if (!reactionSession) return;
  document.getElementById('reaction-start-btn').style.display = 'none';
  document.getElementById('reaction-status').textContent = '🔴 Aspetta il verde…';
  document.getElementById('reaction-light').style.background = '#ff4444';
  reactionBtnDisable();
  reactionStopLiveTimer();
  try {
    await fetch(`${API}/reaction/start`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin', body: JSON.stringify({ sessionId: reactionSession }),
    });
    reactionPhase = 'waiting';
    reactionPollId = setInterval(async () => {
      try {
        const res = await fetch(`${API}/reaction/phase?sessionId=${reactionSession}`, { credentials: 'same-origin' });
        const d   = await res.json();
        if (d.phase === 'green') {
          clearInterval(reactionPollId);
          reactionPhase = 'green';
          document.getElementById('reaction-light').style.background = '#00ff00';
          document.getElementById('reaction-status').textContent = '🟢 CLICCA ORA!';
          reactionBtnEnable();
          reactionStartLiveTimer();
        }
      } catch { clearInterval(reactionPollId); }
    }, 50);
  } catch {
    document.getElementById('reaction-status').textContent = '⚠ Errore di rete.';
  }
});

// ── Click registrazione ──────────────────────────────────────────────────────
document.getElementById('reaction-btn').addEventListener('click', async () => {
  if (reactionPhase !== 'green' && reactionPhase !== 'waiting') return;
  clearInterval(reactionPollId);
  const clickAtMs = Date.now();
  const frozenMs  = reactionGreenAt ? Math.max(0, clickAtMs - reactionGreenAt) : undefined;
  reactionStopLiveTimer(frozenMs);
  reactionBtnDisable();
  try {
    const res = await fetch(`${API}/reaction/click`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ sessionId: reactionSession, clickAtMs }),
    });
    const data   = await res.json();
    const result = data.result || {};
    const rating = data.rating;

    if (result.clickedEarly) {
      reactionStopLiveTimer();
      document.getElementById('reaction-light').style.background = '#ffaa00';
      document.getElementById('reaction-status').textContent = '⚠ Troppo presto! Aspetta il verde.';
    } else {
      document.getElementById('reaction-light').style.background = '#00cc00';
      const reactionMs  = result.reactionMs ?? frozenMs ?? 0;
      const ratingText  = rating ? `${rating.label} ${rating.emoji}` : '';
      document.getElementById('reaction-status').textContent =
        `✅ ${reactionMs} ms${ratingText ? ` — ${ratingText}` : ''}`;
    }

    document.getElementById('reaction-start-btn').textContent = '↺ Riprova';
    document.getElementById('reaction-start-btn').style.display = 'inline-block';
  } catch {
    document.getElementById('reaction-status').textContent = '⚠ Errore di rete.';
  }
});
