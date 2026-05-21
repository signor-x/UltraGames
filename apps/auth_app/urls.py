"""
URL Configuration per l'app auth_app.

PREFISSO: "api/auth/" (definito in ultragames_django/urls.py)

ENDPOINT COMPLETI:
  POST /api/auth/register → AuthView.register  (crea nuovo account)
  POST /api/auth/login    → AuthView.login     (autentica + cookie JWT)
  POST /api/auth/logout   → AuthView.logout    (cancella cookie JWT)
  GET  /api/auth/me       → AuthView.me        (dati utente dal JWT, richiede JWT)

PATTERN as_view(actions=...):
  AuthView raggruppa tutti gli endpoint di autenticazione in un'unica classe.
  as_view(actions={<http_method>: <nome_metodo>}) mappa ogni verbo HTTP
  al metodo corretto della classe gestore.
"""

from django.urls import path
from .views import AuthView

urlpatterns = [
    path("register", AuthView.as_view(action="register")),  # Crea nuovo account
    path("login",    AuthView.as_view(action="login")),      # Autentica + JWT
    path("logout",   AuthView.as_view(action="logout")),     # Cancella cookie JWT
    path("me",       AuthView.as_view(action="me")),         # Dati utente (JWT)
]
