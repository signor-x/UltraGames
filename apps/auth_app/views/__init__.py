"""
Package di esportazione delle view dell'app auth_app.

PATTERN __init__.py:
  Ri-esporta la classe gestore AuthView in modo che
  apps/auth_app/urls.py possa importarla con:
    from .views import AuthView

VIEW ESPORTATA:
  AuthView → raggruppa tutti gli endpoint di autenticazione:
    register() → POST /api/auth/register  (crea nuovo account)
    login()    → POST /api/auth/login     (autentica + cookie JWT)
    logout()   → POST /api/auth/logout    (cancella cookie JWT)
    me()       → GET  /api/auth/me        (dati utente dal JWT)

PERCORSO FILE:
  AuthView ← apps/auth_app/views/auth_views.py
"""

from .auth_views import AuthView

__all__ = ["AuthView"]
