"""
URL Configuration per l'app stats.

PREFISSO: "api/stats/" (definito in ultragames_django/urls.py)

ENDPOINT COMPLETI:
  GET /api/stats/me               → StatsView.my_stats  (statistiche personali)
  GET /api/stats/ranking/<game>   → StatsView.ranking   (classifica globale)

Entrambi richiedono JWT valido (@cbv_require_auth nei metodi).

PATTERN as_view(actions=...):
  StatsView raggruppa tutti gli endpoint delle statistiche in un'unica classe.
  L'endpoint ranking ha un parametro URL <str:game> che viene passato al metodo.
"""

from django.urls import path
from .views import StatsView

urlpatterns = [
    path("me",                   StatsView.as_view(action="my_stats")),  # Stats personali
    path("ranking/<str:game>",   StatsView.as_view(action="ranking")),   # Classifica globale
]
