"""
URL Configuration per l'app admin_panel.

PREFISSO: "api/admin/" (definito in ultragames_django/urls.py)

ENDPOINT COMPLETI:
  GET  /api/admin/users                 → AdminView.user_list     (lista utenti + stats)
  POST /api/admin/users/<user_id>/ban   → AdminView.ban_user      (banna utente)
  POST /api/admin/users/<user_id>/stats → AdminView.update_stats  (modifica statistiche)

Tutti richiedono JWT con email == ADMIN_EMAIL (@cbv_require_admin nei metodi).

PATTERN as_view(actions=...):
  AdminView raggruppa tutti gli endpoint admin in un'unica classe.
  Gli endpoint con parametro URL (<str:user_id>) passano user_id come argomento
  al metodo, come nei normali path converter di Django.
"""

from django.urls import path
from .views import AdminView

urlpatterns = [
    path("users",                    AdminView.as_view(action="user_list")),    # Lista utenti
    path("users/<str:user_id>/ban",   AdminView.as_view(action="ban_user",     allowed_methods=["DELETE"])), # DELETE Banna utente
    path("users/<str:user_id>/stats", AdminView.as_view(action="update_stats", allowed_methods=["PUT"])),    # PUT    Modifica stats
]
