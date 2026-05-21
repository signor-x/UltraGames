const btn = document.getElementById('btn-register');
    const alertBox = document.getElementById('alert');
    const pwdInput = document.getElementById('password');
    const fill = document.getElementById('strength-fill');
    const label = document.getElementById('strength-label');

    pwdInput.addEventListener('input', () => {
      const v = pwdInput.value;
      let score = 0;
      if (v.length >= 8) score++;
      if (v.length >= 12) score++;
      if (/[A-Z]/.test(v)) score++;
      if (/[0-9]/.test(v)) score++;
      if (/[^A-Za-z0-9]/.test(v)) score++;

      const levels = [
        { pct: '0%', color: 'transparent', text: '// Forza password' },
        { pct: '25%', color: '#ff3333', text: '// Molto debole' },
        { pct: '50%', color: '#ff8800', text: '// Debole' },
        { pct: '75%', color: '#ffcc00', text: '// Discreta' },
        { pct: '90%', color: '#88ff00', text: '// Buona' },
        { pct: '100%', color: '#00ff00', text: '// Ottima' },
      ];

      const lvl = levels[Math.min(score, 5)];
      fill.style.width = lvl.pct;
      fill.style.background = lvl.color;
      label.textContent = lvl.text;
      label.style.color = lvl.color === 'transparent' ? 'var(--text-muted)' : lvl.color;
    });

    function showAlert(msg, type) {
      alertBox.textContent = msg;
      alertBox.className = `alert ${type} show`;
    }

    function setLoading(on) {
      btn.classList.toggle('loading', on);
      btn.disabled = on;
    }

    btn.addEventListener('click', async () => {
      const name = document.getElementById('name').value.trim();
      const email = document.getElementById('email').value.trim();
      const password = pwdInput.value;

      if (!name || !email || !password) {
        showAlert('Compila tutti i campi.', 'error');
        return;
      }

      setLoading(true);
      alertBox.className = 'alert';

      try {
        const res = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, password }),
        });
        const data = await res.json();
        if (res.ok) {
          showAlert('Account creato! Reindirizzamento al login…', 'success');
          setTimeout(() => window.location.href = '/login', 1200);
        } else {
          showAlert(data.error || 'Errore sconosciuto.', 'error');
          setLoading(false);
        }
      } catch {
        showAlert('Errore di rete. Riprova più tardi.', 'error');
        setLoading(false);
      }
    });

    document.addEventListener('keydown', e => { if (e.key === 'Enter') btn.click(); });