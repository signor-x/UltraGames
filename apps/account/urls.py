"""
URL Configuration per l'app account.

PREFISSO: "api/account/" (definito in ultragames_django/urls.py)

ENDPOINT COMPLETI:
  POST /api/account/profile  → AccountView.update_profile  (aggiorna nome e/o email)
  POST /api/account/password → AccountView.change_password (cambia password)
  POST /api/account/delete   → AccountView.delete_account  (elimina account)

Tutti gli endpoint richiedono autenticazione JWT (@cbv_require_auth nei metodi).

PATTERN as_view(actions=...):
  AccountView raggruppa tutti gli endpoint di gestione account in un'unica classe.
  as_view(action=<nome_metodo>) mappa il verbo POST al metodo corretto.

FLUSSO TIPICO:
  1. Utente autenticato vuole cambiare nome:
     POST /api/account/profile  con {"name": "Nuovo Nome", "email": "stessa@email.com"}
  2. Utente vuole cambiare password:
     POST /api/account/password con {"current_password": "vecchia", "new_password": "nuova"}
  3. Utente vuole eliminare l'account:
     POST /api/account/delete   con {"password": "conferma"}
"""

from django.urls import path
from .views import AccountView

urlpatterns = [
    path("profile",  AccountView.as_view(action="update_profile",  allowed_methods=["PUT"])),    # PUT  Aggiorna profilo
    path("password", AccountView.as_view(action="change_password", allowed_methods=["PUT"])),    # PUT  Cambia password
    path("delete",   AccountView.as_view(action="delete_account",  allowed_methods=["DELETE"])), # DELETE Elimina account
]
