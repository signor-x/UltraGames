/* ── STATE ───────────────────────────────────────────────────── */
  let allUsers   = [];
  let filtered   = [];
  let sortField  = 'name';
  let sortAsc    = true;
  let editUserId = null;
  let banUserId  = null;

  /* ── INIT ────────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', async () => {
    await verifyAdmin();
    loadUsers();
  });

  async function verifyAdmin() {
    try {
      const res  = await fetch('/api/auth/me');
      const data = await res.json();
      if (!res.ok || data.email !== 'admin@ultragames.local') {
        window.location.href = '/home';
      }
      document.getElementById('admin-email').textContent = data.email;
    } catch {
      window.location.href = '/login';
    }
  }

  /* ── LOAD USERS ──────────────────────────────────────────────── */
  async function loadUsers() {
    try {
      const res  = await fetch('/api/admin/users');
      if (res.status === 401 || res.status === 403) {
        window.location.href = '/login';
        return;
      }
      const data = await res.json();
      allUsers = data.users || [];
      updateOverview();
      applyFilter();
    } catch (err) {
      showToast('Errore nel caricamento utenti.', 'error');
    }
  }

  function updateOverview() {
    document.getElementById('stat-total').textContent = allUsers.length;

    let trisGames = 0, damaGames = 0, reactGames = 0;
    allUsers.forEach(u => {
      const s = u.stats;
      trisGames  += (s.tris.wins     || 0) + (s.tris.losses     || 0) + (s.tris.draws || 0);
      damaGames  += (s.dama.wins     || 0) + (s.dama.losses     || 0);
      reactGames += (s.reaction.attempts || 0);
    });

    document.getElementById('stat-tris').textContent     = trisGames;
    document.getElementById('stat-dama').textContent     = damaGames;
    document.getElementById('stat-reaction').textContent = reactGames;
  }

  /* ── FILTER / SORT ───────────────────────────────────────────── */
  function filterUsers() {
    const q = document.getElementById('search').value.toLowerCase();
    filtered = allUsers.filter(u =>
      u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
    );
    renderTable();
  }

  function applyFilter() {
    filtered = [...allUsers];
    renderTable();
  }

  function sortBy(field) {
    if (sortField === field) { sortAsc = !sortAsc; }
    else { sortField = field; sortAsc = true; }

    filtered.sort((a, b) => {
      let va, vb;
      switch (field) {
        case 'name':       va = a.name;                       vb = b.name;                       break;
        case 'trisWins':   va = a.stats.tris.wins    || 0;    vb = b.stats.tris.wins    || 0;    break;
        case 'damaWins':   va = a.stats.dama.wins    || 0;    vb = b.stats.dama.wins    || 0;    break;
        case 'reactionMs': va = a.stats.reaction.best_ms ?? Infinity; vb = b.stats.reaction.best_ms ?? Infinity; break;
        default:           va = 0; vb = 0;
      }
      if (va < vb) return sortAsc ? -1 :  1;
      if (va > vb) return sortAsc ?  1 : -1;
      return 0;
    });
    renderTable();
  }

  /* ── RENDER ──────────────────────────────────────────────────── */
  function renderTable() {
    const tbody = document.getElementById('user-table-body');
    if (!filtered.length) {
      tbody.innerHTML = `<tr><td colspan="10"><div class="empty-state">Nessun utente trovato.</div></td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(u => {
      const s = u.stats;
      const ms = s.reaction.best_ms != null ? `<span class="badge badge-ms">${s.reaction.best_ms} ms</span>` : '—';
      return `
        <tr>
          <td class="user-name">${esc(u.name)}</td>
          <td class="user-email">${esc(u.email)}</td>
          <td><span class="badge badge-win">${s.tris.wins}</span></td>
          <td><span class="badge badge-loss">${s.tris.losses}</span></td>
          <td><span class="badge badge-draw">${s.tris.draws}</span></td>
          <td><span class="badge badge-win">${s.dama.wins}</span></td>
          <td><span class="badge badge-loss">${s.dama.losses}</span></td>
          <td>${ms}</td>
          <td>${s.reaction.attempts}</td>
          <td>
            <div class="actions">
              <button class="btn-edit" onclick="openEdit('${u.id}')">Modifica</button>
              <button class="btn-ban"  onclick="openBan('${u.id}')">Banna</button>
            </div>
          </td>
        </tr>`;
    }).join('');
  }

  function esc(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ── EDIT MODAL ──────────────────────────────────────────────── */
  function openEdit(userId) {
    const u = allUsers.find(x => x.id === userId);
    if (!u) return;

    editUserId = userId;
    document.getElementById('edit-name').textContent = u.name;

    const s = u.stats;
    document.getElementById('tris-wins').value         = s.tris.wins      || 0;
    document.getElementById('tris-losses').value       = s.tris.losses    || 0;
    document.getElementById('tris-draws').value        = s.tris.draws     || 0;
    document.getElementById('dama-wins').value         = s.dama.wins      || 0;
    document.getElementById('dama-losses').value       = s.dama.losses    || 0;
    document.getElementById('reaction-ms').value       = s.reaction.best_ms ?? '';
    document.getElementById('reaction-attempts').value = s.reaction.attempts || 0;

    document.getElementById('edit-modal').classList.add('open');
  }

  function closeEdit() {
    document.getElementById('edit-modal').classList.remove('open');
    editUserId = null;
  }

  async function saveStats() {
    if (!editUserId) return;

    const body = {
      tris: {
        wins:   parseInt(document.getElementById('tris-wins').value)   || 0,
        losses: parseInt(document.getElementById('tris-losses').value) || 0,
        draws:  parseInt(document.getElementById('tris-draws').value)  || 0,
      },
      dama: {
        wins:   parseInt(document.getElementById('dama-wins').value)   || 0,
        losses: parseInt(document.getElementById('dama-losses').value) || 0,
      },
      reaction: {
        best_ms:  document.getElementById('reaction-ms').value !== '' ? parseInt(document.getElementById('reaction-ms').value) : null,
        attempts: parseInt(document.getElementById('reaction-attempts').value) || 0,
      },
    };

    try {
      const res = await fetch(`/api/admin/users/${editUserId}/stats`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message || 'Statistiche aggiornate.', 'success');
        closeEdit();
        loadUsers();
      } else {
        showToast(data.error || 'Errore.', 'error');
      }
    } catch {
      showToast('Errore di rete.', 'error');
    }
  }

  /* ── BAN MODAL ───────────────────────────────────────────────── */
  function openBan(userId) {
    const u = allUsers.find(x => x.id === userId);
    if (!u) return;

    banUserId = userId;
    document.getElementById('ban-name').textContent = `${u.name} (${u.email})`;
    document.getElementById('ban-modal').classList.add('open');
  }

  function closeBan() {
    document.getElementById('ban-modal').classList.remove('open');
    banUserId = null;
  }

  async function confirmBan() {
    if (!banUserId) return;

    try {
      const res  = await fetch(`/api/admin/users/${banUserId}/ban`, { method: 'DELETE' });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message || 'Utente bannato.', 'success');
        closeBan();
        loadUsers();
      } else {
        showToast(data.error || 'Errore.', 'error');
      }
    } catch {
      showToast('Errore di rete.', 'error');
    }
  }

  /* ── LOGOUT ──────────────────────────────────────────────────── */
  async function logout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/login';
  }

  /* ── TOAST ───────────────────────────────────────────────────── */
  function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(() => el.remove(), 3500);
  }

  /* ── CLOSE MODALS ON BACKDROP CLICK ─────────────────────────── */
  document.getElementById('edit-modal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeEdit();
  });
  document.getElementById('ban-modal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeBan();
  });