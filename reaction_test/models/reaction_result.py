"""
ReactionResult — Modello di dominio per il risultato di un singolo round (SRP).

RESPONSABILITÀ (SRP):
  Rappresenta il risultato di un round del Reaction Test:
    - reaction_ms: Tempo di reazione in millisecondi (0 se early click)
    - clicked_early: True se l'utente ha cliccato durante WAITING (prima del verde)
    - timestamp: Quando il click è avvenuto

FACTORY METHODS:
  ReactionResult.valid(reaction_ms)  → round completato correttamente
  ReactionResult.early_click()       → click anticipato (durante WAITING)

  Questi factory method evitano costruzioni errate (es. reaction_ms<0 per early).
  Implementano il pattern Factory Method (OCP: aggiungere altri tipi di risultato
  senza modificare il costruttore).

PERCORSO CHIAMATA:
  ReactionApplicationService.register_click()
    → Se phase=WAITING: ReactionResult.early_click()
    → Se phase=GREEN:   ReactionResult.valid(click_at_ms - green_at_ms)
    → session.results.append(result)
  Statistics.from_results(session.results)
    → Aggrega tutti i ReactionResult validi (clicked_early=False)
"""

import uuid
from datetime import datetime
from typing import Optional


class ReactionResult:
    """
    Risultato di un singolo round del Reaction Test.

    UTILIZZO:
      result = ReactionResult.valid(215)        → round valido, 215ms
      result = ReactionResult.early_click()     → click anticipato
    """

    def __init__(
        self,
        reaction_ms:   int,
        clicked_early: bool,
        result_id:     Optional[str] = None,
    ):
        """
        Costruttore diretto (preferire i factory method per chiarezza).

        :param reaction_ms: Millisecondi dal verde al click (0 se early)
        :param clicked_early: True se click anticipato (fase WAITING)
        :param result_id: UUID del risultato; se None, ne genera uno nuovo
        """
        self.id:            str      = result_id or str(uuid.uuid4())
        self.reaction_ms:   int      = reaction_ms
        self.clicked_early: bool     = clicked_early
        self.timestamp:     datetime = datetime.utcnow()

    @classmethod
    def valid(cls, reaction_ms: int) -> "ReactionResult":
        """
        Crea un risultato valido (click avvenuto durante fase GREEN).

        CHIAMATO DA:
          ReactionApplicationService.register_click() quando phase=GREEN

        :param reaction_ms: Tempo di reazione in ms (click_at_ms - green_at_ms)
        :return: ReactionResult con clicked_early=False
        """
        return cls(reaction_ms=reaction_ms, clicked_early=False)

    @classmethod
    def early_click(cls) -> "ReactionResult":
        """
        Crea un risultato per click anticipato (click durante fase WAITING).

        CHIAMATO DA:
          ReactionApplicationService.register_click() quando phase=WAITING

        :return: ReactionResult con reaction_ms=0 e clicked_early=True
        """
        return cls(reaction_ms=0, clicked_early=True)

    def to_dict(self) -> dict:
        """
        Serializza il risultato per la risposta HTTP.

        CHIAMATO DA:
          Session.to_dict() → include tutti i risultati della sessione
          ReactionApplicationService.register_click() → include il risultato corrente

        :return: Dizionario JSON-serializzabile
        """
        return {
            "id":           self.id,
            "reactionMs":   self.reaction_ms,
            "clickedEarly": self.clicked_early,
            "timestamp":    self.timestamp.isoformat(),  # "2026-05-12T14:30:00.123456"
        }
