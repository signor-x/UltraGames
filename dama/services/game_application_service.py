"""
GameApplicationService (Dama) — Orchestrazione dei use case (SRP).

RESPONSABILITÀ (SRP):
  Coordina i use case del gioco Dama:
    - new_game: Crea sessione e restituisce stato iniziale
    - get_legal_moves: Calcola mosse disponibili
    - human_move: Applica mossa umana + risposta AI + verifica fine partita
    - reset_game: Elimina sessione e crea nuova

  NON contiene logica di regole (→ GameRulesService) né AI (→ AIStrategy).

SOLID PRINCIPLES:
  - SRP: Coordina use case senza logica di gioco.
  - DIP: Dipende da astrazioni (GameSessionRepository, GameRulesService,
    AIStrategyFactory) iniettate nel costruttore dalla factory.
    Nessuna dipendenza su implementazioni concrete.
  - OCP: Per aggiungere nuovi use case (es. undo_move) si aggiunge un
    metodo senza modificare quelli esistenti.
  - LSP: Qualsiasi AIStrategy (Random, Minimax) è intercambiabile
    senza modificare questo servizio.

PERCORSO CHIAMATA:
  apps/games/views/dama_*_view.py
    → get_dama_service()                    [dama_service_factory.py]
      → GameApplicationService.new_game() / human_move() / reset_game()
        → GameSessionRepository.*()         [dama/repositories/]
        → GameRulesService.*()              [dama/services/game_rules_service.py]
        → AIStrategyFactory.create().*()   [dama/services/ai_strategy.py]
"""

from ..models.game_state import GameState, GameStatus
from ..models.piece import PieceColor
from ..models.move import Move
from .game_rules_service import GameRulesService
from .ai_strategy import AIStrategyFactory
from ..repositories.game_session_repository import GameSessionRepository


class GameApplicationService:
    """
    Orchestratore dei use case del gioco Dama.

    DIPENDENZE INIETTATE (DIP):
      repository:       GameSessionRepository  → storage in-memory sessioni
      rules:            GameRulesService        → applica mosse, valuta stato
      strategy_factory: AIStrategyFactory       → crea strategia AI per turno
    """

    def __init__(
        self,
        repository:       GameSessionRepository,
        rules:            GameRulesService,
        strategy_factory: AIStrategyFactory,
    ):
        """
        :param repository: Repository per persistenza sessioni in-memory
        :param rules: Servizio con le regole di gioco (applica mosse, valuta)
        :param strategy_factory: Factory per creare la strategia AI corretta
        """
        self._repo    = repository
        self._rules   = rules
        self._factory = strategy_factory

    # ── USE CASES ──────────────────────────────────────────────────────────

    def new_game(self, difficulty: str) -> dict:
        """
        Crea una nuova partita di Dama e restituisce lo stato iniziale.

        FLUSSO:
          1. Repository crea sessione in-memory → session_id (UUID)
          2. Legge lo stato iniziale (Board.initial(), turno WHITE)
          3. Calcola mosse legali per il primo turno (WHITE/umano)
          4. Serializza e restituisce la risposta

        CHIAMATO DA: DamaNewView.post()

        :param difficulty: "random" | "minimax"
        :return: Dizionario con sessionId, stato board, mosse legali, etc.
        """
        sid   = self._repo.create(difficulty)
        state = self._repo.get(sid)["state"]
        moves = self._rules.legal_moves(state)
        return self._response(sid, state, difficulty, moves, ai_move=None)

    def get_legal_moves(self, sid: str) -> dict:
        """
        Restituisce le mosse legali per il turno corrente.

        CHIAMATO DA: DamaMovesView.get()

        :param sid: UUID della sessione
        :return: {"sessionId", "legalMoves": [...], "turn": "white"|"black"}
        :raises KeyError: Se la sessione non esiste
        """
        session = self._require(sid)
        state   = session["state"]
        moves   = self._rules.legal_moves(state)
        return {
            "sessionId":  sid,
            "legalMoves": [m.to_dict() for m in moves],
            "turn":       state.turn.value,
        }

    def human_move(self, sid: str, move_dict: dict) -> dict:
        """
        Applica la mossa del giocatore umano (WHITE) e fa rispondere l'AI.

        FLUSSO:
          1. Recupera sessione e verifica stato (ongoing, turno WHITE)
          2. Converte move_dict → Move e verifica che sia legale
          3. Applica mossa umana → nuovo stato
          4. Se ancora in gioco: AI sceglie e applica la sua mossa
          5. Aggiorna il repository con lo stato finale
          6. Calcola mosse legali per il prossimo turno umano
          7. Serializza e restituisce la risposta

        GUARDIE:
          - Partita già terminata → restituisce errore (no eccezione)
          - Turno non WHITE → restituisce errore
          - Mossa non legale → restituisce errore

        CHIAMATO DA: DamaMoveView.post()

        :param sid: UUID della sessione
        :param move_dict: Dizionario {"path": [...], "captures": [...]}
        :return: Stato aggiornato con aiMove incluso
        """
        session    = self._require(sid)
        state      = session["state"]
        difficulty = session["difficulty"]

        # Guardie: verifica pre-condizioni prima di modificare lo stato
        if state.status != GameStatus.ONGOING:
            return {"error": "Partita già terminata.", "sessionId": sid}
        if state.turn != PieceColor.WHITE:
            return {"error": "Non è il tuo turno.", "sessionId": sid}

        # Converte il dict JSON in un oggetto Move e verifica legalità
        move = Move.from_dict(move_dict)
        if not self._is_legal(state, move):
            return {"error": "Mossa non legale.", "sessionId": sid}

        # Applica la mossa umana: GameRulesService restituisce nuovo GameState
        state = self._rules.apply_move(state, move)
        self._repo.update_state(sid, state)

        # AI risponde solo se la partita è ancora in corso
        ai_move = None
        if state.status == GameStatus.ONGOING:
            ai_move = self._ai_turn(sid, state, difficulty)
            state   = self._repo.get(sid)["state"]  # rilegge stato dopo mossa AI

        # Mosse legali per il prossimo turno (umano); vuote se partita finita
        legal = self._rules.legal_moves(state) if state.status == GameStatus.ONGOING else []
        return self._response(sid, state, difficulty, legal, ai_move)

    def reset_game(self, sid: str) -> dict:
        """
        Resetta la partita: elimina la sessione e ne crea una nuova con stessa difficoltà.

        CHIAMATO DA: DamaResetView.post()

        :param sid: UUID della sessione da resettare
        :return: Stato iniziale della nuova partita (stesso formato di new_game)
        """
        session    = self._require(sid)
        difficulty = session["difficulty"]
        self._repo.delete(sid)
        return self.new_game(difficulty)  # Riusa new_game con stessa difficoltà

    # ── HELPERS PRIVATI ────────────────────────────────────────────────────

    def _ai_turn(self, sid: str, state: GameState, difficulty: str) -> dict:
        """
        Esegue il turno dell'AI: sceglie una mossa e la applica.

        FACTORY PATTERN:
          AIStrategyFactory.create(difficulty, rules) → AIStrategy
          La factory decide quale implementazione creare (Random o Minimax).

        :param sid: UUID della sessione (per aggiornare il repository)
        :param state: Stato corrente (turno BLACK/AI)
        :param difficulty: "random" | "minimax"
        :return: Dizionario mossa AI serializzata, o None se nessuna mossa disponibile
        """
        strategy = self._factory.create(difficulty, self._rules)
        move     = strategy.choose_move(state)
        if move is None:
            return None
        new_state = self._rules.apply_move(state, move)
        self._repo.update_state(sid, new_state)
        return move.to_dict()

    def _require(self, sid: str) -> dict:
        """
        Recupera la sessione o lancia KeyError se non esiste.

        :raises KeyError: Se la sessione non è nel repository
        """
        session = self._repo.get(sid)
        if not session:
            raise KeyError(f"Sessione non trovata: {sid}")
        return session

    def _is_legal(self, state: GameState, move: Move) -> bool:
        """
        Verifica che la mossa proposta sia tra quelle legali.

        Confronta path E captures per garantire che la mossa completa sia valida
        (non solo la destinazione, ma anche le catture intermedie).

        :param state: Stato corrente
        :param move: Mossa da verificare
        :return: True se la mossa è nella lista delle mosse legali
        """
        legal = self._rules.legal_moves(state)
        for m in legal:
            if m.path == move.path and m.captures == move.captures:
                return True
        return False

    def _response(self, sid: str, state: GameState, difficulty: str, moves, ai_move) -> dict:
        """
        Costruisce il dizionario di risposta standard per le view Dama.

        STRUTTURA RISPOSTA:
          sessionId, difficulty, aiMove, legalMoves + tutto state.to_dict()
          (board, turn, status, moveCount, noCapStreak, whiteCount, etc.)
        """
        return {
            "sessionId":  sid,
            "difficulty": difficulty,
            "aiMove":     ai_move,
            "legalMoves": [m.to_dict() for m in moves],
            **state.to_dict(),   # Unpacking: aggiunge tutti i campi dello stato
        }
