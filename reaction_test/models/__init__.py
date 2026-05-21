"""
Package reaction_test.models — Modelli di dominio del Reaction Test.

MODELLI:
  Session        → Aggregato: id, phase (IDLE/WAITING/GREEN/DONE),
                   green_at_ms, results (List[ReactionResult])
  SessionPhase   → Enum: IDLE, WAITING, GREEN, DONE
  ReactionResult → Singolo round: reaction_ms, clicked_early, timestamp
  Statistics     → Value Object: count, best_ms, avg_ms, worst_ms
                   (calcolato da Statistics.from_results(session.results))
"""
