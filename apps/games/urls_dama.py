"""
URL Configuration per il microservizio Dama.

PREFISSO: "dama/" (definito in ultragames_django/urls.py)

ENDPOINT COMPLETI:
  GET  /dama/health → DamaView.health  (health check, nessuna autenticazione)
  POST /dama/new    → DamaView.new     (nuova partita, richiede JWT)
  GET  /dama/moves  → DamaView.moves   (mosse legali, richiede JWT)
  POST /dama/move   → DamaView.move    (esegui mossa, richiede JWT)
  POST /dama/reset  → DamaView.reset   (reset partita, richiede JWT)

PATTERN as_view(actions=...):
  DamaView raggruppa tutti gli endpoint della Dama in un'unica classe.
  as_view(action=<nome_metodo>) mappa ogni verbo HTTP
  al metodo corretto della classe gestore.

FLUSSO TIPICO DI UNA SESSIONE DAMA:
  1. POST /dama/new    → ottieni sessionId e stato iniziale
  2. GET  /dama/moves  → mosse legali disponibili per il giocatore
  3. POST /dama/move   → invia mossa → ricevi risposta AI
  4. Ripeti 2-3 fino a status ≠ "ongoing"
  5. POST /dama/reset  → nuova partita (opzionale)
"""

from django.urls import path
from .views import DamaView

urlpatterns = [
    path("health", DamaView.as_view(action="health")),  # Health check (nessun auth)
    path("new",    DamaView.as_view(action="new")),      # Nuova partita (JWT)
    path("moves",  DamaView.as_view(action="moves")),    # Mosse legali (JWT)
    path("move",   DamaView.as_view(action="move")),     # Esegui mossa (JWT)
    path("reset",  DamaView.as_view(action="reset")),    # Reset partita (JWT)
]
