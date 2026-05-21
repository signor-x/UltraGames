"""
Piece — Entità di dominio per un singolo pezzo della Dama (SRP).

RESPONSABILITÀ (SRP):
  Rappresenta SOLO i dati di un pezzo: colore e tipo (pedina/dama).
  La logica di movimento è in MoveGeneratorService.
  La logica di promozione è gestita in GameRulesService.apply_move().

IMMUTABILITÀ (@dataclass frozen):
  Piece è frozen=True: le sue istanze non possono essere modificate dopo
  la creazione. Questo garantisce che lo stesso oggetto Piece non venga
  accidentalmente mutato da codice in diversi punti.
  Per la promozione, si crea un NUOVO Piece (tramite promote()).

SOLID PRINCIPLES:
  - SRP: Solo dati del pezzo + un metodo di utilità (is_king, promote).
  - OCP: Aggiungere nuovi tipi di pezzo (es. "super dama") richiede
    aggiungere un valore a PieceType senza modificare Piece.

PERCORSO CHIAMATA:
  Board.initial()
    → Crea tutti i Piece della posizione iniziale
  GameRulesService.apply_move()
    → piece.is_king() → verifica promozione
    → piece.promote() → crea nuovo Piece promosso
  MoveGeneratorService._find_captures()
    → piece.is_king() → determina le regole di cattura
  AIStrategy._evaluate()
    → piece.is_king() → valore diverso nella funzione euristica
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum


class PieceColor(str, Enum):
    """Colore del pezzo: WHITE (giocatore umano) o BLACK (AI)."""
    WHITE = "white"
    BLACK = "black"


class PieceType(str, Enum):
    """Tipo del pezzo: PAWN (pedina normale) o KING (dama promossa)."""
    PAWN = "pawn"
    KING = "king"


@dataclass(frozen=True)
class Piece:
    """
    Pezzo immutabile della Dama (frozen dataclass).

    ATTRIBUTI:
      color (PieceColor): WHITE o BLACK
      type  (PieceType):  PAWN (pedina) o KING (dama)
      id    (str):        Identificatore univoco persistente del pezzo.
                          Rimane lo stesso dopo la promozione a dama,
                          permettendo al frontend di tracciare il singolo pezzo.

    FROZEN:
      frozen=True rende le istanze hashable e impedisce modifiche accidentali.
    """
    color: PieceColor
    type:  PieceType = PieceType.PAWN
    id:    str       = field(default_factory=lambda: str(uuid.uuid4()))

    def is_king(self) -> bool:
        """
        Restituisce True se il pezzo è una dama (può volare diagonalmente).

        CHIAMATO DA:
          MoveGeneratorService.generate_simple_moves() → regole di movimento
          MoveGeneratorService._find_captures()        → regole di cattura
          GameRulesService.apply_move()                → verifica promozione
          MinimaxAIStrategy._evaluate()               → valore nella funzione euristica
        """
        return self.type == PieceType.KING

    def promote(self) -> "Piece":
        """
        Crea un nuovo Piece dello stesso colore ma di tipo KING (dama).

        IMMUTABILITÀ: Non modifica self (frozen). Restituisce un nuovo oggetto.

        CHIAMATO DA: GameRulesService.apply_move()
          Quando una pedina raggiunge l'ultima riga avversaria.

        :return: Nuovo Piece con type=KING e stesso color
        """
        return Piece(color=self.color, type=PieceType.KING, id=self.id)
