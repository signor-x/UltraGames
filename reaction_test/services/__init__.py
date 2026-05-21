"""
Package reaction_test.services — Servizi di dominio per il Reaction Test.

SERVIZI:
  TimerStrategy (ABC)         → Interfaccia per il delay del countdown
  RandomTimerStrategy         → Delay casuale 2.0-5.0 secondi (produzione)
  FixedTimerStrategy          → Delay fisso (test e sviluppo)
  ReactionScoringService      → Rating dal tempo: FULMINE/ECCELLENTE/BUONO/NORMALE/LENTO
  ReactionApplicationService  → Orchestratore: new_session, start_round,
                                  get_phase, register_click, get_stats, reset_session
"""
