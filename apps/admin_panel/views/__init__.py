"""
Package di esportazione delle view dell'app admin_panel.

VIEW ESPORTATA:
  AdminView → raggruppa tutti gli endpoint del pannello amministrativo:
    user_list()    → GET  /api/admin/users                 (lista utenti + stats)
    ban_user()     → POST /api/admin/users/<user_id>/ban   (banna utente)
    update_stats() → POST /api/admin/users/<user_id>/stats (modifica statistiche)

  Tutti richiedono JWT valido + email == ADMIN_EMAIL (@cbv_require_admin).

PERCORSO FILE:
  AdminView ← apps/admin_panel/views/admin_views.py
"""

from .admin_views import AdminView

__all__ = ["AdminView"]
