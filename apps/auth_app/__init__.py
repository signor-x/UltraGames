"""
Package apps.auth_app — App Django per l'autenticazione JWT.

Gestisce registrazione, login, logout e lettura del profilo corrente.
Usa cookie HttpOnly con JWT per l'autenticazione stateless.

CONTENUTO:
  views/   → RegisterView, LoginView, LogoutView, MeView
  urls.py  → /api/auth/register, /api/auth/login, /api/auth/logout, /api/auth/me
"""
