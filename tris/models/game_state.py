"""
GameState (Tris) — Stato completo di una partita di Tris (SRP).

RESPONSABILITÀ (SRP):
  Rappresenta lo stato della board 3x3, il turno corrente, lo status
  della partita e la combinazione vincente. Non contiene logica di gioco
  (delegata a GameLogicService).

STRUTTURA BOARD:
  Lista di 9 stringhe (row-major):
  [0, 1, 2]
  [3, 4, 5]
  [6, 7, 8]
  Valori: "X" (HUMAN), "O" (AI), "" (vuoto)

WIN_COMBOS:
  8 combinazioni vincenti (3 righe + 3 colonne + 2 diagonali).
  Definite come costante di classe per essere riutilizzate da GameLogicService._evaluate().

SOLID PRINCIPLES:
  - SRP: Solo dati di stato. Nessuna logica di valutazione.
  - OCP: Aggiungere campi (es. move_count) non richiede modifiche ai servizi.

PERCORSO CHIAMATA:
  tris_service_factory.get_tris_service()
    → GameApplicationService(repository=GameSessionRepository(), ...)
  GameSessionRepository.create()
    → {"state": GameState(), ...}   ← stato iniziale
  GameLogicService.apply_move()
    → state.clone()                 ← copia sicura
    → new_state.board[cell] = ...   ← modifica la copia
    → new_state.status, ...         ← aggiornato da _evaluate()
  GameApplicationService._build_response()
    → state.to_dict()               ← serializzazione per la view
"""

from enum import Enum
from typing import Optional, List
import copy


class Player(str, Enum):
    """
    Enum per i giocatori del Tris.

    Eredita da str: Player.HUMAN == "X" (confrontabile direttamente con board[i]).
    EMPTY rappresenta una cella vuota (board[i] == "").
    """
    HUMAN = "X"
    AI    = "O"
    EMPTY = ""


class GameStatus(str, Enum):
    """Enum per lo stato della partita di Tris."""
    ONGOING   = "ongoing"
    HUMAN_WIN = "human_win"
    AI_WIN    = "ai_win"
    DRAW      = "draw"


class GameState:
    """
    Stato immutabile (tramite clone) di una partita di Tris.

    ATTRIBUTI:
      board (List[str])          : 9 celle della griglia 3x3
      current_turn (Player)      : Chi deve muovere (HUMAN o AI)
      status (GameStatus)        : Stato corrente della partita
      winner_combo (List[int])   : Indici della combinazione vincente (es. [0,4,8])
                                   None se non c'è ancora un vincitore

    CHIAMATO DA:
      GameSessionRepository.create()     → GameState() (iniziale)
      GameLogicService.apply_move()      → state.clone() + modifica clone
      GameApplicationService.*()         → state.to_dict() per risposta HTTP
    """

    # Costante di classe: tutte le combinazioni di 3 celle che costituiscono una vittoria.
    # Condivisa con GameLogicService._evaluate() tramite GameState.WIN_COMBOS.
    WIN_COMBOS = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Righe orizzontali
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Colonne verticali
        [0, 4, 8], [2, 4, 6],             # Diagonali
    ]

    def __init__(
        self,
        board:        Optional[List[str]] = None,
        current_turn: Player              = Player.HUMAN,
        status:       GameStatus          = GameStatus.ONGOING,
        winner_combo: Optional[List[int]] = None,
    ):
        """
        :param board: 9 celle; se None → tutte vuote (inizio partita)
        :param current_turn: Chi inizia; default HUMAN (X va per primo)
        :param status: Stato partita; default ONGOING
        :param winner_combo: Celle della tripletta vincente; default None
        """
        self.board:        List[str]          = board if board is not None else [Player.EMPTY.value] * 9
        self.current_turn: Player             = current_turn
        self.status:       GameStatus         = status
        self.winner_combo: Optional[List[int]]= winner_combo

    def clone(self) -> "GameState":
        """
        Crea una copia superficiale dello stato.

        UTILIZZO: GameLogicService.apply_move() clona prima di modificare.
        copy.copy(self.board): copia la lista di stringhe (stringhe sono immutabili).

        :return: Nuovo GameState con gli stessi valori
        """
        return GameState(
            board=copy.copy(self.board),
            current_turn=self.current_turn,
            status=self.status,
            winner_combo=copy.copy(self.winner_combo),
        )

    def to_dict(self) -> dict:
        """
        Serializza lo stato per la risposta HTTP.

        CHIAMATO DA: GameApplicationService._build_response()

        :return: Dizionario JSON-serializzabile
        """
        return {
            "board":       self.board,
            "currentTurn": self.current_turn.value,   # "X" o "O"
            "status":      self.status.value,          # "ongoing", "human_win", ...
            "winnerCombo": self.winner_combo,          # [0,4,8] o null
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        """
        Factory method: ricostruisce GameState da dizionario (es. da sessione persistita).

        :param data: Dizionario con board, currentTurn, status, winnerCombo
        :return: Istanza GameState ricostruita
        """
        return cls(
            board=data["board"],
            current_turn=Player(data.get("currentTurn", Player.HUMAN.value)),
            status=GameStatus(data.get("status", GameStatus.ONGOING.value)),
            winner_combo=data.get("winnerCombo"),
        )
