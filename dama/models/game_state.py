"""
GameState — Stato aggregato di una partita di Dama (SRP).

RESPONSABILITÀ (SRP):
  Questo modulo contiene SOLO i dati che descrivono lo stato completo di una
  partita: board, turno corrente, status, contatori. Non contiene logica di
  regole (delegata a GameRulesService) né di AI (delegata ad AIStrategy).

FLUSSO DATI:
  GameApplicationService.new_game()
    → GameSessionRepository.create() → GameState()   ← stato iniziale
  GameApplicationService.human_move()
    → GameRulesService.apply_move(state, move)
        → state.clone()               ← copia immutabile
        → new_state.board = ...       ← aggiorna board
        → new_state.turn = ...        ← cambia turno
        → new_state.status = ...      ← valuta fine partita
    → GameSessionRepository.update_state(sid, new_state)

ATTRIBUTI:
  board (Board)           : Scacchiera 8×8 con i pezzi correnti
  turn (PieceColor)       : WHITE (umano) o BLACK (AI)
  status (GameStatus)     : ongoing / white_wins / black_wins / draw
  move_count (int)        : Numero totale di mosse eseguite
  no_capture_streak (int) : Mosse consecutive senza catture (regola patta a 40)

SOLID PRINCIPLES:
  - SRP: Contiene SOLO lo stato; nessuna logica di business.
  - OCP: Aggiungere nuovi campi di stato non richiede modifiche alle classi
    che lo usano (aggiungere solo to_dict/from_dict se necessario).
"""

from enum import Enum
from .board import Board
from .piece import PieceColor


class GameStatus(str, Enum):
    """
    Enum che rappresenta le possibili condizioni di fine partita.

    Eredita da str per serializzare direttamente come valore stringa
    (es. GameStatus.ONGOING.value == "ongoing", ma GameStatus.ONGOING == "ongoing").
    Utile per la serializzazione JSON in to_dict().
    """
    ONGOING   = "ongoing"
    WHITE_WIN = "white_wins"   # Vince il giocatore umano (white)
    BLACK_WIN = "black_wins"   # Vince l'AI (black)
    DRAW      = "draw"         # Patta (40 mosse senza catture)


class GameState:
    """
    Aggregato che rappresenta lo stato completo di una partita di Dama.

    IMMUTABILITÀ PARZIALE:
      GameState non è frozen (è mutabile), ma GameRulesService usa clone()
      prima di modificarlo, garantendo che lo stato originale rimanga intatto.
      Questo è lo "stile funzionale" applicato a oggetti mutabili.

    CHIAMATO DA:
      GameSessionRepository.create()  → crea GameState() (stato iniziale)
      GameRulesService.apply_move()    → clone() → modifica il clone
      GameApplicationService._response() → to_dict() per la risposta HTTP
    """

    def __init__(
        self,
        board:             Board      = None,
        turn:              PieceColor = PieceColor.WHITE,
        status:            GameStatus = GameStatus.ONGOING,
        move_count:        int        = 0,
        no_capture_streak: int        = 0,
    ):
        """
        :param board: Scacchiera corrente; se None, usa Board.initial() (posizione di partenza)
        :param turn: Colore del giocatore di turno (WHITE=umano inizia sempre)
        :param status: Stato della partita (default ONGOING)
        :param move_count: Contatore mosse totali (per statistiche)
        :param no_capture_streak: Mosse consecutive senza catture (limite patta=40)
        """
        self.board             = board if board is not None else Board.initial()
        self.turn              = turn
        self.status            = status
        self.move_count        = move_count
        self.no_capture_streak = no_capture_streak

    def clone(self) -> "GameState":
        """
        Crea una copia profonda dello stato corrente.

        UTILIZZO (GameRulesService.apply_move):
          new_state = state.clone()  ← copia
          new_state.board = ...      ← modifica la copia
          return new_state           ← stato originale invariato

        Board è clonata come dict(self.board._grid): dizionario copiato
        ma i valori Piece sono immutabili (@dataclass frozen), quindi
        non serve una deep copy ricorsiva.

        :return: Nuovo GameState con stessi valori ma oggetti separati
        """
        return GameState(
            board=Board(dict(self.board._grid)),   # copia il dizionario della griglia
            turn=self.turn,
            status=self.status,
            move_count=self.move_count,
            no_capture_streak=self.no_capture_streak,
        )

    def to_dict(self) -> dict:
        """
        Serializza lo stato per la risposta HTTP JSON.

        CHIAMATO DA:
          GameApplicationService._response() → restituito al client via DamaMove/NewView

        Aggiunge anche contatori pezzi (whiteCount, blackCount, whiteKings, blackKings)
        che il frontend usa per mostrare lo stato visivo della partita.

        :return: Dizionario JSON-serializzabile con lo stato completo
        """
        return {
            "board":       self.board.to_dict(),         # lista 2D 8x8
            "turn":        self.turn.value,               # "white" | "black"
            "status":      self.status.value,             # "ongoing" | "white_wins" | ...
            "moveCount":   self.move_count,
            "noCapStreak": self.no_capture_streak,
            "whiteCount":  self.board.count(PieceColor.WHITE),
            "blackCount":  self.board.count(PieceColor.BLACK),
            "whiteKings":  self.board.count_kings(PieceColor.WHITE),
            "blackKings":  self.board.count_kings(PieceColor.BLACK),
        }
