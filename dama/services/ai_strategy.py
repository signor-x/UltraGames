"""
AI Strategy per la Dama — OCP + LSP + DIP.

PATTERN STRATEGY (GoF):
  Definisce una famiglia di algoritmi (RandomAIStrategy, MinimaxAIStrategy),
  li incapsula e li rende intercambiabili. Il client (GameApplicationService)
  usa l'interfaccia AIStrategy senza sapere quale implementazione sta usando.

SOLID PRINCIPLES APPLICATI:
  - OCP (Open/Closed): Per aggiungere una nuova difficoltà (es. "hard") basta
    creare una nuova classe che implementa AIStrategy e registrarla in
    AIStrategyFactory._registry. Nessuna modifica al codice esistente.
  - LSP (Liskov Substitution): RandomAIStrategy e MinimaxAIStrategy sono
    perfettamente intercambiabili tramite l'interfaccia AIStrategy.
    GameApplicationService._ai_turn() funziona identicamente con entrambe.
  - DIP (Dependency Inversion): GameApplicationService dipende da AIStrategy
    (astrazione), non da RandomAIStrategy o MinimaxAIStrategy (concreti).
    La dipendenza è iniettata dalla factory a runtime.
  - SRP: Ogni classe ha una sola responsabilità:
      - AIStrategy: Definisce l'interfaccia
      - RandomAIStrategy: Sceglie casualmente
      - MinimaxAIStrategy: Sceglie ottimalmente con Minimax
      - AIStrategyFactory: Crea la strategia giusta

PERCORSO CHIAMATA:
  GameApplicationService._ai_turn(sid, state, difficulty)
    → AIStrategyFactory.create(difficulty, rules)  ← questo file
      → RandomAIStrategy(rules) | MinimaxAIStrategy(rules)
    → strategy.choose_move(state) → Optional[Move]
"""

import random
from abc import ABC, abstractmethod
from typing import List, Optional
from ..models.game_state import GameState, GameStatus
from ..models.piece import PieceColor, PieceType
from ..models.move import Move
from .game_rules_service import GameRulesService


# ── INTERFACCIA (DIP) ──────────────────────────────────────────────────────

class AIStrategy(ABC):
    """
    Interfaccia astratta per le strategie AI della Dama (DIP).

    Tutte le implementazioni DEVONO implementare choose_move().
    Garantisce LSP: qualsiasi implementazione è usabile dove è attesa AIStrategy.
    """

    @abstractmethod
    def choose_move(self, state: GameState) -> Optional[Move]:
        """
        Sceglie la mossa migliore per l'AI (BLACK) dato lo stato corrente.

        :param state: Stato corrente della partita (turno BLACK)
        :return: Move scelta, o None se non ci sono mosse disponibili (sconfitta)
        """
        ...


# ── RANDOM STRATEGY ────────────────────────────────────────────────────────

class RandomAIStrategy(AIStrategy):
    """
    Strategia casuale: sceglie una mossa tra quelle legali a caso.

    UTILIZZO: difficulty="random"
    FORZA: Debole, adatta ai principianti.
    COMPLESSITÀ: O(n) dove n = numero mosse legali.
    """

    def __init__(self, rules: GameRulesService):
        # rules iniettato: DIP (non crea GameRulesService internamente)
        self._rules = rules

    def choose_move(self, state: GameState) -> Optional[Move]:
        moves = self._rules.legal_moves(state)
        if not moves:
            return None
        return random.choice(moves)


# ── MINIMAX STRATEGY ───────────────────────────────────────────────────────

class MinimaxAIStrategy(AIStrategy):
    """
    Strategia Minimax con alpha-beta pruning.

    ALGORITMO:
      Minimax: Esplora l'albero delle mosse fino a MAX_DEPTH livelli.
        - Nodi MAX (is_maximizing=True):  AI (BLACK) massimizza il punteggio
        - Nodi MIN (is_maximizing=False): Umano (WHITE) minimizza il punteggio
      Alpha-beta pruning: Taglia rami dell'albero che non influenzeranno
        il risultato, riducendo drasticamente il numero di nodi esplorati.

    EURISTICA DI VALUTAZIONE (_evaluate):
      Per ogni pezzo sulla board:
        BLACK: +5 (pedina) o +10 (dama) + bonus avanzamento (0-1.5) + bonus centro (0-1.05)
        WHITE: -5 (pedina) o -10 (dama) + bonus simmetrico (sottratti)
      Terminali: BLACK_WIN=+10000, WHITE_WIN=-10000, DRAW=0

    UTILIZZO: difficulty="minimax"
    FORZA: Molto forte a profondità 6. Quasi imbattibile.
    COMPLESSITÀ: O(b^(d/2)) con pruning, dove b=fattore di ramificazione, d=profondità
    """

    MAX_DEPTH = 6   # Profondità massima dell'albero Minimax

    def __init__(self, rules: GameRulesService):
        self._rules = rules

    def choose_move(self, state: GameState) -> Optional[Move]:
        """
        Sceglie la mossa che massimizza il punteggio per BLACK (AI).

        FLUSSO:
          1. Genera tutte le mosse legali per BLACK
          2. Per ogni mossa: applica e valuta con _minimax() (minimizzando per WHITE)
          3. Sceglie la mossa con punteggio più alto
        """
        moves = self._rules.legal_moves(state)
        if not moves:
            return None
        if len(moves) == 1:
            return moves[0]  # Ottimizzazione: se c'è solo una mossa, sceglila subito

        best_move  = None
        best_score = float("-inf")
        alpha      = float("-inf")
        beta       = float("+inf")

        for move in moves:
            child = self._rules.apply_move(state, move)
            # Dopo la mossa AI, è il turno WHITE (minimizzatore)
            score = self._minimax(child, self.MAX_DEPTH - 1, False, alpha, beta)
            if score > best_score:
                best_score = score
                best_move  = move
            alpha = max(alpha, best_score)  # Aggiorna il limite inferiore del massimizzatore

        return best_move

    def _minimax(
        self,
        state:         GameState,
        depth:         int,
        is_maximizing: bool,
        alpha:         float,
        beta:          float,
    ) -> float:
        """
        Ricorsione Minimax con alpha-beta pruning.

        CASI BASE:
          - Partita terminata (status != ONGOING): valuta con euristica
          - Profondità 0: valuta con euristica (limite di ricerca)
          - Nessuna mossa disponibile: valuta con euristica

        ALPHA-BETA:
          alpha: Miglior valore garantito per il massimizzatore (BLACK)
          beta:  Miglior valore garantito per il minimizzatore (WHITE)
          Se beta <= alpha: il branch corrente non può migliorare il risultato → pruning

        :param state: Stato del nodo corrente
        :param depth: Profondità rimanente (0 = foglia)
        :param is_maximizing: True se è il turno dell'AI (BLACK)
        :param alpha: Limite inferiore per il massimizzatore
        :param beta: Limite superiore per il minimizzatore
        :return: Punteggio euristico del nodo
        """
        if state.status != GameStatus.ONGOING or depth == 0:
            return self._evaluate(state)

        moves = self._rules.legal_moves(state)
        if not moves:
            return self._evaluate(state)

        if is_maximizing:
            # Turno BLACK (AI): massimizza
            best = float("-inf")
            for move in moves:
                child = self._rules.apply_move(state, move)
                best  = max(best, self._minimax(child, depth - 1, False, alpha, beta))
                alpha = max(alpha, best)
                if beta <= alpha:
                    break  # Pruning: il minimizzatore non sceglierà mai questo branch
            return best
        else:
            # Turno WHITE (umano): minimizza
            best = float("+inf")
            for move in moves:
                child = self._rules.apply_move(state, move)
                best  = min(best, self._minimax(child, depth - 1, True, alpha, beta))
                beta  = min(beta, best)
                if beta <= alpha:
                    break  # Pruning: il massimizzatore non sceglierà mai questo branch
            return best

    def _evaluate(self, state: GameState) -> float:
        """
        Funzione euristica di valutazione dello stato (dal punto di vista di BLACK/AI).

        VALORI TERMINALI:
          BLACK_WIN  →  +10000 (vittoria AI)
          WHITE_WIN  →  -10000 (sconfitta AI)
          DRAW       →  0      (patta)

        VALUTAZIONE NON TERMINALE:
          Per ogni pezzo BLACK: base(5/10) + avanzamento(0-1.5) + centro(0-1.05)
          Per ogni pezzo WHITE: stessa formula ma sottratta dal totale

          Avanzamento (adv): Incentiva BLACK ad avanzare verso la promozione (riga 7)
          Centro (center): Incentiva le pedine a occupare il centro (più mobilità)
        """
        if state.status == GameStatus.BLACK_WIN:
            return 10000.0
        if state.status == GameStatus.WHITE_WIN:
            return -10000.0
        if state.status == GameStatus.DRAW:
            return 0.0

        score = 0.0
        board = state.board

        for (row, col), piece in board._grid.items():
            if piece.color == PieceColor.BLACK:
                base   = 10.0 if piece.is_king() else 5.0
                adv    = row / 7.0 * 1.5             # Avanzamento verso riga 7 (promozione BLACK)
                center = (3.5 - abs(col - 3.5)) * 0.3  # Bonus posizione centrale
                score += base + adv + center
            else:  # WHITE
                base   = 10.0 if piece.is_king() else 5.0
                adv    = (7 - row) / 7.0 * 1.5      # Avanzamento verso riga 0 (promozione WHITE)
                center = (3.5 - abs(col - 3.5)) * 0.3
                score -= base + adv + center         # Sottratto: WHITE è l'avversario

        return score


# ── FACTORY (OCP) ─────────────────────────────────────────────────────────

class AIStrategyFactory:
    """
    Factory per creare la strategia AI corretta in base alla difficoltà.

    OCP: Per aggiungere una nuova strategia (es. "hard" con depth=9):
      1. Creare una nuova classe HardMinimaxAIStrategy(AIStrategy)
      2. Aggiungere "hard": HardMinimaxAIStrategy in _registry
      NESSUNA altra modifica richiesta.

    CHIAMATO DA: GameApplicationService._ai_turn()
    """

    # Registry: mappa difficoltà → classe strategia
    _registry = {
        "random":  RandomAIStrategy,
        "minimax": MinimaxAIStrategy,
    }

    @classmethod
    def create(cls, difficulty: str, rules: GameRulesService) -> AIStrategy:
        """
        Istanzia e restituisce la strategia AI per la difficoltà specificata.

        :param difficulty: "random" o "minimax"
        :param rules: GameRulesService iniettato nella strategia
        :return: Istanza AIStrategy pronta all'uso
        :raises ValueError: Se la difficoltà non è nel registry
        """
        klass = cls._registry.get(difficulty)
        if not klass:
            raise ValueError(
                f"Difficoltà sconosciuta: {difficulty}. "
                f"Opzioni: {list(cls._registry)}"
            )
        return klass(rules)
