"""
MoveGeneratorService (Dama) — Generazione delle mosse legali (SRP).

RESPONSABILITÀ (SRP):
  Genera SOLO le mosse legali per la Dama italiana:
    - generate_simple_moves: Spostamenti senza cattura
    - generate_captures:     Catture singole e multiple (rafla)

  Non applica le mosse (→ GameRulesService.apply_move), non valuta
  lo stato (→ GameRulesService._evaluate), non sceglie la mossa AI.

REGOLE IMPLEMENTATE:
  PEDINA (is_king=False):
    - Muove solo in avanti (WHITE verso riga 0, BLACK verso riga 7)
    - Cattura in diagonale (avanti E indietro, come da regole italiane)
    - Può fare rafla (più catture consecutive)

  DAMA (is_king=True):
    - Muove di qualsiasi numero di caselle diagonalmente (volo)
    - Cattura a qualsiasi distanza
    - Può fare rafla

SOLID PRINCIPLES:
  - SRP: Solo generazione mosse. Iniettata in GameRulesService.
  - DIP: GameRulesService riceve MoveGeneratorService come dipendenza.

PERCORSO CHIAMATA:
  dama_service_factory.get_dama_service()
    → move_gen = MoveGeneratorService()
    → GameApplicationService(rules=GameRulesService(move_gen), ...)
  GameRulesService.legal_moves(state)
    → move_gen.generate_captures(board, turn)
    → move_gen.generate_simple_moves(board, turn)
"""

from typing import List
from ..models.piece import PieceColor, PieceType
from ..models.move import Move
from ..models.board import Board


class MoveGeneratorService:
    """
    Generatore di mosse legali per la Dama italiana.

    Tutti i metodi sono puri (no side effects): ricevono board e turn,
    restituiscono lista di Move senza modificare nulla.
    """

    def generate_simple_moves(self, board: Board, turn: PieceColor) -> List[Move]:
        """
        Genera tutte le mosse semplici (senza cattura) per il giocatore di turno.

        CHIAMATO DA: GameRulesService.legal_moves() quando non ci sono catture.

        DIREZIONI PEDINA:
          WHITE: verso riga 0 → direzione = -1
          BLACK: verso riga 7 → direzione = +1
          La dama può muoversi in entrambe le direzioni.

        :param board: Scacchiera corrente
        :param turn: PieceColor.WHITE o PieceColor.BLACK
        :return: Lista di oggetti Move (spostamenti semplici disponibili)
        """
        moves = []
        direction = -1 if turn == PieceColor.WHITE else 1

        for (r, c), piece in board._grid.items():
            if piece.color != turn:
                continue

            if piece.is_king():
                # Dama: volo in tutte e 4 le direzioni diagonali
                for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    nr, nc = r + dr, c + dc
                    while 0 <= nr <= 7 and 0 <= nc <= 7:
                        if (nr, nc) in board._grid:
                            break  # Ostacolo: interrompe il volo
                        moves.append(Move(path=[[r, c], [nr, nc]], captures=[]))
                        nr += dr
                        nc += dc
            else:
                # Pedina: solo avanti (direzione specifica del colore)
                for dc in [-1, 1]:
                    nr, nc = r + direction, c + dc
                    if 0 <= nr <= 7 and 0 <= nc <= 7 and (nr, nc) not in board._grid:
                        moves.append(Move(path=[[r, c], [nr, nc]], captures=[]))

        return moves

    def generate_captures(self, board: Board, turn: PieceColor) -> List[Move]:
        """
        Genera tutte le catture disponibili (inclusa la rafla) per il turno corrente.

        RAFLA (cattura multipla):
          Una pedina/dama può continuare a catturare nella stessa mossa
          finché ci sono pezzi avversari adiacenti catturabili.
          La rafla è obbligatoria se disponibile (ma gestita da GameRulesService
          tramite obbligo di cattura: se ci sono catture, solo quelle sono legali).

        ALGORITMO DFS:
          _find_captures usa una ricerca in profondità per trovare
          tutte le sequenze di cattura possibili partendo da ogni pezzo.

        :param board: Scacchiera corrente
        :param turn: PieceColor.WHITE o PieceColor.BLACK
        :return: Lista di Move (con captures non vuoto), può essere vuota
        """
        all_captures = []

        for (r, c), piece in board._grid.items():
            if piece.color != turn:
                continue
            # DFS da ogni pezzo del giocatore di turno
            self._find_captures(
                board, r, c, piece,
                path=[[r, c]], captured=set(),
                result=all_captures,
            )

        return all_captures

    def _find_captures(self, board, r, c, piece, path, captured, result):
        """
        DFS ricorsivo per trovare tutte le sequenze di cattura.

        FLUSSO:
          1. Per ogni direzione diagonale:
             a. Cerca un pezzo avversario adiacente (o a distanza per le dame)
             b. Verifica che la casella di atterraggio sia libera
             c. Verifica che il pezzo non sia già stato catturato in questa sequenza
          2. Se trova una cattura valida:
             a. Aggiunge il pezzo catturato a `captured`
             b. Aggiunge la posizione di atterraggio a `path`
             c. Ricorre per cercare ulteriori catture
             d. Se non ci sono ulteriori catture: aggiunge la mossa a `result`

        PARAMETRI:
          board:    Scacchiera corrente
          r, c:     Posizione corrente del pezzo
          piece:    Pezzo che sta catturando
          path:     Sequenza di posizioni (partenza + tutte le atterrissate)
          captured: Set di posizioni già catturate in questa sequenza (no doppia cattura)
          result:   Lista da cui aggiungere i Move completi

        :param board: Board corrente
        :param r, c: Riga e colonna correnti
        :param piece: Pezzo che sta effettuando la cattura
        :param path: Percorso corrente (lista di [r,c])
        :param captured: Set di tuple (r,c) dei pezzi già catturati in questa sequenza
        :param result: Lista di Move risultanti da popolare
        """
        found_any = False
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

        for dr, dc in directions:
            if piece.is_king():
                # Dama: cerca avversario a qualsiasi distanza, poi atterra oltre
                dist = 1
                enemy_pos = None
                while True:
                    er, ec = r + dr * dist, c + dc * dist
                    if not (0 <= er <= 7 and 0 <= ec <= 7):
                        break
                    if (er, ec) in board._grid:
                        if board._grid[(er, ec)].color == piece.color:
                            break   # Pezzo amico: blocca la visuale
                        if (er, ec) in captured:
                            break   # Già catturato in questa sequenza
                        enemy_pos = (er, ec)
                        break
                    dist += 1

                if enemy_pos is None:
                    continue

                # Atterraggio: qualsiasi casella oltre il nemico
                land_dist = dist + 1
                while True:
                    lr, lc = r + dr * land_dist, c + dc * land_dist
                    if not (0 <= lr <= 7 and 0 <= lc <= 7):
                        break
                    if (lr, lc) in board._grid:
                        break   # Casella occupata: non si può atterrare

                    new_captured = captured | {enemy_pos}
                    new_path     = path + [[lr, lc]]
                    found_any    = True

                    # Ricorre per cercare altre catture dalla nuova posizione
                    prev_len = len(result)
                    self._find_captures(board, lr, lc, piece, new_path, new_captured, result)
                    if len(result) == prev_len:
                        # Nessuna cattura ulteriore trovata: aggiunge la mossa corrente
                        result.append(Move(
                            path=new_path,
                            captures=[list(p) for p in new_captured],
                        ))
                    land_dist += 1

            else:
                # Pedina: cattura una sola casella in diagonale, atterraggio fisso
                er, ec = r + dr, c + dc        # Posizione del nemico
                lr, lc = r + dr * 2, c + dc * 2  # Posizione di atterraggio

                if not (0 <= er <= 7 and 0 <= ec <= 7 and 0 <= lr <= 7 and 0 <= lc <= 7):
                    continue
                if (er, ec) not in board._grid:
                    continue   # Nessun pezzo da catturare
                if board._grid[(er, ec)].color == piece.color:
                    continue   # Pezzo amico: non catturabile
                if (er, ec) in captured:
                    continue   # Già catturato in questa sequenza
                if (lr, lc) in board._grid and (lr, lc) not in captured:
                    continue   # Casella di atterraggio occupata

                new_captured = captured | {(er, ec)}
                new_path     = path + [[lr, lc]]
                found_any    = True

                prev_len = len(result)
                self._find_captures(board, lr, lc, piece, new_path, new_captured, result)
                if len(result) == prev_len:
                    result.append(Move(
                        path=new_path,
                        captures=[list(p) for p in new_captured],
                    ))

        return found_any
