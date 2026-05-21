"""
ReactionApplicationService — Orchestrazione use case Reaction Test (SRP).

RESPONSABILITÀ (SRP):
  Coordina i use case del Reaction Test:
    - new_session:    Crea sessione in-memory
    - start_round:    Avvia countdown con thread daemon
    - get_phase:      Legge fase corrente (per polling)
    - register_click: Registra il click e calcola risultato + rating
    - get_stats:      Calcola statistiche aggregate della sessione
    - reset_session:  Resetta la sessione al suo stato iniziale

  NON contiene logica di timer (→ TimerStrategy), scoring (→ ScoringService)
  né persistenza DB (→ InDatabaseStatsRepository).

SOLID PRINCIPLES:
  - SRP: Solo orchestrazione dei use case. Zero logica di timer o scoring.
  - DIP: Dipende da astrazioni iniettate nel costruttore:
      repository      → SessionRepository
      timer_strategy  → TimerStrategy (es. RandomTimerStrategy)
      scoring_service → ReactionScoringService
  - OCP: Aggiungere un nuovo use case (es. get_history) non richiede
    modificare quelli esistenti.
  - LSP: RandomTimerStrategy e FixedTimerStrategy sono intercambiabili
    senza modificare questo servizio.

THREAD DAEMON:
  start_round() avvia un thread daemon (daemon=True) che:
    1. Dorme per `delay` secondi (timer_strategy.delay_seconds())
    2. Controlla che la sessione esista ancora e sia in phase WAITING
    3. Imposta phase=GREEN e green_at_ms=time.time()*1000
  Daemon=True: il thread non blocca lo shutdown del processo.

PERCORSO CHIAMATA:
  apps/games/views/reaction_*_view.py
    → get_reaction_service()                   [reaction_service_factory.py]
      → ReactionApplicationService.new_session()
      → ReactionApplicationService.start_round(sid)
      → ReactionApplicationService.get_phase(sid)
      → ReactionApplicationService.register_click(sid, click_at_ms)
      → ReactionApplicationService.get_stats(sid)
      → ReactionApplicationService.reset_session(sid)
"""

import threading
import time
from typing import Optional

from reaction_test.models.session import Session, SessionPhase
from reaction_test.models.reaction_result import ReactionResult
from reaction_test.models.statistics import Statistics
from reaction_test.repositories.session_repository import SessionRepository
from reaction_test.services.timer_strategy import TimerStrategy
from reaction_test.services.reaction_scoring_service import ReactionScoringService


class ReactionApplicationService:
    """
    Orchestratore dei use case del Reaction Test.

    DIPENDENZE INIETTATE (DIP):
      repository:      SessionRepository       → storage in-memory sessioni
      timer_strategy:  TimerStrategy           → calcola delay countdown
      scoring_service: ReactionScoringService  → calcola rating dal tempo
    """

    def __init__(
        self,
        repository:      SessionRepository,
        timer_strategy:  TimerStrategy,
        scoring_service: ReactionScoringService,
    ):
        self._repo    = repository
        self._timer   = timer_strategy
        self._scoring = scoring_service

    # ── USE CASES ──────────────────────────────────────────────────────────

    def new_session(self) -> dict:
        """
        Crea una nuova sessione Reaction Test.

        FLUSSO:
          1. SessionRepository.create() → Session(id=UUID, phase=IDLE)
          2. Serializza e restituisce

        CHIAMATO DA: ReactionNewView.post()

        :return: {"sessionId", "phase": "idle", "greenAtMs": null, "results": []}
        """
        session = self._repo.create()
        return session.to_dict()

    def start_round(self, sid: str) -> dict:
        """
        Avvia il countdown per un nuovo round.

        FLUSSO:
          1. Recupera sessione (KeyError se non esiste)
          2. Imposta phase=WAITING immediatamente (risposta rapida al client)
          3. Calcola delay = timer_strategy.delay_seconds()
          4. Avvia thread daemon che dopo `delay` secondi:
              a. Verifica che session.phase sia ancora WAITING
              b. Imposta session.phase=GREEN e session.green_at_ms=now_ms
          5. Restituisce stato con phase=WAITING e delayMs

        THREAD DAEMON:
          daemon=True → Il thread non blocca lo shutdown del processo Django.
          Il thread modifica l'istanza Session direttamente (riferimento condiviso
          con il repository). Non serve una chiamata di salvataggio aggiuntiva.

        CHIAMATO DA: ReactionStartView.post()

        :param sid: UUID della sessione
        :return: {"sessionId", "phase": "waiting", "delayMs": int}
        :raises KeyError: Se la sessione non esiste
        """
        session = self._get_session(sid)
        session.phase = SessionPhase.WAITING

        delay = self._timer.delay_seconds()    # Secondi; es. 3.2
        delay_ms = int(delay * 1000)           # Millisecondi; es. 3200

        def _set_green():
            """Funzione eseguita dal thread daemon dopo il delay."""
            time.sleep(delay)
            # Controlla che la sessione non sia stata resettata nel frattempo
            if session.phase == SessionPhase.WAITING:
                session.phase      = SessionPhase.GREEN
                session.green_at_ms = time.time() * 1000   # Epoch ms

        thread = threading.Thread(target=_set_green, daemon=True)
        thread.start()

        return {
            "sessionId": sid,
            "phase":     SessionPhase.WAITING.value,
            "delayMs":   delay_ms,
        }

    def get_phase(self, sid: str) -> dict:
        """
        Restituisce la fase corrente della sessione (usato per polling).

        CHIAMATO DA: ReactionPhaseView.get()
        Il client chiama questo endpoint ripetutamente ogni ~50ms dopo start_round().

        :param sid: UUID della sessione
        :return: {"sessionId", "phase": str, "greenAtMs": float|null}
        :raises KeyError: Se la sessione non esiste
        """
        session = self._get_session(sid)
        return {
            "sessionId": sid,
            "phase":     session.phase.value,
            "greenAtMs": session.green_at_ms,
        }

    def register_click(self, sid: str, click_at_ms: float) -> dict:
        """
        Registra il click dell'utente e calcola il risultato del round.

        FLUSSO:
          1. Recupera sessione
          2. Verifica la fase:
              - GREEN:   calcola reaction_ms = click_at_ms - green_at_ms
                         crea ReactionResult.valid(reaction_ms)
              - WAITING: click anticipato → ReactionResult.early_click()
              - Altro:   nessun round attivo → ValueError
          3. Appende result a session.results
          4. Imposta session.phase = DONE
          5. Calcola rating (solo per round validi) e statistiche aggregate
          6. Restituisce tutto nella risposta

        CHIAMATO DA: ReactionClickView.post()

        :param sid: UUID della sessione
        :param click_at_ms: Timestamp del click in ms epoch (da Date.now())
        :return: {"sessionId", "result": {...}, "rating": {...}|null, "stats": {...}}
        :raises KeyError: Se la sessione non esiste
        :raises ValueError: Se phase non è GREEN né WAITING
        """
        session = self._get_session(sid)

        if session.phase == SessionPhase.GREEN:
            # Click valido: calcola il tempo di reazione
            reaction_ms = int(click_at_ms - session.green_at_ms)
            result      = ReactionResult.valid(reaction_ms)
            rating      = self._scoring.rate(reaction_ms)   # {"label", "emoji"}
        elif session.phase == SessionPhase.WAITING:
            # Click anticipato: non vale, ma viene registrato
            result = ReactionResult.early_click()
            rating = None    # Nessun rating per i click anticipati
        else:
            raise ValueError("Nessun round attivo.")

        session.results.append(result)
        session.phase = SessionPhase.DONE

        # Calcola le statistiche aggregate di tutti i round validi
        stats = Statistics.from_results(session.results)

        return {
            "sessionId": sid,
            "result":    result.to_dict(),
            "rating":    rating,
            "stats":     stats.to_dict(),
        }

    def get_stats(self, sid: str) -> dict:
        """
        Calcola e restituisce le statistiche aggregate della sessione.

        CHIAMATO DA: ReactionStatsView.get()

        :param sid: UUID della sessione
        :return: {"sessionId"} + Statistics.to_dict() (count, bestMs, avgMs, worstMs)
        :raises KeyError: Se la sessione non esiste
        """
        session = self._get_session(sid)
        stats   = Statistics.from_results(session.results)
        return {"sessionId": sid, **stats.to_dict()}

    def reset_session(self, sid: str) -> dict:
        """
        Resetta una sessione: azzera fase, timer e risultati.

        FLUSSO:
          1. Recupera sessione
          2. Reimposta phase=IDLE, green_at_ms=None, results=[]
          3. Restituisce lo stato resettato

        NOTA THREAD:
          Se un thread daemon è in corso (phase=WAITING), il reset imposta
          phase=IDLE. Il thread daemon, controllando session.phase==WAITING
          prima di impostare GREEN, vedrà IDLE e non farà nulla.
          In questo modo il reset è sicuro anche con thread in corso.

        CHIAMATO DA: ReactionResetView.post()

        :param sid: UUID della sessione
        :return: Stato sessione resettata (phase="idle", results=[])
        :raises KeyError: Se la sessione non esiste
        """
        session             = self._get_session(sid)
        session.phase       = SessionPhase.IDLE
        session.green_at_ms = None
        session.results     = []
        return session.to_dict()

    # ── HELPER PRIVATO ─────────────────────────────────────────────────────

    def _get_session(self, sid: str) -> Session:
        """
        Recupera la sessione o lancia KeyError se non esiste.

        :raises KeyError: Con messaggio "Sessione non trovata: <sid>"
        """
        session = self._repo.get(sid)
        if session is None:
            raise KeyError(f"Sessione non trovata: {sid}")
        return session
