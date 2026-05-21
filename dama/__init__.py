"""
Package dama — Dominio di gioco per la Dama italiana.

Implementa la logica completa della Dama italiana con:
  - Obbligo di cattura e rafla
  - Promozione a dama (volo)
  - Strategia AI Random e Minimax alpha-beta (profondità 6)
  - Patta a 40 mosse senza catture

STRUTTURA:
  models/       → Entità di dominio (Board, Piece, Move, GameState)
  repositories/ → Persistenza in-memory delle sessioni (GameSessionRepository)
  services/     → Logica di gioco (GameRulesService, MoveGeneratorService,
                   AIStrategy, GameApplicationService)

PERCORSO CHIAMATA PRINCIPALE:
  dama_service_factory.get_dama_service()
    → GameApplicationService(repository, rules, strategy_factory)
  apps/games/views/dama_*_view.py
    → get_dama_service().*()
"""
