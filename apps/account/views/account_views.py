"""
account_views.py — Gestore unificato delle view per la gestione dell'account utente.

STRUTTURA DEL FILE:
  AccountView → classe gestore con i metodi HTTP dell'area account:
                  update_profile()  PUT    /api/account/profile
                  change_password() PUT    /api/account/password
                  delete_account()  DELETE /api/account/delete

PERCORSO CHIAMATA (URL → metodo):
  ultragames_django/urls.py
    → include("apps.account.urls")        [apps/account/urls.py]
      → AccountView.update_profile()  PUT    /api/account/profile
      → AccountView.change_password() PUT    /api/account/password
      → AccountView.delete_account()  DELETE /api/account/delete

SOLID PRINCIPLES:
  - SRP: Ogni metodo gestisce un solo endpoint; la logica di business è in AccountService.
  - DIP: Usa get_container() per ottenere AccountService iniettato.
  - OCP: Nuovo endpoint account = nuovo metodo nella classe, senza modificare gli altri.

SICUREZZA (comune a tutti i metodi):
  - user_id letto ESCLUSIVAMENTE da request.current_user.user_id (payload JWT)
    → prevenzione IDOR (Insecure Direct Object Reference)
  - Tutti i metodi richiedono @cbv_require_auth → 401 se token assente/scaduto
"""

import json

from django.http import JsonResponse
from django.views import View
from apps.core.action_view import ActionView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from services.container import get_container
from services.auth_helpers import cbv_require_auth


@method_decorator(csrf_exempt, name="dispatch")
class AccountView(ActionView, View):
    """
    Gestore unificato delle view per la gestione dell'account utente.

    Raccoglie in un'unica classe tutti gli endpoint di gestione account,
    condividendo le dipendenze (get_container, cbv_require_auth) senza duplicazioni.

    ENDPOINT GESTITI:
      PUT    /api/account/profile  → update_profile()  (aggiorna nome/email)
      PUT    /api/account/password → change_password() (cambia password)
      DELETE /api/account/delete   → delete_account()  (elimina account)

    Tutti richiedono JWT valido (@cbv_require_auth nel metodo).

    NOTA CSRF:
      @method_decorator(csrf_exempt, name="dispatch") disabilita il CSRF per
      tutti i metodi POST. La protezione è garantita dal JWT HttpOnly + SameSite=Lax.
    """

    # ── update_profile ────────────────────────────────────────────────────────

    @cbv_require_auth
    def update_profile(self, request):
        """
        Aggiorna il profilo (nome e/o email) dell'utente autenticato.

        ENDPOINT: PUT /api/account/profile
        BODY JSON: {"name": "Nuovo Nome", "email": "nuova@email.com"}

        RISPOSTA SUCCESSO (200):
          {"message": "Profilo aggiornato."}

        RISPOSTA ERRORI (400):
          {"error": "Il nome non può essere vuoto."}
          {"error": "Indirizzo email non valido."}
          {"error": "Email già in uso da un altro account."}
          {"error": "Utente non trovato."}

        RISPOSTA ERRORE (401):
          {"error": "Non autenticato."}  ← token assente o scaduto

        SICUREZZA:
          user_id dal JWT (non dal body) → prevenzione IDOR.
          Un utente non può modificare il profilo di un altro utente
          anche se ne conosce l'UUID.

        PERCORSO:
          → get_container().account_service.update_profile(user_id, new_name, new_email)
            [services/account_service.py]
              → user_repository.find_by_id()
              → user_repository.exists_by_email()  (se email cambiata)
              → user_repository.update(user)
        """
        self.allowed_methods = ["PUT"]
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "JSON non valido."}, status=400)

        result = get_container().account_service.update_profile(
            user_id=request.current_user.user_id,
            new_name=body.get("name", ""),
            new_email=body.get("email", ""),
        )
        if not result.success:
            return JsonResponse({"error": result.error}, status=400)
        return JsonResponse({"message": "Profilo aggiornato."})

    # ── change_password ───────────────────────────────────────────────────────

    @cbv_require_auth
    def change_password(self, request):
        """
        Cambia la password dell'utente autenticato.

        ENDPOINT: PUT /api/account/password
        BODY JSON: {"current_password": "vecchia", "new_password": "nuova1234"}

        RISPOSTA SUCCESSO (200):
          {"message": "Password cambiata."}

        RISPOSTA ERRORI (400):
          {"error": "La nuova password deve contenere almeno 8 caratteri."}
          {"error": "Utente non trovato."}
          {"error": "Password attuale non corretta."}

        RISPOSTA ERRORE (401):
          {"error": "Non autenticato."}

        SICUREZZA:
          La verifica della password attuale (bcrypt.checkpw) in AccountService
          garantisce che solo l'utente legittimo possa cambiare la password,
          anche se il token JWT fosse stato compromesso durante la sessione.

        PERCORSO:
          → get_container().account_service.change_password(user_id, current_password, new_password)
            [services/account_service.py]
              → user_repository.find_by_id()
              → bcrypt.checkpw(current_password, user.hashed_password)
              → bcrypt.hashpw(new_password)
              → user_repository.update(user)
        """
        self.allowed_methods = ["PUT"]
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "JSON non valido."}, status=400)

        result = get_container().account_service.change_password(
            user_id=request.current_user.user_id,
            current_password=body.get("current_password", ""),
            new_password=body.get("new_password", ""),
        )
        if not result.success:
            return JsonResponse({"error": result.error}, status=400)
        return JsonResponse({"message": "Password cambiata."})

    # ── delete_account ────────────────────────────────────────────────────────

    @cbv_require_auth
    def delete_account(self, request):
        """
        Elimina l'account dell'utente autenticato e tutti i suoi dati.

        ENDPOINT: DELETE /api/account/delete
        BODY JSON: {"password": "conferma_password"}

        RISPOSTA SUCCESSO (200):
          {"message": "Account eliminato."}
          Header: Set-Cookie: access_token=; Max-Age=0  ← cookie eliminato

        RISPOSTA ERRORI (400):
          {"error": "Utente non trovato."}
          {"error": "Password non corretta."}

        RISPOSTA ERRORE (401):
          {"error": "Non autenticato."}

        OPERAZIONI ESEGUITE (in AccountService):
          1. Verifica esistenza utente (find_by_id)
          2. Verifica password (bcrypt.checkpw) → conferma esplicita dell'utente
          3. Elimina stats: tris_stats, dama_stats, reaction_stats
          4. Elimina utente dalla tabella users

        POST-ELIMINAZIONE:
          Il cookie JWT viene eliminato lato client. Anche se il token fosse
          ancora valido, il browser non lo invierà più nelle richieste successive.

        PERCORSO:
          → get_container().account_service.delete_account(user_id, password)
            [services/account_service.py]
              → user_repository.find_by_id()
              → bcrypt.checkpw(password)
              → stats_repository.delete_user_stats(user_id)
              → user_repository.delete(user_id)
          → response.delete_cookie("access_token")  ← invalida il JWT lato client
        """
        self.allowed_methods = ["DELETE"]
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "JSON non valido."}, status=400)

        result = get_container().account_service.delete_account(
            user_id=request.current_user.user_id,
            password=body.get("password", ""),
        )
        if not result.success:
            return JsonResponse({"error": result.error}, status=400)

        # Account eliminato: invalida il cookie JWT lato client.
        response = JsonResponse({"message": "Account eliminato."})
        response.delete_cookie("access_token")
        return response
