"""
Package dama.services — Servizi di dominio per la Dama.

SERVIZI:
  MoveGeneratorService    → Genera mosse legali (semplici + catture/rafla)
  GameRulesService        → Applica mosse, valuta stato, obbligo cattura
  AIStrategy              → Interfaccia + Random + Minimax (OCP/LSP/DIP)
  AIStrategyFactory       → Crea la strategia AI in base alla difficoltà
  GameApplicationService  → Orchestratore use case (new_game, human_move, reset)
"""
