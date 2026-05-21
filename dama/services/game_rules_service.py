"""
GameRulesService (Dama) — Regole di gioco, applicazione mosse, valutazione stato (SRP).

RESPONSABILITÀ (SRP):
  Contiene SOLO la logica delle regole della Dama italiana:
    - legal_moves:  Genera tutte le mosse legali per il giocatore di turno
    - apply_move:   Applica una mossa e restituisce il nuovo stato
    - _evaluate:    Determina il risultato della partita dopo una mossa

  NON contiene AI (→ AIStrategy), persistenza (→ GameSessionRepository)
  né use case (→ GameApplicationService).

REGOLE DAMA ITALIANA IMPLEMENTATE:
  1. Obbligo di cattura: se esistono catture disponibili, solo quelle sono legali
  2. Rafla (cattura multipla): una pedina può catturare più pezzi in sequenza
  3. Promozione a dama: una pedina che raggiunge l'ultima riga diventa dama
  4. Volo della dama: la dama può muoversi di più caselle diagonalmente
  5. Patta a 40 mosse: 40 mosse consecutive senza catture → draw

SOLID PRINCIPLES:
  - SRP: Solo regole e valutazione. La strategia AI è in AIStrategy.
  - DIP: GameApplicationService e AIStrategy ricevono GameRulesService
    come dipendenza iniettata. Sostituibile con una variante per test.
  - OCP: Aggiungere nuove regole (es. limite tempo) non richiede
    modificare i metodi esistenti (si aggiunge _evaluate_time(), etc.).

PERCORSO CHIAMATA:
  dama_service_factory.get_dama_service()
    → GameApplicationService(rules=GameRulesService(move_gen), ...)
  GameApplicationService.new_game()
    → rules.legal_moves(state) → lista mosse per il turno iniziale
  GameApplicationService.human_move()
    → rules.apply_move(state, move) → nuovo GameState
    → rules.legal_moves(new_state) → mosse per il prossimo turno
  AIStrategy.choose_move()
    → rules.legal_moves(state) → mosse legali per la simulazione
    → rules.apply_move(state, move) → simulazione per Minimax
"""

from ..models.game_state import GameState, GameStatus
from ..models.piece import PieceColor, PieceType
from ..models.move import Move
from .move_generator_service import MoveGeneratorService

# Limite patta: 40 mosse consecutive senza catture → DRAW
_NO_CAPTURE_DRAW_LIMIT = 40


class GameRulesService:
    """
    Applica le regole della Dama italiana e valuta lo stato della partita.

    DIPENDENZA INIETTATA (DIP):
      move_generator: MoveGeneratorService
        Genera le mosse possibili (catture e spostamenti semplici).
        Iniettato nel costruttore → sostituibile con mock nei test.
    """

    def __init__(self, move_generator: MoveGeneratorService):
        """
        :param move_generator: Servizio per la generazione delle mosse legali
        """
        self._gen = move_generator

    def legal_moves(self, state: GameState) -> list:
        """
        Restituisce la lista delle mosse legali per il giocatore di turno.

        REGOLA OBBLIGO DI CATTURA:
          Se esistono catture disponibili, SOLO le catture sono legali.
          Le mosse semplici non sono ammesse quando è possibile catturare.
          Questo è il punto centrale delle regole della Dama italiana.

        FLUSSO:
          1. Genera tutte le catture possibili per il giocatore di turno
          2. Se ci sono catture → restituisce SOLO quelle (obbligo di cattura)
          3. Se non ci sono catture → genera e restituisce mosse semplici

        CHIAMATO DA:
          GameApplicationService.new_game()        → mosse iniziali per WHITE
          GameApplicationService.human_move()      → mosse dopo ogni turno
          AIStrategy.choose_move()                 → mosse disponibili per AI
          MinimaxAIStrategy._minimax()             → esplora albero delle mosse

        :param state: Stato corrente (include turn, board)
        :return: Lista di oggetti Move (può essere vuota se il giocatore ha perso)
        """
        captures = self._gen.generate_captures(state.board, state.turn)
        if captures:
            return captures    # Obbligo di cattura: solo le catture sono legali
        return self._gen.generate_simple_moves(state.board, state.turn)

    def apply_move(self, state: GameState, move: Move) -> GameState:
        """
        Applica una mossa e restituisce il nuovo stato della partita.

        FLUSSO:
          1. Clona lo stato (immutabilità: lo stato originale non viene modificato)
          2. Muove il pezzo dalla posizione iniziale alla finale (path[-1])
          3. Rimuove i pezzi catturati dalla board
          4. Verifica promozione a dama (pedina raggiunge l'ultima riga)
          5. Aggiorna contatori (move_count, no_capture_streak)
          6. Cambia il turno (WHITE ↔ BLACK)
          7. Valuta la fine partita (_evaluate)
          8. Restituisce il nuovo stato

        PROMOZIONE:
          WHITE: la pedina viene promossa quando raggiunge riga 0
          BLACK: la pedina viene promossa quando raggiunge riga 7
          La dama (is_king=True) può muoversi di più caselle diagonalmente.

        CONTATORE PATTA:
          no_capture_streak: Incrementato se nessuna cattura, azzerato se c'è una cattura.
          Dopo 40 mosse senza catture → DRAW.

        CHIAMATO DA:
          GameApplicationService.human_move() → applica mossa umana
          GameApplicationService._ai_turn()   → applica mossa AI
          MinimaxAIStrategy._minimax()         → simulazione mosse per Minimax

        :param state: Stato corrente (non modificato)
        :param move: Mossa da applicare (path di coordinate + catture)
        :return: Nuovo GameState con lo stato aggiornato
        """
        new_state = state.clone()
        board     = new_state.board

        start = move.path[0]   # Posizione iniziale del pezzo
        end   = move.path[-1]  # Posizione finale del pezzo

        # Sposta il pezzo dalla posizione iniziale a quella finale
        piece             = board._grid.pop(tuple(start))
        board._grid[tuple(end)] = piece

        # Rimuove i pezzi catturati dalla board
        for cap in move.captures:
            board._grid.pop(tuple(cap), None)

        # Verifica promozione a dama
        if not piece.is_king():
            if piece.color == PieceColor.WHITE and end[0] == 0:
                board._grid[tuple(end)] = piece.promote()   # WHITE arriva a riga 0
            elif piece.color == PieceColor.BLACK and end[0] == 7:
                board._grid[tuple(end)] = piece.promote()   # BLACK arriva a riga 7

        # Aggiorna contatori
        new_state.move_count += 1
        if move.captures:
            new_state.no_capture_streak = 0    # Cattura → azzera streak patta
        else:
            new_state.no_capture_streak += 1   # No cattura → incrementa streak

        # Cambia turno: WHITE → BLACK, BLACK → WHITE
        new_state.turn = (
            PieceColor.BLACK if state.turn == PieceColor.WHITE else PieceColor.WHITE
        )

        # Valuta la fine partita
        new_state.status = self._evaluate(new_state)
        return new_state

    def _evaluate(self, state: GameState) -> GameStatus:
        """
        Valuta se la partita è terminata dopo l'ultima mossa.

        CASI DI FINE PARTITA:
          1. DRAW: no_capture_streak >= _NO_CAPTURE_DRAW_LIMIT (40 mosse)
          2. SCONFITTA: Il giocatore di turno non ha mosse legali disponibili
             (i suoi pezzi sono stati catturati tutti o sono bloccati)
          3. ONGOING: Ci sono ancora mosse disponibili

        NOTA: Il vincitore è determinato dal giocatore che NON ha mosse.
          Se BLACK non ha mosse → WHITE vince (WHITE_WIN)
          Se WHITE non ha mosse → BLACK vince (BLACK_WIN)

        :param state: Stato dopo l'ultima mossa (turno già cambiato)
        :return: GameStatus (ONGOING, WHITE_WIN, BLACK_WIN, DRAW)
        """
        # Patta per 40 mosse senza catture
        if state.no_capture_streak >= _NO_CAPTURE_DRAW_LIMIT:
            return GameStatus.DRAW

        # Controlla se il giocatore di turno ha mosse disponibili
        available = self.legal_moves(state)
        if not available:
            # Nessuna mossa → il giocatore di turno ha perso
            if state.turn == PieceColor.BLACK:
                return GameStatus.WHITE_WIN    # BLACK non ha mosse → WHITE vince
            else:
                return GameStatus.BLACK_WIN    # WHITE non ha mosse → BLACK vince

        return GameStatus.ONGOING