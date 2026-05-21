"""
AI Strategy (Tris) — OCP + LSP + DIP.

PATTERN STRATEGY (GoF):
  Interfaccia AIStrategy + due implementazioni (Random, Minimax) + Factory.
  Identico nella struttura a dama/services/ai_strategy.py, ma adattato
  alla logica del Tris (celle 0-8 invece di oggetti Move).

SOLID PRINCIPLES:
  - OCP: Aggiungere nuove strategie (es. "mcts" con Monte Carlo) non
    richiede modificare AIStrategy, GameApplicationService o le view.
  - LSP: RandomAIStrategy e MinimaxAIStrategy sono intercambiabili.
  - DIP: GameApplicationService dipende da AIStrategy (interfaccia astratta),
    non dalle implementazioni concrete.

DIFFERENZE RISPETTO A DAMA:
  - choose_move restituisce int (indice cella) invece di Optional[Move]
  - MinimaxAIStrategy è imbattibile (Tris ha spazio di stati limitato)
  - La funzione euristica è più semplice (win=+10, loss=-10, draw=0)
  - La profondità viene incrementata (depth=0 → foglia) invece di decrementata

PERCORSO CHIAMATA:
  GameApplicationService._ai_move_internal(session_id, state, difficulty)
    → AIStrategyFactory.create(difficulty, logic)  ← questo file
      → RandomAIStrategy(logic) | MinimaxAIStrategy(logic)
    → strategy.choose_move(state) → int (indice cella)
"""

import random
from abc import ABC, abstractmethod
from typing import List
from tris.models.game_state import GameState, Player, GameStatus
from tris.services.game_logic_service import GameLogicService


class AIStrategy(ABC):
    """
    Interfaccia astratta per le strategie AI del Tris (DIP).
    Garantisce LSP: qualsiasi implementazione è usabile dove è attesa AIStrategy.
    """

    @abstractmethod
    def choose_move(self, state: GameState) -> int:
        """
        Sceglie la mossa migliore per l'AI.

        :param state: Stato corrente della partita
        :return: Indice della cella scelta (0-8)
        """
        ...


class RandomAIStrategy(AIStrategy):
    """
    Strategia casuale: sceglie una cella libera a caso.

    UTILIZZO: difficulty="random"
    FORZA: Debole, adatta ai principianti o per varietà.
    """

    def __init__(self, logic: GameLogicService):
        self._logic = logic  # Iniettato dalla factory (DIP)

    def choose_move(self, state: GameState) -> int:
        empty = self._logic.get_empty_cells(state.board)
        if not empty:
            raise ValueError("Nessuna mossa disponibile")
        return random.choice(empty)


class MinimaxAIStrategy(AIStrategy):
    """
    Strategia Minimax con alpha-beta pruning.

    Per il Tris l'albero è piccolo (max 9 mosse) quindi Minimax esplora
    l'intero spazio di stati: l'AI è imbattibile (mai perde, spesso pareggia).

    EURISTICA:
      AI_WIN  → +10 - depth  (vince prima = meglio)
      HUMAN_WIN → depth - 10 (perde prima = peggio, ma è inevitabile)
      DRAW    → 0

    ALPHA-BETA PRUNING:
      Taglia i rami dell'albero inutili, riducendo il numero di nodi esplorati.
      Nel Tris il beneficio è limitato (spazio piccolo), ma migliora le prestazioni
      nei casi con molte mosse iniziali disponibili.
    """

    def __init__(self, logic: GameLogicService):
        self._logic = logic

    def choose_move(self, state: GameState) -> int:
        empty = self._logic.get_empty_cells(state.board)
        if not empty:
            raise ValueError("Nessuna mossa disponibile")

        best_score = float("-inf")
        best_move  = empty[0]

        for cell in empty:
            # Simula: AI gioca in questa cella
            new_state = self._logic.apply_move(state, cell, Player.AI)
            # Valuta con Minimax (turno umano, minimizza)
            score = self._minimax(new_state, depth=0, is_maximizing=False,
                                  alpha=float("-inf"), beta=float("inf"))
            if score > best_score:
                best_score = score
                best_move  = cell

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
        Ricorsione Minimax con alpha-beta pruning per il Tris.

        depth viene INCREMENTATA (misura la profondità della ricerca,
        usata nell'euristica per preferire vittorie più rapide).

        :param state: Nodo corrente dell'albero
        :param depth: Profondità corrente (0 = primo livello sotto la radice)
        :param is_maximizing: True se è il turno AI (massimizza)
        :param alpha: Miglior valore garantito per il massimizzatore
        :param beta: Miglior valore garantito per il minimizzatore
        :return: Punteggio euristico del nodo
        """
        # Casi base: partita terminata
        if state.status == GameStatus.AI_WIN:
            return 10 - depth    # Vittoria AI (preferisce vincere prima)
        if state.status == GameStatus.HUMAN_WIN:
            return depth - 10    # Sconfitta AI (peggio quanto più vicina)
        if state.status == GameStatus.DRAW:
            return 0

        empty = self._logic.get_empty_cells(state.board)

        if is_maximizing:
            # Turno AI: massimizza
            best = float("-inf")
            for cell in empty:
                child = self._logic.apply_move(state, cell, Player.AI)
                score = self._minimax(child, depth + 1, False, alpha, beta)
                best  = max(best, score)
                alpha = max(alpha, best)
                if beta <= alpha:
                    break  # Pruning
            return best
        else:
            # Turno umano: minimizza
            best = float("inf")
            for cell in empty:
                child = self._logic.apply_move(state, cell, Player.HUMAN)
                score = self._minimax(child, depth + 1, True, alpha, beta)
                best  = min(best, score)
                beta  = min(beta, best)
                if beta <= alpha:
                    break  # Pruning
            return best


class AIStrategyFactory:
    """
    Factory per creare la strategia AI corretta (OCP).

    CHIAMATO DA: GameApplicationService._ai_move_internal()

    Per aggiungere "hard" difficulty:
      1. Creare HardStrategy(AIStrategy)
      2. Aggiungere "hard": HardStrategy in _registry
    """

    _registry = {
        "random":  RandomAIStrategy,
        "minimax": MinimaxAIStrategy,
    }

    @classmethod
    def create(cls, difficulty: str, logic: GameLogicService) -> AIStrategy:
        """
        Istanzia la strategia AI per la difficoltà data.

        :param difficulty: "random" o "minimax"
        :param logic: GameLogicService iniettato nella strategia
        :return: Istanza AIStrategy
        :raises ValueError: Se difficulty non è nel registry
        """
        strategy_class = cls._registry.get(difficulty)
        if not strategy_class:
            raise ValueError(
                f"Difficoltà sconosciuta: {difficulty}. "
                f"Usa: {list(cls._registry)}"
            )
        return strategy_class(logic)
