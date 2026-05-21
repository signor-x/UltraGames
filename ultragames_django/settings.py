"""
Settings Django per il progetto UltraGames.

PATTERN DI CONFIGURAZIONE: Variabili d'ambiente tramite python-dotenv.
  Tutti i valori sensibili (SECRET_KEY, DB_PASSWORD, ADMIN_EMAIL) sono letti
  da variabili d'ambiente, mai hardcoded nel codice sorgente.
  In produzione: impostare le variabili nel sistema operativo o in un .env file.

CONFIGURAZIONI PRINCIPALI:

  1. SECURITY:
     SECRET_KEY         → Chiave HMAC per firma JWT e sessioni Django
     DEBUG              → False in produzione (nasconde stack trace)
     ALLOWED_HOSTS      → Lista di host validi (prevenzione HTTP Host header attack)

  2. INSTALLED_APPS:
     Le app Django installate. Non include i moduli di gioco (dama, tris, reaction_test)
     perché non usano modelli Django ORM né admin Django.
     Include solo le app con views/urls registrate nel router principale.

  3. MIDDLEWARE:
     Ordine critico — Django processa i middleware in questo ordine per ogni richiesta:
       SecurityMiddleware        → HTTPS redirect, header sicurezza
       SessionMiddleware         → Sessioni Django (usate da admin Django, non da JWT)
       CommonMiddleware          → APPEND_SLASH, normalize URL
       CsrfViewMiddleware        → Protezione CSRF (bypassata da @csrf_exempt nelle view)
       AuthenticationMiddleware  → Autenticazione Django (non usata, JWT la sostituisce)
       MessageMiddleware         → Flash messages Django
       XFrameOptionsMiddleware   → Header X-Frame-Options (anti-clickjacking)
       JwtAuthMiddleware         → CUSTOM: Inietta request.current_user dal cookie JWT
         ↑ POSIZIONE: Dopo i middleware Django standard, prima delle view.
         ↑ DEVE essere in questa lista per essere eseguito ad ogni richiesta.

  4. DATABASE:
     Driver: python-mariadb (accesso diretto, NO Django ORM)
     DATABASES["default"] è definito solo per compatibilità con alcuni strumenti Django.
     Le query reali avvengono in InDatabaseUserRepository e InDatabaseStatsRepository.

  5. JWT SETTINGS:
     JWT_EXPIRY_MINUTES: Durata di validità del token JWT in minuti.
       Letto da: JwtTokenService.generate() (per exp claim)
       Usato da: LoginView.post() (per max_age del cookie)

  6. ADMIN:
     ADMIN_EMAIL: Email dell'unico amministratore del sistema.
       Confrontata da: @cbv_require_admin in auth_helpers.py
       NON è un campo nel DB: l'admin è identificato solo dall'email nel JWT.

SOLID PRINCIPLES:
  - SRP: settings.py è il punto centrale di configurazione. Nessuna configurazione
    è sparsa nei singoli file (es. no SECRET_KEY hardcoded in jwt_token_service.py).
  - OCP: Aggiungere una nuova app richiede solo aggiungere una riga a INSTALLED_APPS
    e al router urls.py, senza modificare settings.py in modo invasivo.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carica variabili d'ambiente dal file .env nella root del progetto
load_dotenv()

# ── PATH ─────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

# ── SECURITY ─────────────────────────────────────────────────────────────────

# SECRET_KEY: Usata per firma JWT (JwtTokenService) e per alcune feature Django.
# In produzione: stringa casuale di almeno 50 caratteri.
# MAI committare il valore reale nel repository.
SECRET_KEY = os.environ.get("SECRET_KEY", "pizza-al-forno-1234567890")

# DEBUG: In produzione deve essere False (non mostrare stack trace agli utenti)
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

# ALLOWED_HOSTS: Prevenzione HTTP Host header spoofing.
# In produzione: ["yourdomain.com", "www.yourdomain.com"]
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

# ── APPLICAZIONI INSTALLATE ───────────────────────────────────────────────────

INSTALLED_APPS = [
    # App Django standard (alcune non usate attivamente ma richieste dal framework)
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    # App del progetto UltraGames
    "apps.auth_app",
    "apps.account",
    "apps.stats",
    "apps.admin_panel",
    "apps.games",
]

# ── MIDDLEWARE ────────────────────────────────────────────────────────────────

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",       # Bypassato da @csrf_exempt nelle view
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # CUSTOM: Middleware JWT - Inietta request.current_user da cookie "access_token"
    # Deve essere DOPO i middleware Django standard per avere accesso a request.COOKIES
    "middleware.jwt_middleware.JwtAuthMiddleware",
]

# ── URL ROOT ──────────────────────────────────────────────────────────────────

ROOT_URLCONF = "ultragames_django.urls"   # → ultragames_django/urls.py

# ── DATABASE (MariaDB via python-mariadb) ─────────────────────────────────────

# NOTA: L'ORM Django NON è usato per le tabelle utenti/statistiche.
# Queste credenziali sono lette direttamente da InDatabaseUserRepository
# e InDatabaseStatsRepository tramite _get_connection().
DATABASES = {
    "default": {
        "ENGINE":   "django.db.backends.dummy",  # Dummy: nessuna migrazione Django
        "NAME":     os.environ.get("DB_NAME",     "bernasconil"),
        "USER":     os.environ.get("DB_USER",     "studente-bernasconil"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "bernasconil"),
        "HOST":     os.environ.get("DB_HOST",     "dbmagistri.ddns.net"),
        "PORT":     os.environ.get("DB_PORT",     "3309"),
    }
}

# ── INTERNAZIONALIZZAZIONE ────────────────────────────────────────────────────

# ── STATIC FILES ─────────────────────────────────────────────────────────────

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "frontend" / "static"]

# ── INTERNAZIONALIZZAZIONE ────────────────────────────────────────────────────

LANGUAGE_CODE = "it-it"
TIME_ZONE     = "Europe/Rome"
USE_I18N      = True
USE_TZ        = True

# ── JWT ───────────────────────────────────────────────────────────────────────

# Durata di validità del JWT in minuti.
# JwtTokenService.generate() lo usa per il claim "exp".
# LoginView.post() lo usa per max_age del cookie Set-Cookie.
JWT_EXPIRY_MINUTES = int(os.environ.get("JWT_EXPIRY_MINUTES", "60"))

# ── ADMIN ─────────────────────────────────────────────────────────────────────

# Email dell'amministratore del sistema.
# @cbv_require_admin in auth_helpers.py confronta request.current_user.email
# con questo valore. Non è un campo nel DB.
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@ultragames.local").lower()

