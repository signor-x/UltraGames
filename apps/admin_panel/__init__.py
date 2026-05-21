"""
Package apps.admin_panel — App Django per il pannello amministrativo.

Permette all'amministratore di visualizzare la lista utenti,
bannare utenti e modificare manualmente le statistiche di gioco.

CONTENUTO:
  views/   → UserListView, BanUserView, UpdateStatsView
  urls.py  → /api/admin/users, /api/admin/users/<id>/ban, /api/admin/users/<id>/stats
"""
