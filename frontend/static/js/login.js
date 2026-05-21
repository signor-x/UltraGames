const btn = document.getElementById('btn-login');
    const alertBox = document.getElementById('alert');

    function showAlert(msg, type) {
      alertBox.textContent = msg;
      alertBox.className = `alert ${type} show`;
    }

    function setLoading(on) {
      btn.classList.toggle('loading', on);
      btn.disabled = on;
    }

    btn.addEventListener('click', async () => {
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;

      if (!email || !password) { showAlert('Compila tutti i campi.', 'error'); return; }

      setLoading(true);
      alertBox.className = 'alert';

      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        if (res.ok) {
          showAlert('Accesso riuscito. Reindirizzamento…', 'success');
          setTimeout(() => window.location.href = '/home', 600);
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