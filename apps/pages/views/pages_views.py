"""
pages_views.py — Gestore unificato delle view per il serving delle pagine HTML e asset statici.

STRUTTURA DEL FILE:
  PagesView → classe gestore con i metodi HTTP dell'area frontend:
                root()            GET /              → redirect a /login
                login_page()      GET /login         → serve login.html
                register_page()   GET /register      → serve register.html
                home_page()       GET /home          → serve home.html (richiede auth)
                admin_page()      GET /admin         → serve admin.html (richiede auth + admin)
                serve_script()    GET /script/<file> → serve JS da frontend/static/js/
                serve_style()     GET /style/<file>  → serve CSS da frontend/static/css/

ARCHITETTURA SPA (Single Page Application):
  Django serve l'HTML grezzo dal filesystem (NON usa il template engine Django).
  I file HTML sono statici: il JavaScript nel browser gestisce il rendering
  dinamico chiamando le API REST (auth, games, stats).
  Vantaggio: Separazione netta tra backend (API JSON) e frontend (HTML+JS).

SICUREZZA — PATH TRAVERSAL PREVENTION (TemplateReaderMixin):
  _read_template() e _read_static() verificano che il path risolto resti
  all'interno della directory consentita prima di leggere il file.
  Path.resolve() + startswith() impediscono attacchi tipo GET /script/../../../etc/passwd.

PERCORSO CHIAMATA (URL → metodo):
  ultragames_django/urls.py
    → include("apps.pages.urls")    [apps/pages/urls.py]
      → PagesView.root()           GET /
      → PagesView.login_page()     GET /login
      → PagesView.register_page()  GET /register
      → PagesView.home_page()      GET /home
      → PagesView.admin_page()     GET /admin
      → PagesView.serve_script()   GET /script/<file>
      → PagesView.serve_style()    GET /style/<file>

SOLID PRINCIPLES:
  - SRP: Ogni metodo serve un singolo tipo di risorsa.
  - DRY: La logica di lettura sicura è centralizzata in TemplateReaderMixin.
  - OCP: Nuova pagina = nuovo metodo, senza modificare gli altri.
"""

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.views import View
from apps.core.action_view import ActionView

from services.auth_helpers import cbv_require_auth
from .template_reader_mixin import TemplateReaderMixin, _MIME


class PagesView(TemplateReaderMixin, ActionView, View):
    """
    Gestore unificato delle view per il serving del frontend.

    Eredita TemplateReaderMixin per la lettura sicura di template HTML
    e asset statici (CSS, JS) con protezione da path traversal.

    ENDPOINT GESTITI:
      GET /              → root()           (redirect a /login, no auth)
      GET /login         → login_page()     (serve login.html, no auth)
      GET /register      → register_page()  (serve register.html, no auth)
      GET /home          → home_page()      (serve home.html, richiede JWT)
      GET /admin         → admin_page()     (serve admin.html, richiede JWT + admin)
      GET /script/<file> → serve_script()   (serve JS, no auth)
      GET /style/<file>  → serve_style()    (serve CSS, no auth)

    MRO (Method Resolution Order):
      PagesView → TemplateReaderMixin → View → object
    """

    # ── root ──────────────────────────────────────────────────────────────────

    def root(self, request):
        """
        Reindirizza GET / → GET /login (HTTP 302).

        ENDPOINT: GET /
        AUTENTICAZIONE: Non richiesta (redirect pubblico e incondizionato).
        RISPOSTA (302 Found): Location: /login

        PATTERN: Redirect 302 (temporaneo) — se la destinazione cambia in futuro
        (es. /home per utenti già loggati), si modifica solo questo metodo.
        """
        self.allowed_methods = ["GET"]
        return HttpResponseRedirect("/login")

    # ── login_page ────────────────────────────────────────────────────────────

    def login_page(self, request):
        """
        Serve il file HTML della pagina di login.

        ENDPOINT: GET /login
        AUTENTICAZIONE: Non richiesta (pagina pubblica).
        RISPOSTA (200): Content-Type: text/html, Body: login.html

        FLUSSO UTENTE:
          1. Browser richiede GET /login → Django serve login.html
          2. JS nel browser mostra il form
          3. Utente invia credenziali → POST /api/auth/login [AuthView.login]
          4. Se successo: cookie JWT + redirect a /home
        """
        self.allowed_methods = ["GET"]
        return HttpResponse(self._read_template("login.html"), content_type="text/html")

    # ── register_page ─────────────────────────────────────────────────────────

    def register_page(self, request):
        """
        Serve il file HTML della pagina di registrazione.

        ENDPOINT: GET /register
        AUTENTICAZIONE: Non richiesta (pagina pubblica).
        RISPOSTA (200): Content-Type: text/html, Body: register.html

        FLUSSO UTENTE:
          1. Browser richiede GET /register → Django serve register.html
          2. Utente compila il form e invia → POST /api/auth/register [AuthView.register]
          3. Se successo: redirect a /login per effettuare il login
        """
        self.allowed_methods = ["GET"]
        return HttpResponse(self._read_template("register.html"), content_type="text/html")

    # ── home_page ─────────────────────────────────────────────────────────────

    @cbv_require_auth
    def home_page(self, request):
        """
        Serve la home page HTML agli utenti autenticati.

        ENDPOINT: GET /home
        AUTENTICAZIONE: Richiesta (@cbv_require_auth → JWT valido nel cookie).
        RISPOSTA SUCCESSO (200): Content-Type: text/html, Body: home.html
        RISPOSTA ERRORE (401): {"error": "Non autenticato."}

        FLUSSO UTENTE:
          1. Browser richiede GET /home (con cookie access_token)
          2. JwtAuthMiddleware decodifica il JWT → request.current_user
          3. @cbv_require_auth verifica che current_user non sia None
          4. Django serve home.html (statico)
          5. JS nel browser chiama GET /api/auth/me per popolare la pagina
        self.allowed_methods = ["GET"]
        """
        return HttpResponse(self._read_template("home.html"), content_type="text/html")

    # ── admin_page ────────────────────────────────────────────────────────────

    @cbv_require_auth
    def admin_page(self, request):
        """
        Serve la pagina HTML del pannello admin agli utenti amministratori.
        Reindirizza silenziosamente i non-admin a /home.

        ENDPOINT: GET /admin
        AUTENTICAZIONE: Richiesta (@cbv_require_auth).
        AUTORIZZAZIONE: Solo utenti con email == settings.ADMIN_EMAIL.

        RISPOSTA SUCCESSO (200): Content-Type: text/html, Body: admin.html
        RISPOSTA NON ADMIN (302): Location: /home (redirect silenzioso)
        RISPOSTA NON AUTENTICATO (401): {"error": "Non autenticato."}

        NOTA SU REDIRECT vs 403:
          Usa redirect 302 anziché @cbv_require_admin che restituirebbe 403 JSON.
          Il redirect è più user-friendly per una pagina HTML: l'utente viene
          silenziosamente reindirizzato invece di ricevere un errore.
          Evita anche di rivelare l'esistenza del pannello admin.

        VERIFICA ADMIN:
          .lower() su entrambi garantisce confronto case-insensitive.
        self.allowed_methods = ["GET"]
        """
        if request.current_user.email.lower() != settings.ADMIN_EMAIL.lower():
            return HttpResponseRedirect("/home")
        return HttpResponse(self._read_template("admin.html"), content_type="text/html")

    # ── serve_script ──────────────────────────────────────────────────────────

    def serve_script(self, request, file: str):
        """
        Serve i file JavaScript da frontend/static/js/.

        ENDPOINT: GET /script/<file>
          file: nome del file JS (es. "home-tris.js")
        AUTENTICAZIONE: Non richiesta (gli script sono pubblici).

        RISPOSTA SUCCESSO (200):
          Content-Type: application/javascript; charset=utf-8
          Body: contenuto binario del file JS

        RISPOSTA ERRORE (404): File non trovato o path traversal tentato.

        SICUREZZA:
          _read_static("js", file) verifica che il path risolto resti
          dentro frontend/static/js/ prima di leggere il file.
        self.allowed_methods = ["GET"]
        """
        content = self._read_static("js", file)
        if content is None:
            raise Http404
        return HttpResponse(content, content_type=_MIME.get(".js", "application/javascript"))

    # ── serve_style ───────────────────────────────────────────────────────────

    def serve_style(self, request, file: str):
        """
        Serve i file CSS da frontend/static/css/.

        ENDPOINT: GET /style/<file>
          file: nome del file CSS (es. "home.css")
        AUTENTICAZIONE: Non richiesta (i CSS sono pubblici).

        RISPOSTA SUCCESSO (200):
          Content-Type: text/css; charset=utf-8
          Body: contenuto binario del file CSS

        RISPOSTA ERRORE (404): File non trovato o path traversal tentato.

        SICUREZZA:
          _read_static("css", file) verifica che il path risolto resti
          dentro frontend/static/css/ prima di leggere il file.
        self.allowed_methods = ["GET"]
        """
        content = self._read_static("css", file)
        if content is None:
            raise Http404
        return HttpResponse(content, content_type=_MIME.get(".css", "text/css"))
