"""
URL Configuration per il microservizio Tris.

PREFISSO: "tris/" (definito in ultragames_django/urls.py)

ENDPOINT COMPLETI:
  GET  /tris/health → TrisView.health  (health check, nessuna autenticazione)
  POST /tris/new    → TrisView.new     (nuova partita, richiede JWT)
  POST /tris/move   → TrisView.move    (esegui mossa + risposta AI, richiede JWT)
  POST /tris/reset  → TrisView.reset   (reset partita, richiede JWT)

PATTERN as_view(actions=...):
  Poiché TrisView raggruppa più metodi HTTP logici in un'unica classe,
  gli URL usano as_view(action=<nome_metodo>) per mappare
  esplicitamente ogni verbo HTTP al metodo corretto della classe gestore.

  Esempio: path("new", TrisView.as_view(action="new"))
    → POST /tris/new → TrisView.new(request)

FLUSSO TIPICO DI UNA SESSIONE TRIS:
  1. POST /tris/new   → ottieni sessionId e board vuota
  2. POST /tris/move  → invia cell → ricevi risposta AI + nuovo stato
  3. Ripeti 2 fino a status ≠ "ongoing"
  4. POST /tris/reset → nuova partita (opzionale)

NOTE:
  Il Tris NON ha un endpoint /moves perché le celle disponibili sono
  semplicemente quelle vuote (board[i] == ""), calcolabili dal client
  direttamente dalla board restituita.
"""

from django.urls import path
from .views import TrisView

urlpatterns = [
    path("health", TrisView.as_view(action="health")),  # Health check (nessun auth)
    path("new",    TrisView.as_view(action="new")),      # Nuova partita (JWT)
    path("move",   TrisView.as_view(action="move")),     # Esegui mossa (JWT)
    path("reset",  TrisView.as_view(action="reset")),    # Reset partita (JWT)
]
