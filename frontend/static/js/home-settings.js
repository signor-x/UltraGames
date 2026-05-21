// ── SETTINGS ─────────────────────────────────────────────────────────────────
// Gestisce la sezione Impostazioni: aggiornamento profilo, password, eliminazione account.

function showSettingsMsg(id, text, type) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className = `settings-msg ${type}`;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 4000);
}

// ── Aggiorna profilo ─────────────────────────────────────────────────────────
document.getElementById('btn-update-profile').addEventListener('click', async () => {
  const name  = document.getElementById('setting-name').value.trim();
  const email = document.getElementById('setting-email').value.trim();
  try {
    const res = await fetch(`${API}/api/account/profile`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ name, email }),
    });
    const data = await res.json();
    if (!res.ok) { showSettingsMsg('profile-msg', data.error, 'err'); return; }
    showSettingsMsg('profile-msg', '✔ Profilo aggiornato.', 'ok');
    await loadCurrentUser();
  } catch {
    showSettingsMsg('profile-msg', 'Errore di rete.', 'err');
  }
});

// ── Cambia password ──────────────────────────────────────────────────────────
document.getElementById('btn-change-password').addEventListener('click', async () => {
  const current_password = document.getElementById('pw-current').value;
  const new_password     = document.getElementById('pw-new').value;
  const confirm          = document.getElementById('pw-confirm').value;

  if (new_password !== confirm) {
    showSettingsMsg('password-msg', 'Le password non coincidono.', 'err'); return;
  }
  try {
    const res = await fetch(`${API}/api/account/password`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ current_password, new_password }),
    });
    const data = await res.json();
    if (!res.ok) { showSettingsMsg('password-msg', data.error, 'err'); return; }
    showSettingsMsg('password-msg', '✔ Password cambiata.', 'ok');
    ['pw-current', 'pw-new', 'pw-confirm'].forEach(id => document.getElementById(id).value = '');
  } catch {
    showSettingsMsg('password-msg', 'Errore di rete.', 'err');
  }
});

// ── Elimina account ──────────────────────────────────────────────────────────
document.getElementById('btn-delete-account').addEventListener('click', async () => {
  const password = document.getElementById('delete-password').value;
  if (!password) { showSettingsMsg('delete-msg', 'Inserisci la password per confermare.', 'err'); return; }
  if (!confirm('⚠ Sei sicuro? Questa azione è irreversibile.')) return;
  try {
    const res = await fetch(`${API}/api/account/delete`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ password }),
    });
    const data = await res.json();
    if (!res.ok) { showSettingsMsg('delete-msg', data.error, 'err'); return; }
    window.location.href = '/login';
  } catch {
    showSettingsMsg('delete-msg', 'Errore di rete.', 'err');
  }
});
