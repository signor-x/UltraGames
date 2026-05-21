"""
Move — Value Object per una mossa della Dama (SRP).

RESPONSABILITÀ (SRP):
  Rappresenta una mossa completa: percorso (path) e pezzi catturati (captures).
  Non contiene logica di validazione (→ GameRulesService) né generazione (→ MoveGeneratorService).

STRUTTURA:
  path:     Lista di [row, col] dalla posizione iniziale a quella finale
            (inclusi eventuali passaggi intermedi nella rafla)
  captures: Lista di [row, col] dei pezzi avversari catturati

SERIALIZZAZIONE:
  to_dict() → JSON per la risposta HTTP (view → client)
  from_dict() → Ricostruzione dalla richiesta HTTP del client

PERCORSO CHIAMATA:
  MoveGeneratorService.generate_*()
    → crea Move(path=..., captures=...)
  GameApplicationService._is_legal()
    → confronta move.path e move.captures con le mosse legali
  DamaMoveView.post()
    → move = Move.from_dict(body["move"])  ← dal JSON del client
  GameApplicationService._response()
    → [m.to_dict() for m in moves]         ← per la risposta HTTP
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Move:
    """
    Rappresenta una mossa completa nella Dama.

    ATTRIBUTI:
      path:     Lista di coordinate [[r1,c1], [r2,c2], ...] (2+ elementi)
      captures: Lista di coordinate [[rc,cc], ...] dei pezzi catturati (vuota se mossa semplice)
    """
    path:     List[List[int]] = field(default_factory=list)
    captures: List[List[int]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """
        Serializza la mossa per la risposta HTTP JSON.

        CHIAMATO DA:
          GameApplicationService._response() → "legalMoves": [m.to_dict() for m in moves]
          GameApplicationService._ai_turn()  → "aiMove": ai_move.to_dict()
        """
        return {"path": self.path, "captures": self.captures}

    @classmethod
    def from_dict(cls, data: dict) -> "Move":
        """
        Deserializza una mossa dalla richiesta HTTP del client.

        CHIAMATO DA:
          GameApplicationService.human_move()
            → move = Move.from_dict(move_dict)

        :param data: Dizionario {"path": [...], "captures": [...]}
        :return: Istanza Move
        """
        return cls(
            path=data.get("path", []),
            captures=data.get("captures", []),
        )
