"""
GameApplicationService (Tris) — Orchestrazione use case (SRP).

RESPONSABILITÀ (SRP):
  Coordina i use case del gioco Tris:
    - new_game: Crea sessione, restituisce stato iniziale
    - human_move: Applica mossa umana → risposta AI → aggiorna repository
    - reset_game: Elimina sessione e ricrea con stessa difficoltà

  NON contiene logica di regole (→ GameLogicService) né AI (→ AIStrategy).

SOLID PRINCIPLES:
  - SRP: Solo orchestrazione. Zero logica di gioco.
  - DIP: Dipende da astrazioni iniettate nel costruttore:
      repository → GameSessionRepository
      logic      → GameLogicService
      strategy_factory → AIStrategyFactory
  - LSP: Qualsiasi AIStrategy può essere iniettata senza modificare
    questo servizio (RandomAIStrategy e MinimaxAIStrategy sono intercambiabili).
  - OCP: Aggiungere nuovi use case (es. undo) non richiede modificare quelli
    esistenti.

PERCORSO CHIAMATA:
  apps/games/views/tris_*_view.py
    → get_tris_service()                      [tris_service_factory.py]
      → GameApplicationService.new_game()
        → GameSessionRepository.create()
      → GameApplicationService.human_move()
        → GameLogicService.apply_move(state, cell, Player.HUMAN)
        → AIStrategyFactory.create(difficulty, logic).choose_move(state)
        → GameLogicService.apply_move(state, ai_cell, Player.AI)
        → GameSessionRepository.update(session_id, new_state)
      → GameApplicationService.reset_game()
        → GameSessionRepository.delete(session_id)
        → GameApplicationService.new_game(difficulty)
"""

from tris.models.game_state import GameState, Player, GameStatus
from tris.services.game_logic_service import GameLogicService
from tris.services.ai_strategy import AIStrategyFactory
from tris.repositories.game_session_repository import GameSessionRepository


class GameApplicationService:
    """
    Orchestratore dei use case del gioco Tris.

    DIPENDENZE INIETTATE (DIP):
      repository:       GameSessionRepository → storage in-memory sessioni
      logic:            GameLogicService      → regole di gioco
      strategy_factory: AIStrategyFactory     → crea strategia AI
    """

    def __init__(
        self,
        repository:       GameSessionRepository,
        logic:            GameLogicService,
        strategy_factory: AIStrategyFactory,
    ):
        self._repo    = repository
        self._logic   = logic
        self._factory = strategy_factory

    def new_game(self, difficulty: str) -> dict:
        """
        Crea una nuova partita di Tris.

        FLUSSO:
          1. Repository crea sessione (GameState vuoto, turno HUMAN)
          2. Legge lo stato appena creato
          3. Serializza e restituisce la risposta

        CHIAMATO DA: TrisNewView.post()

        :param difficulty: "random" | "minimax"
        :return: {"sessionId", "difficulty", board, currentTurn, status, winnerCombo}
        """
        session_id = self._repo.create(difficulty)
        session    = self._repo.get(session_id)
        return {
            "sessionId":  session_id,
            "difficulty": difficulty,
            **session["state"].to_dict(),
        }

    def human_move(self, session_id: str, cell: int) -> dict:
        """
        Applica la mossa dell'utente (X) e la risposta dell'AI (O).

        FLUSSO:
          1. Recupera sessione (lancia KeyError se non esiste)
          2. Verifica che sia il turno HUMAN (lancia PermissionError se no)
          3. Applica mossa HUMAN → nuovo stato
          4. Se partita ancora in corso: AI risponde immediatamente
          5. Aggiorna repository con stato finale
          6. Restituisce stato + cella scelta dall'AI

        GUARDIA TURNO:
          PermissionError se current_turn != HUMAN. Catturato da TrisMoveView
          come errore 400.

        CHIAMATO DA: TrisMoveView.post()

        :param session_id: UUID della sessione
        :param cell: Indice 0-8 della cella scelta dall'utente
        :return: Stato aggiornato con aiCell
        :raises KeyError: Se la sessione non esiste
        :raises PermissionError: Se non è il turno dell'umano
        """
        session    = self._get_session(session_id)
        state: GameState = session["state"]

        if state.current_turn != Player.HUMAN:
            raise PermissionError("Non è il turno del giocatore umano.")

        # Applica mossa HUMAN: lancia ValueError se cella non valida
        state = self._logic.apply_move(state, cell, Player.HUMAN)
        self._repo.update(session_id, state)

        # Se la partita è finita dopo la mossa umana, non far rispondere l'AI
        if state.status != GameStatus.ONGOING:
            return self._build_response(session_id, state, ai_cell=None)

        # AI risponde immediatamente
        ai_cell = self._ai_move_internal(session_id, state, session["difficulty"])
        # Rilegge lo stato dal repository (aggiornato da _ai_move_internal)
        state = self._repo.get(session_id)["state"]
        return self._build_response(session_id, state, ai_cell=ai_cell)

    def reset_game(self, session_id: str) -> dict:
        """
        Resetta la partita: elimina la sessione e crea nuova con stessa difficoltà.

        CHIAMATO DA: TrisResetView.post()

        :param session_id: UUID della sessione da resettare
        :return: Stato iniziale della nuova partita
        """
        session    = self._get_session(session_id)
        difficulty = session["difficulty"]
        self._repo.delete(session_id)
        return self.new_game(difficulty)

    # ── HELPERS PRIVATI ────────────────────────────────────────────────────

    def _ai_move_internal(self, session_id: str, state: GameState, difficulty: str) -> int:
        """
        Esegue il turno AI: sceglie cella e applica la mossa.

        FACTORY: AIStrategyFactory.create(difficulty, logic) → AIStrategy
        La strategia scelta dipende da difficulty (random o minimax).

        :return: Indice della cella scelta dall'AI (per includerla nella risposta)
        """
        strategy = self._factory.create(difficulty, self._logic)
        ai_cell  = strategy.choose_move(state)
        new_state = self._logic.apply_move(state, ai_cell, Player.AI)
        self._repo.update(session_id, new_state)
        return ai_cell

    def _get_session(self, session_id: str) -> dict:
        """
        Recupera la sessione o lancia KeyError se non esiste.

        :raises KeyError: Se session_id non è nel repository
        """
        session = self._repo.get(session_id)
        if not session:
            raise KeyError(f"Sessione non trovata: {session_id}")
        return session

    def _build_response(self, session_id: str, state: GameState, ai_cell) -> dict:
        """
        Costruisce il dizionario di risposta standard per le view Tris.

        STRUTTURA: sessionId, aiCell + tutto state.to_dict()
        """
        return {
            "sessionId": session_id,
            "aiCell":    ai_cell,    # int (cella AI) o null se partita finita
            **state.to_dict(),
        }
