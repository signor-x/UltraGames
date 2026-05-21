"""
Package tris — Dominio di gioco per il Tris (Tic-Tac-Toe).

Implementa la logica completa del Tris su griglia 3x3 con:
  - Strategia AI Random (per principianti)
  - Strategia AI Minimax alpha-beta (imbattibile)

STRUTTURA:
  models/       → GameState (board 9 celle, turno, status, winner_combo)
  repositories/ → Persistenza in-memory sessioni (GameSessionRepository)
  services/     → Logica (GameLogicService, AIStrategy, GameApplicationService)

PERCORSO CHIAMATA:
  tris_service_factory.get_tris_service()
    → GameApplicationService(repository, logic, strategy_factory)
  apps/games/views/tris_*_view.py
    → get_tris_service().*()
"""
