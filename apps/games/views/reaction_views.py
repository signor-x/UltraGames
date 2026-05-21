"""
reaction_views.py — Gestore unificato delle view e della factory per il Reaction Test.

STRUTTURA DEL FILE:
  get_reaction_service()  → Factory Singleton con lazy initialization via importlib
  ReactionView            → classe gestore con i metodi HTTP del Reaction Test:
                              health()  GET  /reaction/health
                              new()     POST /reaction/new
                              start()   POST /reaction/start
                              phase()   GET  /reaction/phase
                              click()   POST /reaction/click
                              stats()   GET  /reaction/stats
                              reset()   POST /reaction/reset

PATTERN SINGLETON + FACTORY con LAZY INITIALIZATION (get_reaction_service):
  Analogo a dama_views.py. Usa importlib per importazione lazy dei moduli
  del dominio reaction_test, evitando import circolari all'avvio di Django.

GRAFO DI DIPENDENZE COSTRUITO:
  ReactionApplicationService
    ├── SessionRepository         (reaction_test/repositories/session_repository.py)
    │     → Dict[str, Session] in-memory
    ├── RandomTimerStrategy       (reaction_test/services/timer_strategy.py)
    │     → Delay casuale 2.0–5.0 secondi prima del semaforo verde
    │     → Implementa TimerStrategy (ABC) → DIP + LSP
    └── ReactionScoringService    (reaction_test/services/reaction_scoring_service.py)
          → Calcola rating (FULMINE/ECCELLENTE/...) dal tempo in ms

PERCORSO CHIAMATA (URL → metodo):
  ultragames_django/urls.py
    → include("apps.games.urls_reaction")        [apps/games/urls_reaction.py]
      → ReactionView.health_view()   GET  /reaction/health
      → ReactionView.new_view()      POST /reaction/new
      → ReactionView.start_view()    POST /reaction/start
      → ReactionView.phase_view()    GET  /reaction/phase
      → ReactionView.click_view()    POST /reaction/click
      → ReactionView.stats_view()    GET  /reaction/stats
      → ReactionView.reset_view()    POST /reaction/reset

FLUSSO COMPLETO SESSIONE:
  1. POST /reaction/new    → new()    → sessionId, phase="idle"
  2. POST /reaction/start  → start()  → avvia countdown (phase="waiting", thread daemon)
  3. GET  /reaction/phase  → phase()  → polling ogni ~50ms finché phase="green"
  4. [utente vede il verde e clicca il prima possibile]
  5. POST /reaction/click  → click()  → registra click (reaction_ms, rating)
  6. GET  /reaction/stats  → stats()  → statistiche sessione corrente
  7. POST /reaction/reset  → reset()  → ricomincia (torna a phase="idle")

SOLID PRINCIPLES:
  - SRP: Ogni metodo gestisce un solo endpoint.
  - DIP: Le view dipendono dall'interfaccia ReactionApplicationService tramite factory.
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

# Singleton del servizio Reaction Test, inizializzato a None (lazy).
_reaction_service = None


def get_reaction_service():
    """
    Restituisce il singleton di ReactionApplicationService.

    PRIMO ACCESSO:
      1. Importa i moduli via importlib (lazy, evita circular import)
      2. Costruisce il grafo: Repository → TimerStrategy → ScoringService
      3. Istanzia ReactionApplicationService con le dipendenze iniettate (DIP)
      4. Salva in _reaction_service (global)

    ACCESSI SUCCESSIVI: Restituisce il singleton già creato (O(1)).

    :return: Istanza singleton di ReactionApplicationService
    """
    global _reaction_service
    if _reaction_service is None:
        repo_mod    = importlib.import_module("reaction_test.repositories.session_repository")
        svc_mod     = importlib.import_module("reaction_test.services.reaction_application_service")
        timer_mod   = importlib.import_module("reaction_test.services.timer_strategy")
        scoring_mod = importlib.import_module("reaction_test.services.reaction_scoring_service")

        _reaction_service = svc_mod.ReactionApplicationService(
            repository=repo_mod.SessionRepository(),              # In-memory {id: Session}
            timer_strategy=timer_mod.RandomTimerStrategy(),       # Delay 2-5s random
            scoring_service=scoring_mod.ReactionScoringService(), # Rating da ms
        )
    return _reaction_service


# ── View gestore ──────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class ReactionView(JsonBodyMixin, ActionView, View):
    """
    Gestore unificato delle view per il Reaction Test.

    Raccoglie in un'unica classe tutti gli endpoint del gioco, condividendo
    le dipendenze (JsonBodyMixin, get_reaction_service, get_container) senza
    duplicazioni.

    ENDPOINT GESTITI:
      GET  /reaction/health → health()  (health check, no auth)
      POST /reaction/new    → new()     (nuova sessione, JWT richiesto)
      POST /reaction/start  → start()   (avvia countdown, JWT richiesto)
      GET  /reaction/phase  → phase()   (polling fase corrente, JWT richiesto)
      POST /reaction/click  → click()   (registra click utente, JWT richiesto)
      GET  /reaction/stats  → stats()   (statistiche sessione, JWT richiesto)
      POST /reaction/reset  → reset()   (reset sessione, JWT richiesto)

    NOTA CSRF:
      @method_decorator(csrf_exempt, name="dispatch") disabilita il CSRF per
      tutti i metodi POST. I GET (health, phase, stats) non sono influenzati.
    """

    # ── health ────────────────────────────────────────────────────────────────

    def health(self, request):
        """
        Health check per il servizio Reaction Test.

        ENDPOINT: GET /reaction/health
        AUTENTICAZIONE: Non richiesta (usato da load balancer / monitoraggio).
        RISPOSTA (200): {"status": "ok", "game": "reaction"}
        """
        self.allowed_methods = ["GET"]
        return JsonResponse({"status": "ok", "game": "reaction"})

    # ── new ───────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def new(self, request):
        """
        Crea una nuova sessione del Reaction Test.

        ENDPOINT: POST /reaction/new
        BODY: (vuoto, nessun parametro necessario)

        RISPOSTA SUCCESSO (201 Created):
          {
            "sessionId": "<UUID>",
            "phase": "idle",          ← stato iniziale, in attesa di /start
            "greenAtMs": null,
            "results": []
          }

        DIFFERENZA CON new_game (Dama/Tris):
          La sessione Reaction Test non ha un game state con board, solo una
          fase (IDLE → WAITING → GREEN → DONE) e una lista di risultati.
          Non riceve parametri (nessuna "difficulty").

        PERCORSO:
          → get_reaction_service().new_session()
            [reaction_test/services/reaction_application_service.py]
              → SessionRepository.create() → Session(id=UUID, phase=IDLE)
        """
        self.allowed_methods = ["POST"]
        result = get_reaction_service().new_session()
        return JsonResponse(result, status=201)

    # ── start ─────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def start(self, request):
        """
        Avvia il countdown del Reaction Test per la sessione specificata.

        ENDPOINT: POST /reaction/start
        BODY JSON: {"sessionId": "<UUID>"}

        RISPOSTA SUCCESSO (200):
          {
            "sessionId": "<UUID>",
            "phase": "waiting",           ← in attesa del semaforo verde
            "delayMs": 3200               ← durata attesa in ms (informativa)
          }

        RISPOSTA ERRORI:
          400 {"error": "sessionId obbligatorio"}
          404 {"error": "Sessione non trovata: <sid>"}

        THREAD BACKGROUND:
          start_round() avvia un thread daemon che:
          1. Dorme per delay secondi (RandomTimerStrategy.delay_seconds())
          2. Controlla che la sessione sia ancora in phase WAITING
          3. Imposta phase=GREEN e green_at_ms=time.time()*1000
          Il client fa polling su GET /reaction/phase per rilevare il cambiamento.

        PERCORSO:
          → get_reaction_service().start_round(sid)
            [reaction_test/services/reaction_application_service.py]
              → session.phase = WAITING
              → threading.Thread(target=_set_green_after, delay=random 2-5s).start()
        """
        self.allowed_methods = ["POST"]
        body = self._parse_body(request)
        sid  = body.get("sessionId")
        if not sid:
            return JsonResponse({"error": "sessionId obbligatorio"}, status=400)
        try:
            return JsonResponse(get_reaction_service().start_round(sid))
        except KeyError as e:
            return JsonResponse({"error": str(e)}, status=404)

    # ── phase ─────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def phase(self, request):
        """
        Restituisce la fase corrente della sessione Reaction Test (polling).

        ENDPOINT: GET /reaction/phase?sessionId=<UUID>

        RISPOSTA SUCCESSO (200):
          {
            "sessionId": "<UUID>",
            "phase": "waiting" | "green" | "done" | "idle",
            "greenAtMs": 1715000000000 | null   ← epoch ms quando è diventato verde
          }

        RISPOSTA ERRORI:
          400 {"error": "sessionId obbligatorio"}
          404 {"error": "Sessione non trovata: <sid>"}

        PATTERN POLLING:
          Il client chiama questo endpoint ripetutamente (es. ogni 50ms) dopo
          aver inviato POST /reaction/start, finché phase passa da "waiting" a "green".

          Fasi possibili (SessionPhase enum):
            IDLE    → sessione creata, nessun round avviato
            WAITING → countdown in corso (thread background in sleep)
            GREEN   → semaforo verde! Il client deve mostrare il segnale
            DONE    → click registrato, risultato disponibile

        PERCORSO:
          → get_reaction_service().get_phase(sid)
            [reaction_test/services/reaction_application_service.py]
              → SessionRepository.get(session_id) → Session
              → Restituisce {sessionId, phase, greenAtMs}
        """
        self.allowed_methods = ["GET"]
        sid = request.GET.get("sessionId")
        if not sid:
            return JsonResponse({"error": "sessionId obbligatorio"}, status=400)
        try:
            return JsonResponse(get_reaction_service().get_phase(sid))
        except KeyError as e:
            return JsonResponse({"error": str(e)}, status=404)

    # ── click ─────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def click(self, request):
        """
        Registra il click dell'utente e calcola il tempo di reazione.

        ENDPOINT: POST /reaction/click
        BODY JSON: {"sessionId": "<UUID>", "clickAtMs": 1715000003200}
          clickAtMs: timestamp in millisecondi epoch (Date.now() lato client)

        RISPOSTA SUCCESSO (200):
          {
            "sessionId": "<UUID>",
            "result": {
              "id": "<UUID>",
              "reactionMs": 215,
              "clickedEarly": false,
              "timestamp": "2026-05-12T14:30:00.123456"
            },
            "rating": {"label": "ECCELLENTE", "emoji": "🚀"},  ← null se early click
            "stats": {"count": 3, "bestMs": 190, "avgMs": 210.3, "worstMs": 240}
          }

        RISPOSTA ERRORI:
          400 {"error": "sessionId e clickAtMs obbligatori"}
          400 {"error": "Nessun round attivo."}  ← phase non è GREEN né WAITING
          404 {"error": "Sessione non trovata: <sid>"}

        CALCOLO reaction_ms:
          Il client invia clickAtMs = Date.now() (timestamp JavaScript in ms epoch).
          Il server ha memorizzato green_at_ms = time.time() * 1000 (stesso formato).
          reaction_ms = clickAtMs - green_at_ms (ms trascorsi dal verde al click)

        GESTIONE STATISTICHE:
          record_reaction_ms() viene chiamato solo se reaction_ms > 0.
          Un click anticipato (clickedEarly=True) ha reaction_ms=0 e non viene registrato.

        PERCORSO:
          → get_reaction_service().register_click(sid, click_at_ms)
            [reaction_test/services/reaction_application_service.py]
              → Se phase=WAITING: ReactionResult.early_click() (clicked_early=True)
              → Se phase=GREEN:
                  reaction_ms = click_at_ms - session.green_at_ms
                  ReactionScoringService.rate(reaction_ms) → ReactionRating
              → Statistics.from_results(session.results)
          → stats_repository.record_reaction_ms(user_id, reaction_ms)  ← solo se > 0
        self.allowed_methods = ["POST"]
        """
        body     = self._parse_body(request)
        sid      = body.get("sessionId")
        click_ms = body.get("clickAtMs")

        # click_ms può essere 0 (falsy!): "is None" è il controllo corretto.
        if not sid or click_ms is None:
            return JsonResponse({"error": "sessionId e clickAtMs obbligatori"}, status=400)

        try:
            result = get_reaction_service().register_click(sid, float(click_ms))
        except KeyError as e:
            return JsonResponse({"error": str(e)}, status=404)

        # Aggiorna il record nel DB solo se il click è valido (reaction_ms > 0).
        reaction_ms = (result.get("result") or {}).get("reactionMs")
        if reaction_ms is not None and reaction_ms > 0:
            try:
                get_container().stats_repository.record_reaction_ms(
                    request.current_user.user_id, int(reaction_ms)
                )
            except Exception:
                # Errore DB nelle stats: non interrompe la risposta di gioco.
                pass

        return JsonResponse(result)

    # ── stats ─────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def stats(self, request):
        """
        Statistiche aggregate dei round della sessione corrente.

        ENDPOINT: GET /reaction/stats?sessionId=<UUID>

        RISPOSTA SUCCESSO (200):
          {
            "sessionId": "<UUID>",
            "count": 3,         ← numero di round validi (esclude early click)
            "bestMs": 190,
            "avgMs": 210.3,
            "worstMs": 240
          }

        RISPOSTA ERRORI:
          400 {"error": "sessionId obbligatorio"}
          404 {"error": "Sessione non trovata: <sid>"}

        DIFFERENZA CON /api/stats/me:
          Questo endpoint restituisce le statistiche della SESSIONE corrente
          (in-memory, round di questa sessione). /api/stats/me restituisce le
          statistiche globali dal DATABASE (best_ms assoluto, totale tentativi).

        PERCORSO:
          → get_reaction_service().get_stats(sid)
            [reaction_test/services/reaction_application_service.py]
              → Statistics.from_results(session.results)
                [reaction_test/models/statistics.py]
        """
        self.allowed_methods = ["GET"]
        sid = request.GET.get("sessionId")
        if not sid:
            return JsonResponse({"error": "sessionId obbligatorio"}, status=400)
        try:
            return JsonResponse(get_reaction_service().get_stats(sid))
        except KeyError as e:
            return JsonResponse({"error": str(e)}, status=404)

    # ── reset ─────────────────────────────────────────────────────────────────

    @cbv_require_auth
    def reset(self, request):
        """
        Resetta una sessione Reaction Test: azzera fase, timer e risultati.

        ENDPOINT: POST /reaction/reset
        BODY JSON: {"sessionId": "<UUID>"}
        RISPOSTA SUCCESSO (200): Stato sessione dopo reset (phase="idle", results=[])
        RISPOSTA ERRORI:
          400 {"error": "sessionId obbligatorio"}
          404 {"error": "Sessione non trovata: <sid>"}

        PERCORSO:
          → get_reaction_service().reset_session(sid)
            [reaction_test/services/reaction_application_service.py]
              → session.phase = IDLE
              → session.green_at_ms = None
              → session.results = []
              → SessionRepository.save(session)
        """
        self.allowed_methods = ["POST"]
        body = self._parse_body(request)
        sid  = body.get("sessionId")
        if not sid:
            return JsonResponse({"error": "sessionId obbligatorio"}, status=400)
        try:
            return JsonResponse(get_reaction_service().reset_session(sid))
        except KeyError as e:
            return JsonResponse({"error": str(e)}, status=404)
  