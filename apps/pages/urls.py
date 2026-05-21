"""
URL Configuration per l'app pages (frontend).

ENDPOINT:
  GET /              → PagesView.root           (redirect a /login)
  GET /login         → PagesView.login_page     (serve login.html)
  GET /register      → PagesView.register_page  (serve register.html)
  GET /home          → PagesView.home_page       (serve home.html, JWT)
  GET /admin         → PagesView.admin_page      (serve admin.html, JWT + admin)
  GET /script/<file> → PagesView.serve_script    (serve JS)
  GET /style/<file>  → PagesView.serve_style     (serve CSS)

PATTERN as_view(actions=...):
  PagesView raggruppa tutti gli endpoint del frontend in un'unica classe.
  as_view(actions={"get": <nome_metodo>}) mappa GET al metodo corretto.
  Gli endpoint con parametro URL (<str:file>) passano file come argomento al metodo.
"""

from django.urls import path
from .views import PagesView

urlpatterns = [
    path("",                  PagesView.as_view(action="root")),           # Redirect /login
    path("login",             PagesView.as_view(action="login_page")),     # login.html
    path("register",          PagesView.as_view(action="register_page")),  # register.html
    path("home",              PagesView.as_view(action="home_page")),      # home.html (JWT)
    path("admin",             PagesView.as_view(action="admin_page")),     # admin.html (JWT+admin)
    path("script/<str:file>", PagesView.as_view(action="serve_script")),  # Serve JS
    path("style/<str:file>",  PagesView.as_view(action="serve_style")),   # Serve CSS
]
