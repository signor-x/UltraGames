"""
admin_views.py — Gestore unificato delle view per il pannello amministrativo.

STRUTTURA DEL FILE:
  AdminView → classe gestore con i metodi HTTP del pannello admin:
                user_list()     GET  /api/admin/users
                ban_user()      DELETE /api/admin/users/<user_id>/ban
                update_stats()  PUT    /api/admin/users/<user_id>/stats

PERCORSO CHIAMATA (URL → metodo):
  ultragames_django/urls.py
    → include("apps.admin_panel.urls")    [apps/admin_panel/urls.py]
      → AdminView.user_list()     GET  /api/admin/users
      → AdminView.ban_user()      DELETE /api/admin/users/<user_id>/ban
      → AdminView.update_stats()  PUT    /api/admin/users/<user_id>/stats

SOLID PRINCIPLES:
  - SRP: Ogni metodo gestisce un solo endpoint; la logica DB è nei repository.
  - DIP: Usa get_container() per ottenere user_repository e stats_repository.
  - OCP: Nuova funzionalità admin = nuovo metodo, senza modificare gli altri.

SICUREZZA (comune a tutti i metodi):
  - Tutti i metodi richiedono @cbv_require_admin:
      1. request.current_user is None → 401 Unauthorized
      2. request.current_user.email != ADMIN_EMAIL → 403 Forbidden
  - ban_user() ha una guardia anti-self-ban aggiuntiva.
"""

import json

from django.http import JsonResponse
from django.views import View
from apps.core.action_view import ActionView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from services.container import get_container
from services.auth_helpers import cbv_require_admin


@method_decorator(csrf_exempt, name="dispatch")
class AdminView(ActionView, View):
    """
    Gestore unificato delle view per il pannello amministrativo.

    Raccoglie in un'unica classe tutti gli endpoint admin, condividendo
    le dipendenze (get_container, cbv_require_admin) senza duplicazioni.

    ENDPOINT GESTITI:
      GET  /api/admin/users                 → user_list()    (lista utenti + stats)
      DELETE /api/admin/users/<user_id>/ban   → ban_user()     (banna utente)
      PUT    /api/admin/users/<user_id>/stats → update_stats() (modifica statistiche)

    Tutti richiedono JWT valido + email == ADMIN_EMAIL (@cbv_require_admin).
    """

    # ── user_list ─────────────────────────────────────────────────────────────

    @cbv_require_admin
    def user_list(self, request):
        """
        Restituisce la lista di tutti gli utenti con le loro statistiche di gioco.

        ENDPOINT: GET /api/admin/users
        AUTENTICAZIONE: JWT con email = ADMIN_EMAIL.

        RISPOSTA SUCCESSO (200):
          {
            "users": [
              {
                "id": "<UUID>",
                "email": "user@example.com",
                "name": "Mario",
                "stats": {
                  "tris":     {"wins": 5, "losses": 3, "draws": 1},
                  "dama":     {"wins": 2, "losses": 4},
                  "reaction": {"best_ms": 210, "attempts": 15}
                }
              }, ...
            ]
          }

        RISPOSTA ERRORI:
          401 {"error": "Non autenticato."}
          403 {"error": "Accesso non autorizzato."}

        NOTA PRESTAZIONI:
          Per ogni utente viene eseguita una query get_user_stats() (3 SELECT).
          Con N utenti → N*3+1 query totali. In produzione considerare
          una query JOIN ottimizzata o caching.

        PERCORSO:
          → get_container().user_repository.find_all()
            [services/user_repository.py]
          → get_container().stats_repository.get_user_stats(u.id)   ← per ogni utente
            [services/stats_repository.py]
        """
        self.allowed_methods = ["GET"]
        c = get_container()
        users = c.user_repository.find_all()

        result = [
            {
                "id":    u.id,
                "email": u.email,
                "name":  u.name,
                "stats": c.stats_repository.get_user_stats(u.id),
            }
            for u in users
        ]
        return JsonResponse({"users": result})

    # ── ban_user ──────────────────────────────────────────────────────────────

    @cbv_require_admin
    def ban_user(self, request, user_id: str):
        """
        Banna un utente: elimina i suoi dati statistici e il suo account.

        ENDPOINT: DELETE /api/admin/users/<user_id>/ban
        PARAMETRO URL: user_id → UUID dell'utente da bannare
        BODY: (vuoto, l'ID arriva dalla URL)

        RISPOSTA SUCCESSO (200):
          {"message": "Utente 'Mario' bannato con successo."}

        RISPOSTA ERRORI:
          400 {"error": "Non puoi bannare te stesso."}
          404 {"error": "Utente non trovato."}
          401 {"error": "Non autenticato."}
          403 {"error": "Accesso non autorizzato."}

        GUARDIA ANTI-SELF-BAN:
          Verifica che l'admin non stia tentando di bannare se stesso
          (user_id == request.current_user.user_id). Previene la perdita
          accidentale dell'unico account admin.

        ORDINE OPERAZIONI (prevenzione errori FK):
          1. delete_user_stats → elimina tris_stats, dama_stats, reaction_stats
          2. user_repository.delete → elimina la riga in users

        PERCORSO:
          → get_container().user_repository.find_by_id(user_id)
          → get_container().stats_repository.delete_user_stats(user_id)
          → get_container().user_repository.delete(user_id)
        """
        self.allowed_methods = ["DELETE"]
        if user_id == request.current_user.user_id:
            return JsonResponse({"error": "Non puoi bannare te stesso."}, status=400)

        c = get_container()
        user = c.user_repository.find_by_id(user_id)
        if user is None:
            return JsonResponse({"error": "Utente non trovato."}, status=404)

        # Elimina prima le statistiche (righe nelle tabelle *_stats)
        # poi l'utente stesso (riga in users). Ordine necessario per le FK.
        c.stats_repository.delete_user_stats(user_id)
        c.user_repository.delete(user_id)

        return JsonResponse({"message": f"Utente '{user.name}' bannato con successo."})

    # ── update_stats ──────────────────────────────────────────────────────────

    @cbv_require_admin
    def update_stats(self, request, user_id: str):
        """
        Aggiorna manualmente le statistiche di gioco di un utente (uso amministrativo).

        ENDPOINT: PUT /api/admin/users/<user_id>/stats
        PARAMETRO URL: user_id → UUID dell'utente target
        BODY JSON (tutte le chiavi sono opzionali):
          {
            "tris":     {"wins": 10, "losses": 2, "draws": 1},
            "dama":     {"wins": 5, "losses": 3},
            "reaction": {"best_ms": 180, "attempts": 20}
          }

        RISPOSTA SUCCESSO (200):
          {"message": "Statistiche aggiornate."}

        RISPOSTA ERRORI:
          400 {"error": "JSON non valido."}
          400 {"error": "<messaggio da set_user_stats>"}
          401 {"error": "Non autenticato."}
          403 {"error": "Accesso non autorizzato."}

        NOTA:
          set_user_stats() esegue UPSERT per ogni gioco presente nel body.
          Se una chiave ("tris", "dama", "reaction") è assente, quella
          tabella non viene toccata (aggiornamento granulare).

        PERCORSO:
          → get_container().stats_repository.set_user_stats(user_id, body)
            [services/stats_repository.py]
        self.allowed_methods = ["PUT"]
        """
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "JSON non valido."}, status=400)

        try:
            get_container().stats_repository.set_user_stats(user_id, body)
        except Exception as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        return JsonResponse({"message": "Statistiche aggiornate."})
