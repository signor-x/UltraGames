"""
TemplateReaderMixin — Mixin per la lettura sicura di template HTML e asset statici.

RESPONSABILITÀ (SRP):
  Fornisce SOLO i metodi helper per leggere file dal filesystem:
    _read_template(name) → legge HTML da frontend/templates/
    _read_static(sub, f) → legge CSS/JS da frontend/static/<sub>/

  NON gestisce la risposta HTTP (→ view), NON esegue autenticazione (→ decorator).

PATTERN MIXIN (ereditarietà multipla):
  Progettato per essere combinato con django.views.View nelle page view:
    class HomePageView(TemplateReaderMixin, View):
        def get(self, request):
            return HttpResponse(self._read_template("home.html"))

  MRO (Method Resolution Order):
    HomePageView → TemplateReaderMixin → View → object

SICUREZZA — PATH TRAVERSAL PREVENTION:
  Entrambi i metodi eseguono una verifica che il path risolto resti
  all'interno della directory consentita (startswith del path assoluto).
  Questo impedisce attacchi del tipo:
    GET /script/../../../etc/passwd
    → path = frontend/static/js/../../../etc/passwd
    → path.resolve() = /etc/passwd  ← NON inizia con _STATIC_DIR → 404

  Path.resolve() restituisce il path assoluto canonico (risolve .., symlink, etc.).
  Il confronto str(path).startswith(str(_safe_root)) è la guardia di sicurezza.

DJANGO TEMPLATE ENGINE:
  Questo progetto NON usa il template engine di Django (django.template).
  I file HTML sono letti e restituiti come stringhe grezze (raw HTML).
  Il JavaScript nel browser gestisce il rendering dinamico (SPA-like).
  Vantaggio: Zero dipendenza dal sistema di template Django; HTML è un file statico.

SOLID PRINCIPLES:
  - SRP: Solo lettura sicura di file. Nessuna logica di business o HTTP.
  - DRY: Il codice di lettura con path-traversal check è scritto una sola volta
    e riutilizzato da tutte le page view (LoginPageView, HomePageView, etc.).
  - OCP: Per aggiungere altri tipi di asset (es. immagini) si aggiunge
    un metodo senza modificare quelli esistenti.

PERCORSO CHIAMATA:
  apps/pages/views/login_page_view.py
    → LoginPageView._read_template("login.html")  ← questo mixin
  apps/pages/views/serve_script_view.py
    → ServeScriptView._read_static("js", file)    ← questo mixin
  apps/pages/views/serve_style_view.py
    → ServeStyleView._read_static("css", file)    ← questo mixin

STRUTTURA FILE ATTESA:
  BASE_DIR/
    frontend/
      templates/
        login.html
        register.html
        home.html
        admin.html
      static/
        js/
          *.js
        css/
          *.css
"""

from pathlib import Path

from django.conf import settings
from django.http import Http404

# ── Percorsi base per i file serviti ──────────────────────────────────────────

# BASE_DIR: Radice del progetto (directory contenente manage.py), letto da settings.py
_BASE = Path(settings.BASE_DIR)

# _TEMPLATE_DIR: Directory da cui vengono letti i template HTML.
# Tutti i file HTML del frontend vivono qui.
_TEMPLATE_DIR = _BASE / "frontend" / "templates"

# _STATIC_DIR: Directory da cui vengono serviti i file statici (CSS, JS).
# Organizzata in sottocartelle per tipo: static/css/, static/js/
_STATIC_DIR = _BASE / "frontend" / "static"

# ── Mappa estensione → MIME type ──────────────────────────────────────────────
# Usata da ServeScriptView e ServeStyleView per impostare Content-Type corretto.
# charset=utf-8 è buona prassi per evitare problemi di encoding nei browser.
_MIME = {
    ".css": "text/css; charset=utf-8",
    ".js":  "application/javascript; charset=utf-8",
}


class TemplateReaderMixin:
    """
    Mixin che fornisce lettura sicura di template HTML e asset statici.

    UTILIZZO:
      class MyPageView(TemplateReaderMixin, View):
          def get(self, request):
              html = self._read_template("mypage.html")
              return HttpResponse(html, content_type="text/html")

    SICUREZZA (PATH TRAVERSAL):
      Ogni metodo risolve il path assoluto e verifica che rimanga
      all'interno della directory consentita prima di leggere il file.
    """

    def _read_template(self, name: str) -> str:
        """
        Legge e restituisce il contenuto di un file HTML dalla cartella templates.

        FLUSSO:
          1. Costruisce il path: _TEMPLATE_DIR / name
          2. Risolve il path assoluto (elimina .. e symlink)
          3. Verifica che il path risolto inizi con _TEMPLATE_DIR.resolve()
             → Se no: 404 (path traversal attempt)
          4. Apre il file in encoding UTF-8 e restituisce il contenuto

        SICUREZZA:
          path.resolve() + startswith(): Previene path traversal.
          Esempio malevolo:
            name = "../../etc/passwd"
            path = _TEMPLATE_DIR / "../../etc/passwd"
            path.resolve() = "/etc/passwd"
            startswith(_TEMPLATE_DIR.resolve()) → False → Http404

        CHIAMATO DA:
          LoginPageView.get()     → _read_template("login.html")
          RegisterPageView.get()  → _read_template("register.html")
          HomePageView.get()      → _read_template("home.html")
          AdminPageView.get()     → _read_template("admin.html")

        :param name: Nome del file HTML (es. "home.html"), senza path traversal
        :return: Contenuto del file HTML come stringa UTF-8
        :raises Http404: Se il file non esiste o il path è fuori dalla directory
        """
        path = (_TEMPLATE_DIR / name).resolve()

        # GUARDIA SICUREZZA: verifica che il path risolto sia dentro _TEMPLATE_DIR
        if not str(path).startswith(str(_TEMPLATE_DIR.resolve())):
            raise Http404  # Path traversal attempt → 404

        with open(path, encoding="utf-8") as f:
            return f.read()

    def _read_static(self, subfolder: str, filename: str) -> bytes | None:
        """
        Legge e restituisce il contenuto di un asset statico (CSS o JS).

        FLUSSO:
          1. Costruisce il path: _STATIC_DIR / subfolder / filename
          2. Risolve il path della sottodirectory (es. _STATIC_DIR / "js")
          3. Risolve il path completo del file
          4. Verifica path traversal (path deve iniziare con static_subdir)
          5. Verifica che il file esista
          6. Legge e restituisce il contenuto come bytes

        SICUREZZA:
          Il check avviene sulla sottodirectory specifica (es. static/js/),
          non sulla directory statica generale. Questo impedisce di accedere
          a file di un'altra sottocartella (es. /script/../css/file.css).

        CHIAMATO DA:
          ServeScriptView.get() → _read_static("js", file)
          ServeStyleView.get()  → _read_static("css", file)

        :param subfolder: "js" o "css" (sottodirectory di static/)
        :param filename: Nome del file (es. "app.js"), dalla URL Django <str:file>
        :return: Contenuto del file come bytes, o None se non trovato/non sicuro
        """
        static_subdir = (_STATIC_DIR / subfolder).resolve()  # Es: .../frontend/static/js
        path          = (static_subdir / filename).resolve()  # Es: .../frontend/static/js/app.js

        # GUARDIA SICUREZZA: path deve essere dentro la sottodirectory specifica
        if not str(path).startswith(str(static_subdir)):
            return None  # Path traversal attempt → None → 404 nella view

        # Verifica esistenza del file prima di leggerlo
        if not path.is_file():
            return None

        return path.read_bytes()
