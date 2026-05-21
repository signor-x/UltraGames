"""
GameLogicService (Tris) — Regole del gioco e valutazione stato (SRP).

RESPONSABILITÀ (SRP):
  Contiene SOLO la logica di gioco del Tris:
    - apply_move: Applica una mossa e valuta il nuovo stato
    - get_empty_cells: Lista delle celle disponibili
    - _evaluate: Determina lo stato della partita (win/draw/ongoing)
  Non contiene AI (→ AIStrategy) né gestione sessioni (→ GameApplicationService).

SOLID PRINCIPLES:
  - SRP: Solo regole di gioco. Nessuna AI, nessuna persistenza.
  - DIP: GameApplicationService e AIStrategy ricevono GameLogicService
    come dipendenza iniettata dalla factory. Sostituibile con una versione
    diversa (es. per test) senza modificare i consumatori.

PERCORSO CHIAMATA:
  tris_service_factory.get_tris_service()
    → GameApplicationService(logic=GameLogicService(), ...)
  GameApplicationService.human_move()
    → logic.apply_move(state, cell, Player.HUMAN) → nuovo GameState
  AIStrategy.choose_move()
    → logic.get_empty_cells(state.board) → celle disponibili
    → logic.apply_move(state, cell, Player.AI)  → simulazione per Minimax
"""

from typing import Optional, List, Tuple
from tris.models.game_state import GameState, Player, GameStatus


class GameLogicService:
    """
    Valuta lo stato del gioco Tris e applica le mosse.

    METODI PUBBLICI:
      apply_move(state, cell, player) → GameState aggiornato
      get_empty_cells(board) → List[int] celle vuote

    METODI PRIVATI:
      _is_valid_move(state, cell) → bool
      _evaluate(board) → (GameStatus, winner_combo | None)
    """

    def apply_move(self, state: GameState, cell: int, player: Player) -> GameState:
        """
        Applica la mossa del giocatore specificato nella cella indicata.

        FLUSSO:
          1. Valida la mossa (cella in range, vuota, partita in corso)
          2. Clona lo stato (immutabilità: lo stato originale non viene modificato)
          3. Imposta board[cell] = player.value ("X" o "O")
          4. Aggiorna il turno (alternato: HUMAN → AI → HUMAN)
          5. Valuta il nuovo stato (_evaluate)
          6. Restituisce il nuovo stato

        CHIAMATO DA:
          GameApplicationService.human_move() → player=Player.HUMAN
          GameApplicationService._ai_move_internal() → player=Player.AI
          MinimaxAIStrategy._minimax() → player=Player.AI/HUMAN (simulazione)

        :param state: Stato corrente della partita
        :param cell: Indice 0-8 della cella nella griglia
        :param player: Player.HUMAN ("X") o Player.AI ("O")
        :return: Nuovo GameState dopo la mossa
        :raises ValueError: Se la mossa non è valida
        """
        if not self._is_valid_move(state, cell):
            raise ValueError(f"Mossa non valida: cella {cell}")

        # Clone: non modifica lo stato originale (stile funzionale)
        new_state = state.clone()
        new_state.board[cell] = player.value

        # Alterna il turno: dopo HUMAN tocca ad AI e viceversa
        new_state.current_turn = Player.AI if player == Player.HUMAN else Player.HUMAN

        # Valuta se la partita è terminata dopo questa mossa
        new_state.status, new_state.winner_combo = self._evaluate(new_state.board)
        return new_state

    def get_empty_cells(self, board: List[str]) -> List[int]:
        """
        Restituisce gli indici delle celle vuote nella board.

        CHIAMATO DA:
          RandomAIStrategy.choose_move() → sceglie casualmente
          MinimaxAIStrategy.choose_move() → itera per esplorare mosse
          MinimaxAIStrategy._minimax()    → verifica se ci sono mosse

        :param board: Lista di 9 stringhe
        :return: Lista di indici (0-8) dove board[i] == ""
        """
        return [i for i, v in enumerate(board) if v == Player.EMPTY.value]

    def _is_valid_move(self, state: GameState, cell: int) -> bool:
        """
        Verifica la validità di una mossa.

        CONDIZIONI:
          1. cell in [0, 8]
          2. La cella è vuota (board[cell] == "")
          3. La partita è ancora in corso (status == ONGOING)

        :return: True se la mossa è valida
        """
        return (
            0 <= cell <= 8
            and state.board[cell] == Player.EMPTY.value
            and state.status == GameStatus.ONGOING
        )

    def _evaluate(self, board: List[str]) -> Tuple[GameStatus, Optional[List[int]]]:
        """
        Valuta lo stato della board e determina se la partita è terminata.

        LOGICA:
          1. Controlla tutte le 8 WIN_COMBOS
          2. Se una combo ha 3 simboli uguali e non vuoti → vittoria
          3. Se tutte le celle sono occupate (nessuna vittoria) → pareggio
          4. Altrimenti → partita in corso

        CHIAMATO DA: apply_move() dopo ogni mossa.

        :param board: Lista 9 stringhe con lo stato attuale
        :return: (GameStatus, winner_combo) oppure (GameStatus, None)
        """
        for combo in GameState.WIN_COMBOS:
            values = [board[i] for i in combo]
            # Verifica: tutte e 3 le celle uguali E non vuote
            if values[0] != Player.EMPTY.value and len(set(values)) == 1:
                winner = values[0]
                status = GameStatus.HUMAN_WIN if winner == Player.HUMAN.value else GameStatus.AI_WIN
                return status, combo

        # Nessuna vittoria: controlla patta (tutte le celle occupate)
        if all(v != Player.EMPTY.value for v in board):
            return GameStatus.DRAW, None

        return GameStatus.ONGOING, None
