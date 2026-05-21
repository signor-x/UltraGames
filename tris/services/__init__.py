"""
Package tris.services — Servizi di dominio per il Tris.

SERVIZI:
  GameLogicService        → Applica mosse, valuta stato (win/draw/ongoing)
  AIStrategy (ABC)        → Interfaccia strategia AI
  RandomAIStrategy        → Sceglie cella libera casualmente
  MinimaxAIStrategy       → Minimax alpha-beta (imbattibile)
  AIStrategyFactory       → Crea la strategia in base alla difficoltà (OCP)
  GameApplicationService  → Orchestratore: new_game, human_move, reset_game
"""
