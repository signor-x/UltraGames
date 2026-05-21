// ── CURRENT USER ─────────────────────────────────────────────────────────────
// Carica una volta i dati dell'utente corrente e li condivide tra tutti i moduli.

const API = '';
let currentUser = null;

async function loadCurrentUser() {
  try {
    const res = await fetch(`${API}/api/auth/me`, { credentials: 'same-origin' });
    if (!res.ok) { window.location.href = '/login'; return; }
    currentUser = await res.json();

    document.getElementById('setting-name').value  = currentUser.name  || '';
    document.getElementById('setting-email').value = currentUser.email || '';

    const initials = (currentUser.name || 'UG')
      .split(' ').slice(0, 2)
      .map(w => w[0]?.toUpperCase() ?? '').join('');
    document.getElementById('avatar').textContent = initials;
    document.title = `${currentUser.name} — UltraGames`;
  } catch {
    window.location.href = '/login';
  }
}

loadCurrentUser();

// Logout
document.getElementById('btn-logout').addEventListener('click', async () => {
  await fetch(`${API}/api/auth/logout`, { method: 'POST', credentials: 'same-origin' });
  window.location.href = '/login';
});
