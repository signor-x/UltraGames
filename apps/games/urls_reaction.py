"""
URL Configuration per il microservizio Test di Reazione.

PREFISSO: "reaction/" (definito in ultragames_django/urls.py)

ENDPOINT COMPLETI:
  GET  /reaction/health → ReactionView.health  (health check, nessuna autenticazione)
  POST /reaction/new    → ReactionView.new     (nuova sessione, richiede JWT)
  POST /reaction/start  → ReactionView.start   (avvia countdown, richiede JWT)
  GET  /reaction/phase  → ReactionView.phase   (polling fase, richiede JWT)
  POST /reaction/click  → ReactionView.click   (registra click, richiede JWT)
  GET  /reaction/stats  → ReactionView.stats   (statistiche sessione, richiede JWT)
  POST /reaction/reset  → ReactionView.reset   (reset sessione, richiede JWT)

PATTERN as_view(actions=...):
  ReactionView raggruppa tutti gli endpoint del Reaction Test in un'unica
  classe. as_view(action=<nome_metodo>) mappa ogni verbo
  HTTP al metodo corretto della classe gestore.

FLUSSO COMPLETO CLIENT → SERVER:
  1. POST /reaction/new    → crea sessione (phase=idle)
  2. POST /reaction/start  → avvia countdown (phase=waiting, thread daemon)
  3. GET  /reaction/phase  → polling ogni ~50ms finché phase=green
  4. [utente vede il verde e clicca il prima possibile]
  5. POST /reaction/click  → registra click (reaction_ms, rating)
  6. GET  /reaction/stats  → vedi statistiche sessione corrente
  7. POST /reaction/reset  → ricomincia (torna a phase=idle)
"""

from django.urls import path
from .views import ReactionView

urlpatterns = [
    path("health", ReactionView.as_view(action="health")),  # Health check (nessun auth)
    path("new",    ReactionView.as_view(action="new")),      # Nuova sessione (JWT)
    path("start",  ReactionView.as_view(action="start")),    # Avvia countdown (JWT)
    path("phase",  ReactionView.as_view(action="phase")),    # Polling fase (JWT)
    path("click",  ReactionView.as_view(action="click")),    # Registra click (JWT)
    path("stats",  ReactionView.as_view(action="stats")),    # Statistiche sessione (JWT)
    path("reset",  ReactionView.as_view(action="reset")),    # Reset sessione (JWT)
]
