"""
Board — Scacchiera della Dama (SRP).

RESPONSABILITÀ (SRP):
  Rappresenta e gestisce la griglia 8x8 della Dama.
  Fornisce metodi di accesso, conteggio e serializzazione.
  Non contiene logica di movimento (→ MoveGeneratorService).

STRUTTURA INTERNA:
  _grid: Dict[Tuple[int,int], Piece]
  Chiave: (row, col) con row e col in [0,7]
  Valore: Piece (solo le celle occupate sono nel dizionario)

  VANTAGGIO di un dizionario sparso rispetto a una lista 8x8:
    - Iterazione efficiente sui soli pezzi esistenti
    - Nessun valore "None" per le celle vuote
    - O(1) per accesso, inserimento e rimozione per posizione

POSIZIONE INIZIALE (Board.initial()):
  Dama italiana standard: 3 righe di 4 pedine per parte.
    WHITE (giocatore): righe 5-7
    BLACK (AI):        righe 0-2
  I pezzi occupano le caselle scure (somma di riga+colonna dispari).

PERCORSO CHIAMATA:
  GameState.__init__()
    → self.board = Board.initial()  ← posizione di partenza
  GameState.clone()
    → Board(dict(self.board._grid)) ← copia del dizionario
  GameRulesService.apply_move()
    → board._grid.pop(tuple(start))   ← rimuove dal sorgente
    → board._grid[tuple(end)] = piece ← inserisce alla destinazione
  GameApplicationService._response()
    → state.board.to_dict()           ← serializza per HTTP
"""

from typing import Dict, Tuple, Optional
from .piece import Piece, PieceColor, PieceType


class Board:
    """
    Scacchiera 8x8 della Dama, implementata come dizionario sparso.

    Le caselle vuote NON sono nel dizionario (_grid).
    Solo le caselle occupate da un Piece sono presenti come chiavi.
    """

    def __init__(self, grid: Optional[Dict[Tuple[int, int], Piece]] = None):
        """
        :param grid: Dizionario posizione→Piece; se None, crea una board vuota
        """
        self._grid: Dict[Tuple[int, int], Piece] = grid if grid is not None else {}

    @classmethod
    def initial(cls) -> "Board":
        """
        Crea la posizione iniziale standard della Dama italiana.

        POSIZIONE INIZIALE:
          BLACK (AI):    righe 0-2, caselle scure (r+c dispari)
          WHITE (umano): righe 5-7, caselle scure (r+c dispari)
          Righe 3-4: vuote (zone di battaglia)

        CHIAMATO DA: GameState.__init__() quando board=None

        :return: Board con i 24 pezzi nella posizione di partenza
        """
        grid = {}
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1:  # Solo caselle scure (somma dispari)
                    if row < 3:
                        grid[(row, col)] = Piece(color=PieceColor.BLACK)  # Pedine AI
                    elif row > 4:
                        grid[(row, col)] = Piece(color=PieceColor.WHITE)  # Pedine umane
        return cls(grid)

    def count(self, color: PieceColor) -> int:
        """
        Conta il numero totale di pezzi del colore specificato (pedine + dame).

        CHIAMATO DA: GameState.to_dict() → "whiteCount", "blackCount"

        :param color: PieceColor.WHITE o PieceColor.BLACK
        :return: Numero di pezzi del colore
        """
        return sum(1 for p in self._grid.values() if p.color == color)

    def count_kings(self, color: PieceColor) -> int:
        """
        Conta solo le dame (pezzi promossi) del colore specificato.

        CHIAMATO DA: GameState.to_dict() → "whiteKings", "blackKings"

        :param color: PieceColor.WHITE o PieceColor.BLACK
        :return: Numero di dame del colore
        """
        return sum(1 for p in self._grid.values() if p.color == color and p.is_king())

    def to_dict(self) -> list:
        """
        Serializza la board come lista 2D 8x8 per la risposta HTTP.

        FORMATO:
          Lista di 8 liste (righe), ognuna con 8 elementi.
          Ogni elemento è null (cella vuota) o un dict:
            {"color": "white"|"black", "type": "pawn"|"king"}

        CHIAMATO DA: GameState.to_dict() → "board": board.to_dict()

        :return: Lista 8x8 di None o dict pezzo
        """
        result = []
        for row in range(8):
            row_data = []
            for col in range(8):
                piece = self._grid.get((row, col))
                if piece is None:
                    row_data.append(None)
                else:
                    row_data.append({
                        "color":   piece.color.value,
                        "type":    piece.type.value,
                        "id":      piece.id,
                        "is_king": piece.is_king(),
                    })
            result.append(row_data)
        return result
