"""
Package di esportazione delle view dell'app account.

PATTERN __init__.py:
  Ri-esporta la classe gestore AccountView in modo che
  apps/account/urls.py possa importarla con:
    from .views import AccountView

VIEW ESPORTATA:
  AccountView → raggruppa tutti gli endpoint di gestione account:
    update_profile()  → POST /api/account/profile  (aggiorna nome/email)
    change_password() → POST /api/account/password (cambia password)
    delete_account()  → POST /api/account/delete   (elimina account)

  Tutti i metodi richiedono JWT valido (@cbv_require_auth).

PERCORSO FILE:
  AccountView ← apps/account/views/account_views.py
"""

from .account_views import AccountView

__all__ = ["AccountView"]
