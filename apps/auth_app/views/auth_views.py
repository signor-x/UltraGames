"""
auth_views.py — Gestore unificato delle view per l'autenticazione.

STRUTTURA DEL FILE:
  AuthView → classe gestore con i metodi HTTP dell'area autenticazione:
               register() POST /api/auth/register
               login()    POST /api/auth/login
               logout()   POST /api/auth/logout
               me()       GET  /api/auth/me

PERCORSO CHIAMATA (URL → metodo):
  ultragames_django/urls.py
    → include("apps.auth_app.urls")    [apps/auth_app/urls.py]
      → AuthView.register()  POST /api/auth/register
      → AuthView.login()     POST /api/auth/login
      → AuthView.logout()    POST /api/auth/logout
      → AuthView.me()        GET  /api/auth/me

SOLID PRINCIPLES:
  - SRP: Ogni metodo gestisce un solo endpoint; la logica è in AuthService.
  - DIP: Usa get_container() per ottenere AuthService iniettato.
  - OCP: Nuovo endpoint auth = nuovo metodo, senza modificare gli altri.
"""

import json

from django.conf import settings
from django.http import JsonResponse
from django.views import View
from apps.core.action_view import ActionView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from services.container import get_container
from services.auth_helpers import cbv_require_auth


@method_decorator(csrf_exempt, name="dispatch")
class AuthView(ActionView, View):
    """
    Gestore unificato delle view per l'autenticazione.

    Raccoglie in un'unica classe tutti gli endpoint di autenticazione,
    condividendo le dipendenze (get_container, cbv_require_auth) senza duplicazioni.

    ENDPOINT GESTITI:
      POST /api/auth/register → register()  (crea nuovo account, no auth)
      POST /api/auth/login    → login()     (autentica + cookie JWT, no auth)
      POST /api/auth/logout   → logout()    (cancella cookie JWT, no auth)
      GET  /api/auth/me       → me()        (dati utente dal JWT, richiede auth)

    NOTA CSRF:
      @method_decorator(csrf_exempt, name="dispatch") disabilita il CSRF per
      tutti i metodi. Necessario per register, login, logout (utente non ancora
      autenticato, privo di sessione Django). La protezione è garantita dal JWT
      HttpOnly + SameSite=Lax per gli endpoint che lo richiedono.
    """

    # ── register ──────────────────────────────────────────────────────────────

    def register(self, request):
        """
        Registra un nuovo utente nel sistema.

        ENDPOINT: POST /api/auth/register
        BODY JSON: {"email": "user@example.com", "password": "password123", "name": "Mario"}
        AUTENTICAZIONE: Non richiesta (endpoint pubblico).

        RISPOSTA SUCCESSO (201 Created):
          {"message": "Registrazione completata.", "user_id": "<UUID>"}

        RISPOSTA ERRORI (400):
          {"error": "JSON non valido."}
          {"error": "Il nome è obbligatorio."}
          {"error": "Indirizzo email non valido."}
          {"error": "La password deve contenere almeno 8 caratteri."}
          {"error": "Un account con questa email esiste già."}

        PERCORSO:
          → get_container().auth_service.register(email, password, name)
            [services/auth_service.py]
              → AuthService._validate_registration()
              → user_repository.exists_by_email()
              → bcrypt.hashpw()
              → user_repository.create(User)
        """
        self.allowed_methods = ["POST"]
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "JSON non valido."}, status=400)

        result = get_container().auth_service.register(
            email=body.get("email", ""),
            password=body.get("password", ""),
            name=body.get("name", ""),
        )
        if not result.success:
            return JsonResponse({"error": result.error}, status=400)

        return JsonResponse(
            {"message": "Registrazione completata.", "user_id": result.user_id},
            status=201,
        )

    # ── login ─────────────────────────────────────────────────────────────────

    def login(self, request):
        """
        Autentica un utente e imposta il cookie JWT.

        ENDPOINT: POST /api/auth/login
        BODY JSON: {"email": "user@example.com", "password": "password123"}
        AUTENTICAZIONE: Non richiesta (endpoint pubblico).

        RISPOSTA SUCCESSO (200):
          {"message": "Login effettuato."}
          Header: Set-Cookie: access_token=<JWT>; HttpOnly; SameSite=Lax; Max-Age=3600

        RISPOSTA ERRORE (400):
          {"error": "JSON non valido."}

        RISPOSTA ERRORE (401):
          {"error": "Credenziali non valide."}

        SICUREZZA COOKIE:
          httponly=True  → Non accessibile da JS (prevenzione XSS)
          samesite="Lax" → Solo per navigazioni same-site (prevenzione CSRF)
          max_age        → JWT_EXPIRY_MINUTES * 60 (cookie scade con il token)

        PERCORSO:
          → get_container().auth_service.login(email, password)
            [services/auth_service.py]
              → user_repository.find_by_email()
              → bcrypt.checkpw()
              → token_service.generate(TokenPayload)
          → response.set_cookie("access_token", token, httponly=True)
        """
        self.allowed_methods = ["POST"]
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "JSON non valido."}, status=400)

        result = get_container().auth_service.login(
            email=body.get("email", ""),
            password=body.get("password", ""),
        )
        if not result.success:
            return JsonResponse({"error": result.error}, status=401)

        response = JsonResponse({"message": "Login effettuato."})
        response.set_cookie(
            "access_token",
            result.token,
            httponly=True,
            samesite="Lax",
            max_age=settings.JWT_EXPIRY_MINUTES * 60,
        )
        return response

    # ── logout ────────────────────────────────────────────────────────────────

    def logout(self, request):
        """
        Effettua il logout cancellando il cookie JWT.

        ENDPOINT: POST /api/auth/logout
        BODY: (vuoto, non richiesto)
        AUTENTICAZIONE: Non richiesta (il cookie viene solo eliminato).

        RISPOSTA (200):
          {"message": "Logout effettuato."}
          Header: Set-Cookie: access_token=; expires=...; Max-Age=0

        STRATEGIA DI LOGOUT:
          Il JWT è stateless: non esiste una blacklist lato server.
          L'unico modo per invalidare un token lato client è eliminare il cookie.
          Dopo il logout, JwtAuthMiddleware non troverà il cookie e imposterà
          request.current_user = None → qualsiasi endpoint @cbv_require_auth darà 401.

        PERCORSO:
          → response.delete_cookie("access_token")
            Django imposta Max-Age=0 + data di scadenza nel passato → browser elimina il cookie.
        """
        self.allowed_methods = ["POST"]
        response = JsonResponse({"message": "Logout effettuato."})
        response.delete_cookie("access_token")
        return response

    # ── me ────────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def me(self, request):
        """
        Restituisce i dati dell'utente autenticato dal payload JWT.

        ENDPOINT: GET /api/auth/me
        AUTENTICAZIONE: Richiesta (@cbv_require_auth → JWT valido nel cookie).

        RISPOSTA SUCCESSO (200):
          {"id": "<UUID>", "email": "user@example.com", "name": "Mario"}

        RISPOSTA ERRORE (401):
          {"error": "Non autenticato."}

        NOTA PRESTAZIONI:
          Zero query al database. I dati provengono dal TokenPayload già
          decodificato da JwtAuthMiddleware: è la chiamata più leggera dell'API.

        FLUSSO (eseguito prima del metodo):
          1. JwtAuthMiddleware ha estratto il token dal cookie "access_token"
          2. JwtTokenService.verify(token) ha decodificato il TokenPayload
          3. request.current_user = TokenPayload(user_id, email, name)
          4. @cbv_require_auth ha verificato che current_user non sia None
        """
        self.allowed_methods = ["GET"]
        u = request.current_user
        return JsonResponse({"id": u.user_id, "email": u.email, "name": u.name})
