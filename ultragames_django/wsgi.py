"""
WSGI — Entry point per server web di produzione (Gunicorn, uWSGI, Daphne).

COS'È WSGI (Web Server Gateway Interface):
  WSGI è lo standard Python (PEP 3333) che definisce come un server web
  comunica con un'applicazione Python. È un'interfaccia chiamabile:
    response = application(environ, start_response)

  Il server web (es. Gunicorn) riceve la richiesta HTTP, la converte in
  un dizionario `environ` (metodo, path, headers, body, etc.) e chiama
  `application`. Django elabora la richiesta e restituisce la risposta.

PERCORSO DI UNA RICHIESTA IN PRODUZIONE:
  Client (browser)
    → Nginx / Load Balancer (terminazione SSL, proxy)
    → Gunicorn (server WSGI, gestisce worker processes)
    → application() [questo file]
    → Django middleware chain  [settings.MIDDLEWARE]
      → JwtAuthMiddleware      [middleware/jwt_middleware.py]
        → URL router           [ultragames_django/urls.py]
          → View CBV           [apps/*/views/*.py]
            → JsonResponse     → risposta HTTP
    ← Gunicorn assembla la risposta HTTP
  ← Nginx invia al client

DIFFERENZA CON manage.py runserver:
  manage.py runserver: Server di sviluppo Django (single-threaded, no SSL,
    non adatto a produzione).
  wsgi.py + Gunicorn: Server di produzione (multi-process/multi-thread,
    supporta SSL, alte prestazioni).

VARIABILE DJANGO_SETTINGS_MODULE:
  Imposta il file di configurazione Django da usare.
  "ultragames_django.settings" → ultragames_django/settings.py
  Può essere sovrascritta per usare settings diversi (es. testing):
    DJANGO_SETTINGS_MODULE=ultragames_django.settings_test gunicorn wsgi:application

SOLID PRINCIPLES:
  - SRP: Questo file ha una sola responsabilità: esporre l'oggetto
    `application` che Gunicorn usa come entry point.
"""

import os
from django.core.wsgi import get_wsgi_application

# Imposta il modulo di settings di Django come variabile d'ambiente.
# os.environ.setdefault: imposta solo se non già definita (permette override esterno).
# Utile per ambienti Docker/K8s che impostano la variabile prima di avviare il processo.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ultragames_django.settings")

# get_wsgi_application():
#   1. Legge DJANGO_SETTINGS_MODULE e carica la configurazione (settings.py)
#   2. Inizializza Django: INSTALLED_APPS, MIDDLEWARE, database, etc.
#   3. Costruisce e restituisce un oggetto callable WSGI
#
# `application`: Il nome convenzionale atteso da Gunicorn.
# Gunicorn viene avviato con: gunicorn ultragames_django.wsgi:application
# Questo dice a Gunicorn di importare il modulo "ultragames_django.wsgi"
# e usare l'attributo "application" come entry point WSGI.
application = get_wsgi_application()
