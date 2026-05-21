"""
tris_views.py — Gestore unificato delle view e della factory per il gioco Tris.

STRUTTURA DEL FILE:
  TrisServiceFactory  → funzione get_tris_service()  (Singleton + lazy init)
  TrisView            → classe gestore con i metodi HTTP del Tris:
                          health()  GET  /tris/health
                          new()     POST /tris/new
                          move()    POST /tris/move
                          reset()   POST /tris/reset

PATTERN SINGLETON + FACTORY con LAZY INITIALIZATION (TrisServiceFactory):
  La variabile modulo _tris_service viene inizializzata a None.
  Al primo accesso, viene costruito il grafo completo di dipendenze e
  memorizzato nel singleton. Le chiamate successive restituiscono la stessa
  istanza, evitando il costo di re-istanziazione a ogni richiesta HTTP.

GRAFO DI DIPENDENZE COSTRUITO:
  GameApplicationService (tris/services/game_application_service.py)
    ├── GameSessionRepository  (tris/repositories/game_session_repository.py)
    │     → Dizionario in-memory {session_id: {state, difficulty}}
    ├── GameLogicService       (tris/services/game_logic_service.py)
    │     → apply_move(), _evaluate(), get_empty_cells()
    └── AIStrategyFactory      (tris/services/ai_strategy.py)
          → Crea RandomAIStrategy o MinimaxAIStrategy

PERCORSO CHIAMATA (URL → metodo):
  ultragames_django/urls.py
    → include("apps.games.urls_tris")        [apps/games/urls_tris.py]
      → TrisView.health_view()   GET  /tris/health
      → TrisView.new_view()      POST /tris/new
      → TrisView.move_view()     POST /tris/move
      → TrisView.reset_view()    POST /tris/reset

SOLID PRINCIPLES:
  - SRP: Ogni metodo gestisce un solo endpoint.
  - DIP: Le view dipendono dall'interfaccia GameApplicationService tramite factory.
  - OCP: Nuovo endpoint = nuovo metodo nella classe, senza modificare gli altri.
"""

import importlib

from django.http import JsonResponse
from django.views import View
from apps.core.action_view import ActionView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from services.container import get_container
from services.auth_helpers import cbv_require_auth
from .mixins import JsonBodyMixin

# ── Factory ───────────────────────────────────────────────────────────────────

# Singleton del servizio Tris, inizializzato a None (lazy).
_tris_service = None


def get_tris_service():
    """
    Restituisce il singleton di GameApplicationService per il Tris.

    PRIMO ACCESSO:
      1. Importa i moduli del dominio tris (import statici diretti)
      2. Istanzia le dipendenze: Repository, LogicService, AIStrategyFactory
      3. Costruisce GameApplicationService con DI (Dependency Injection)
      4. Salva in _tris_service (global)

    ACCESSI SUCCESSIVI: Restituisce il singleton già creato (O(1)).

    :return: Istanza singleton di GameApplicationService per il Tris
    """
    global _tris_service
    if _tris_service is None:
        from tris.repositories.game_session_repository import GameSessionRepository
        from tris.services.game_logic_service import GameLogicService
        from tris.services.ai_strategy import AIStrategyFactory
        from tris.services.game_application_service import GameApplicationService

        _tris_service = GameApplicationService(
            repository=GameSessionRepository(),      # In-memory session store
            logic=GameLogicService(),                # Regole Tris (apply_move, evaluate)
            strategy_factory=AIStrategyFactory(),    # Crea random/minimax AI
        )
    return _tris_service


# ── View gestore ──────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class TrisView(JsonBodyMixin, ActionView, View):
    """
    Gestore unificato delle view per il gioco Tris.

    Raccoglie in un'unica classe tutti gli endpoint del gioco, condividendo
    le dipendenze (JsonBodyMixin, get_tris_service, get_container) senza
    duplicazioni.

    ENDPOINT GESTITI:
      GET  /tris/health → health()   (health check, no auth)
      POST /tris/new    → new()      (nuova partita, JWT richiesto)
      POST /tris/move   → move()     (mossa + risposta AI, JWT richiesto)
      POST /tris/reset  → reset()    (reset partita, JWT richiesto)

    NOTA CSRF:
      @method_decorator(csrf_exempt, name="dispatch") disabilita il CSRF per
      tutti i metodi POST. La protezione è garantita dal JWT HttpOnly + SameSite=Lax.
      Gli health check GET non sono influenzati.
    """

    # ── health ────────────────────────────────────────────────────────────────

    def health(self, request):
        """
        Health check per il servizio Tris.

        ENDPOINT: GET /tris/health
        AUTENTICAZIONE: Non richiesta (usato da load balancer / monitoraggio).
        RISPOSTA (200): {"status": "ok", "game": "tris"}

        PATTERN: Health Check Endpoint (standard nei microservizi e Docker/K8s).
        """
        self.allowed_methods = ["GET"]
        return JsonResponse({"status": "ok", "game": "tris"})

    # ── new ───────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def new(self, request):
        """
        Crea una nuova partita di Tris e restituisce lo stato iniziale.

        ENDPOINT: POST /tris/new
        BODY JSON (opzionale): {"difficulty": "random" | "minimax"}
          "random"  → AI sceglie cella libera a caso
          "minimax" → AI usa Minimax con alpha-beta pruning (imbattibile)
          Default: "random"

        RISPOSTA SUCCESSO (201 Created):
          {
            "sessionId": "<UUID>",
            "difficulty": "random",
            "board": ["", "", "", "", "", "", "", "", ""],  ← 9 celle vuote
            "currentTurn": "X",                            ← X = HUMAN inizia
            "status": "ongoing",
            "winnerCombo": null
          }

        PERCORSO:
          → get_tris_service().new_game(difficulty)
            [tris/services/game_application_service.py]
              → GameSessionRepository.create(difficulty)
              → Restituisce stato iniziale (board vuota 3x3, turno HUMAN)
        """
        self.allowed_methods = ["POST"]
        body = self._parse_body(request)
        result = get_tris_service().new_game(body.get("difficulty", "random"))
        return JsonResponse(result, status=201)

    # ── move ──────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def move(self, request):
        """
        Esegue la mossa del giocatore umano (X) e la risposta dell'AI (O).

        ENDPOINT: POST /tris/move
        BODY JSON: {"sessionId": "<UUID>", "cell": 4}
          cell: indice 0-8 della cella nella griglia 3x3 (row-major)
            [0,1,2]
            [3,4,5]
            [6,7,8]

        RISPOSTA SUCCESSO (200):
          {
            "sessionId": "<UUID>",
            "aiCell": 6,                    ← cella scelta dall'AI (null se partita finita)
            "board": ["X","","","","X","","","O",""],
            "currentTurn": "X",
            "status": "ongoing",            ← "human_win" | "ai_win" | "draw" se finita
            "winnerCombo": null
          }

        RISPOSTA ERRORI:
          400 {"error": "sessionId e cell sono obbligatori"}
          400 {"error": "Non è il turno del giocatore umano."}
          400 {"error": "Mossa non valida: cella 4"}
          404 {"error": "Sessione non trovata: <sid>"}

        GESTIONE FINE PARTITA:
          Se status ∈ {"human_win", "ai_win", "draw"} → record_tris_result() nelle stats.
          L'eccezione DB è catturata silenziosamente: un errore nelle stats
          non deve interrompere la risposta di gioco.

        PERCORSO:
          → get_tris_service().human_move(session_id, cell)
            [tris/services/game_application_service.py]
              → GameLogicService.apply_move(state, cell, Player.HUMAN)
              → AIStrategyFactory.create(difficulty, logic).choose_move(state)
              → GameLogicService.apply_move(state, ai_cell, Player.AI)
              → GameSessionRepository.update(session_id, new_state)
          → stats_repository.record_tris_result(user_id, won, draw)  ← solo se terminata
        self.allowed_methods = ["POST"]
        """
        body       = self._parse_body(request)
        session_id = body.get("sessionId")
        cell       = body.get("cell")

        # cell può essere 0 (falsy!): "cell is None" è il controllo corretto.
        if session_id is None or cell is None:
            return JsonResponse({"error": "sessionId e cell sono obbligatori"}, status=400)

        try:
            # human_move: applica la mossa umana, poi fa rispondere l'AI.
            # int(cell): il JSON potrebbe inviare "cell" come stringa.
            result = get_tris_service().human_move(session_id, int(cell))
        except KeyError as e:
            return JsonResponse({"error": str(e)}, status=404)
        except (PermissionError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=400)

        # Registra il risultato nelle statistiche se la partita è terminata.
        status = result.get("status", "")
        if status in ("human_win", "ai_win", "draw"):
            try:
                get_container().stats_repository.record_tris_result(
                    request.current_user.user_id,
                    won=(status == "human_win"),
                    draw=(status == "draw"),
                )
            except Exception:
                # Errore DB nelle stats: non blocca la risposta di gioco.
                pass

        return JsonResponse(result)

    # ── reset ─────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def reset(self, request):
        """
        Resetta una partita di Tris: elimina la sessione corrente e ne crea una
        nuova con la stessa difficoltà.

        ENDPOINT: POST /tris/reset
        BODY JSON: {"sessionId": "<UUID>"}
        RISPOSTA SUCCESSO (200): Stesso formato di /tris/new (nuovo stato iniziale)
        RISPOSTA ERRORI:
          400 {"error": "sessionId obbligatorio"}
          404 {"error": "Sessione non trovata: <sid>"}

        PERCORSO:
          → get_tris_service().reset_game(session_id)
            [tris/services/game_application_service.py]
              → GameSessionRepository.delete(session_id)
              → GameApplicationService.new_game(difficulty)  ← stessa difficoltà
        """
        self.allowed_methods = ["POST"]
        body = self._parse_body(request)
        sid  = body.get("sessionId")
        if not sid:
            return JsonResponse({"error": "sessionId obbligatorio"}, status=400)
        try:
            return JsonResponse(get_tris_service().reset_game(sid))
        except KeyError as e:
            return JsonResponse({"error": str(e)}, status=404)
