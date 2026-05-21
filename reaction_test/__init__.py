"""
Package reaction_test — Dominio del Test di Reazione.

Implementa un test di reazione psicomotoria:
  1. Utente avvia il countdown (POST /reaction/start)
  2. Dopo delay random 2-5s il semaforo diventa verde (thread daemon)
  3. Utente clicca appena vede il verde (POST /reaction/click)
  4. Il sistema calcola reaction_ms e assegna un rating
  5. Le statistiche migliori vengono persistite nel DB

STRUTTURA:
  models/       → Session, ReactionResult, Statistics
  repositories/ → SessionRepository (in-memory)
  services/     → TimerStrategy, ReactionScoringService,
                   ReactionApplicationService

PERCORSO CHIAMATA:
  reaction_service_factory.get_reaction_service()
    → ReactionApplicationService(repository, timer_strategy, scoring_service)
  apps/games/views/reaction_*_view.py
    → get_reaction_service().*()
"""
