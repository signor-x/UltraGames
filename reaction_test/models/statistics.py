"""
Statistics — Modello di aggregazione statistiche di sessione (SRP).

RESPONSABILITÀ (SRP):
  Calcola e contiene le statistiche aggregate dei round validi di una sessione:
  contatore, best_ms, avg_ms, worst_ms.
  Non gestisce persistenza DB (→ InDatabaseStatsRepository) né logica di gioco.

DIFFERENZA CON InDatabaseStatsRepository:
  - Statistics: statistiche in-memory della SESSIONE corrente (in RAM)
  - InDatabaseStatsRepository: statistiche globali PERSISTITE nel DB

PATTERN: Value Object immutabile (calcolato da from_results()).

PERCORSO CHIAMATA:
  ReactionApplicationService.get_stats(sid)
    → Statistics.from_results(session.results)  ← questo file
      → Aggrega tutti i round con clicked_early=False
    → stats.to_dict()
  ReactionApplicationService.register_click()
    → Stessa cosa, inclusa nella risposta del click
"""

from typing import List, Optional
from .reaction_result import ReactionResult


class Statistics:
    """
    Statistiche aggregate dei round validi di una sessione Reaction Test.

    VALORE OGGETTO: Una volta creato, non viene modificato.
    Viene ricalcolato ogni volta da from_results() per garantire consistenza.
    """

    def __init__(
        self,
        count:    int,
        best_ms:  Optional[int],
        avg_ms:   Optional[float],
        worst_ms: Optional[int],
    ):
        self.count:    int            = count
        self.best_ms:  Optional[int]  = best_ms    # Miglior tempo (ms più basso)
        self.avg_ms:   Optional[float]= avg_ms      # Media
        self.worst_ms: Optional[int]  = worst_ms   # Peggior tempo (ms più alto)

    @classmethod
    def from_results(cls, results: List[ReactionResult]) -> "Statistics":
        """
        Factory method: calcola le statistiche dai risultati della sessione.

        FILTRAGGIO:
          Considera solo i round con clicked_early=False e reaction_ms > 0.
          I click anticipati NON contribuiscono alle statistiche.

        CHIAMATO DA:
          ReactionApplicationService.get_stats()
          ReactionApplicationService.register_click()

        :param results: Lista di ReactionResult dalla sessione corrente
        :return: Istanza Statistics con i valori calcolati (None se nessun round valido)
        """
        # Filtra i round validi (esclude early click e reaction_ms=0)
        valid = [r.reaction_ms for r in results if not r.clicked_early and r.reaction_ms > 0]

        if not valid:
            # Nessun round valido ancora: restituisce statistiche vuote
            return cls(count=0, best_ms=None, avg_ms=None, worst_ms=None)

        return cls(
            count=len(valid),
            best_ms=min(valid),                         # Tempo migliore
            avg_ms=round(sum(valid) / len(valid), 1),   # Media con 1 decimale
            worst_ms=max(valid),                        # Tempo peggiore
        )

    def to_dict(self) -> dict:
        """
        Serializza le statistiche per la risposta HTTP.

        CHIAMATO DA:
          ReactionApplicationService.get_stats() → risposta /reaction/stats
          ReactionApplicationService.register_click() → campo "stats" nella risposta

        :return: Dizionario JSON-serializzabile con count, bestMs, avgMs, worstMs
        """
        return {
            "count":   self.count,
            "bestMs":  self.best_ms,    # null se nessun round valido
            "avgMs":   self.avg_ms,
            "worstMs": self.worst_ms,
        }
