"""
Package ultragames_django — Configurazione Django del progetto UltraGames.

CONTENUTO:
  settings.py → Configurazione Django: MIDDLEWARE, DATABASES, JWT, ADMIN_EMAIL
  urls.py     → Router principale: include tutte le app e i giochi
  wsgi.py     → Entry point WSGI per server di produzione (Gunicorn/uWSGI)

FLUSSO DI AVVIO DJANGO:
  1. manage.py / wsgi.py: os.environ["DJANGO_SETTINGS_MODULE"] = "ultragames_django.settings"
  2. Django carica settings.py (INSTALLED_APPS, MIDDLEWARE, ROOT_URLCONF)
  3. Django costruisce la catena di middleware (incluso JwtAuthMiddleware)
  4. Django carica il router da ROOT_URLCONF = "ultragames_django.urls"
  5. Per ogni richiesta: middleware chain → router → view → response
"""
