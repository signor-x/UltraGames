"""
dama_views.py — Gestore unificato delle view e della factory per il gioco Dama.

STRUTTURA DEL FILE:
  get_dama_service()  → Factory Singleton con lazy initialization via importlib
  DamaView            → classe gestore con i metodi HTTP della Dama:
                          health()  GET  /dama/health
                          new()     POST /dama/new
                          moves()   GET  /dama/moves
                          move()    POST /dama/move
                          reset()   POST /dama/reset

PATTERN SINGLETON + FACTORY con LAZY INITIALIZATION (get_dama_service):
  La variabile modulo _dama_service viene inizializzata a None.
  Al primo accesso, i moduli dama.* vengono importati tramite importlib
  (lazy import): questo evita problemi di importazione circolare e permette
  a Django di avviarsi completamente prima che il codice del gioco venga
  caricato (importazione on-demand).

GRAFO DI DIPENDENZE COSTRUITO:
  GameApplicationService (dama/services/game_application_service.py)
    ├── GameSessionRepository  (dama/repositories/game_session_repository.py)
    │     → Dizionario in-memory {session_id: {state, difficulty}}
    ├── GameRulesService       (dama/services/game_rules_service.py)
    │     └── MoveGeneratorService (dama/services/move_generator_service.py)
    │           → Genera mosse legali (catture, mosse semplici, volo delle dame)
    └── AIStrategyFactory      (dama/services/ai_strategy.py)
          → Crea RandomAIStrategy o MinimaxAIStrategy

PERCORSO CHIAMATA (URL → metodo):
  ultragames_django/urls.py
    → include("apps.games.urls_dama")        [apps/games/urls_dama.py]
      → DamaView.health_view()   GET  /dama/health
      → DamaView.new_view()      POST /dama/new
      → DamaView.moves_view()    GET  /dama/moves
      → DamaView.move_view()     POST /dama/move
      → DamaView.reset_view()    POST /dama/reset

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

# Singleton del servizio Dama, inizializzato a None (lazy).
_dama_service = None


def get_dama_service():
    """
    Restituisce il singleton di GameApplicationService per la Dama.

    FLUSSO PRIMA CHIAMATA:
      1. _dama_service è None → entra nel blocco if
      2. Importa i moduli via importlib (lazy import, evita circular import)
      3. Istanzia MoveGeneratorService
      4. Costruisce GameApplicationService con tutte le dipendenze iniettate (DIP)
      5. Salva l'istanza in _dama_service (global)

    FLUSSO CHIAMATE SUCCESSIVE:
      _dama_service non è None → restituisce direttamente il singleton (O(1))

    :return: Istanza singleton di GameApplicationService per la Dama
    """
    global _dama_service
    if _dama_service is None:
        # Importazione lazy dei moduli del dominio Dama tramite importlib.
        # Equivale a import statici, ma eseguita solo al primo utilizzo.
        repo_mod     = importlib.import_module("dama.repositories.game_session_repository")
        rules_mod    = importlib.import_module("dama.services.game_rules_service")
        move_gen_mod = importlib.import_module("dama.services.move_generator_service")
        strategy_mod = importlib.import_module("dama.services.ai_strategy")
        svc_mod      = importlib.import_module("dama.services.game_application_service")

        # MoveGeneratorService: genera mosse legali (semplici + catture/rafla)
        move_gen = move_gen_mod.MoveGeneratorService()

        # GameApplicationService: orchestratore use-case con DI
        _dama_service = svc_mod.GameApplicationService(
            repository=repo_mod.GameSessionRepository(),       # In-memory session store
            rules=rules_mod.GameRulesService(move_gen),        # Regole + move gen iniettato
            strategy_factory=strategy_mod.AIStrategyFactory(), # Crea random/minimax AI
        )
    return _dama_service


# ── View gestore ──────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class DamaView(JsonBodyMixin, ActionView, View):
    """
    Gestore unificato delle view per il gioco Dama.

    Raccoglie in un'unica classe tutti gli endpoint del gioco, condividendo
    le dipendenze (JsonBodyMixin, get_dama_service, get_container) senza
    duplicazioni.

    ENDPOINT GESTITI:
      GET  /dama/health → health()   (health check, no auth)
      POST /dama/new    → new()      (nuova partita, JWT richiesto)
      GET  /dama/moves  → moves()    (mosse legali, JWT richiesto)
      POST /dama/move   → move()     (mossa + risposta AI, JWT richiesto)
      POST /dama/reset  → reset()    (reset partita, JWT richiesto)

    NOTA CSRF:
      @method_decorator(csrf_exempt, name="dispatch") disabilita il CSRF per
      tutti i metodi POST. I GET (health, moves) non sono influenzati.
    """

    # ── health ────────────────────────────────────────────────────────────────

    def health(self, request):
        """
        Health check per il servizio Dama.

        ENDPOINT: GET /dama/health
        AUTENTICAZIONE: Non richiesta (usato da load balancer / monitoraggio).
        RISPOSTA (200): {"status": "ok", "game": "dama"}

        PATTERN: Health Check Endpoint (standard per microservizi e container orchestration).
        """
        self.allowed_methods = ["GET"]
        return JsonResponse({"status": "ok", "game": "dama"})

    # ── new ───────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def new(self, request):
        """
        Crea una nuova partita di Dama e restituisce lo stato iniziale.

        ENDPOINT: POST /dama/new
        BODY JSON (opzionale): {"difficulty": "random" | "minimax"}
          "random"  → RandomAIStrategy (mossa casuale)
          "minimax" → MinimaxAIStrategy (Minimax alpha-beta, profondità 6)
          Default: "random"

        RISPOSTA SUCCESSO (201 Created):
          {
            "sessionId": "<UUID>",
            "difficulty": "random",
            "board": [[...], ...],       ← scacchiera 8x8
            "turn": "white",             ← tocca sempre al bianco (umano) per primo
            "status": "ongoing",
            "legalMoves": [...],         ← mosse disponibili per il bianco
            "aiMove": null
          }

        PERCORSO:
          → get_dama_service().new_game(difficulty)
            [dama/services/game_application_service.py]
              → GameSessionRepository.create(difficulty)
              → GameRulesService.legal_moves(state)
        """
        self.allowed_methods = ["POST"]
        body = self._parse_body(request)
        result = get_dama_service().new_game(body.get("difficulty", "random"))
        return JsonResponse(result, status=201)

    # ── moves ─────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def moves(self, request):
        """
        Restituisce le mosse legali per la sessione di Dama corrente.

        ENDPOINT: GET /dama/moves?sessionId=<UUID>
        PARAMETRI: sessionId (query string)

        RISPOSTA SUCCESSO (200):
          {"sessionId": "<UUID>", "legalMoves": [...], "turn": "white"}
        RISPOSTA ERRORI:
          400 {"error": "sessionId obbligatorio"}
          404 {"error": "Sessione non trovata: <sid>"}

        NOTA: Usa GET parameter (request.GET), non body JSON.

        PERCORSO:
          → get_dama_service().get_legal_moves(sid)
            [dama/services/game_application_service.py]
              → GameRulesService.legal_moves(state)
                → MoveGeneratorService.legal_moves(board, turn)
        """
        self.allowed_methods = ["GET"]
        sid = request.GET.get("sessionId")
        if not sid:
            return JsonResponse({"error": "sessionId obbligatorio"}, status=400)
        try:
            return JsonResponse(get_dama_service().get_legal_moves(sid))
        except KeyError as e:
            return JsonResponse({"error": str(e)}, status=404)

    # ── move ──────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def move(self, request):
        """
        Esegue la mossa del giocatore umano (white) nella partita di Dama.

        ENDPOINT: POST /dama/move
        BODY JSON:
          {
            "sessionId": "<UUID>",
            "move": {"path": [[r1,c1],[r2,c2],...], "captures": [[rc,cc],...]}
          }

        RISPOSTA SUCCESSO (200):
          Stato aggiornato della partita (board, turn, status, legalMoves, aiMove)

        RISPOSTA ERRORI:
          400 {"error": "sessionId e move obbligatori"}
          400 {"error": "Non è il tuo turno."} / "Mossa non legale." / "Partita già terminata."
          404 {"error": "Sessione non trovata: <sid>"}

        GESTIONE FINE PARTITA:
          Se status ∈ {"white_wins", "black_wins"} → record_dama_result().
          "white" = umano, quindi won = (status == "white_wins").
          L'eccezione DB è catturata silenziosamente: non interrompe la risposta.

        PERCORSO:
          → get_dama_service().human_move(sid, move_dict)
            [dama/services/game_application_service.py]
              → GameRulesService.apply_move(state, move)
              → AIStrategyFactory.create() → strategy.choose_move(state)
              → GameSessionRepository.update_state()
          → stats_repository.record_dama_result(user_id, won)  ← solo se terminata
        self.allowed_methods = ["POST"]
        """
        body = self._parse_body(request)
        sid  = body.get("sessionId")
        move = body.get("move")

        # Validazione campi obbligatori prima di chiamare il servizio.
        if not sid or move is None:
            return JsonResponse({"error": "sessionId e move obbligatori"}, status=400)

        try:
            result = get_dama_service().human_move(sid, move)
        except KeyError as e:
            # GameSessionRepository lancia KeyError se sid non trovato.
            return JsonResponse({"error": str(e)}, status=404)
        except (PermissionError, ValueError) as e:
            # PermissionError: non è il turno del bianco
            # ValueError: mossa non nel formato atteso
            return JsonResponse({"error": str(e)}, status=400)

        # Se la partita è terminata, registra il risultato nelle statistiche.
        status = result.get("status", "")
        if status in ("white_wins", "black_wins"):
            try:
                get_container().stats_repository.record_dama_result(
                    request.current_user.user_id,
                    won=(status == "white_wins"),
                )
            except Exception:
                # Errore DB nelle stats: non blocca la risposta di gioco.
                pass

        return JsonResponse(result)

    # ── reset ─────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def reset(self, request):
        """
        Resetta una partita di Dama esistente, ricreandola con la stessa difficoltà.

        ENDPOINT: POST /dama/reset
        BODY JSON: {"sessionId": "<UUID>"}
        RISPOSTA SUCCESSO (200): Stesso formato di /dama/new (nuovo stato iniziale)
        RISPOSTA ERRORI:
          400 {"error": "sessionId obbligatorio"}
          404 {"error": "Sessione non trovata: <sid>"}

        PERCORSO:
          → get_dama_service().reset_game(sid)
            [dama/services/game_application_service.py]
              → GameSessionRepository.delete(sid)
              → GameApplicationService.new_game(difficulty)  ← stessa difficoltà
        """
        self.allowed_methods = ["POST"]
        body = self._parse_body(request)
        sid  = body.get("sessionId")
        if not sid:
            return JsonResponse({"error": "sessionId obbligatorio"}, status=400)
        try:
            return JsonResponse(get_dama_service().reset_game(sid))
        except KeyError as e:
            return JsonResponse({"error": str(e)}, status=404)
