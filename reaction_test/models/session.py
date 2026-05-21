"""
Session — Modello di dominio per una sessione del Reaction Test (SRP).

RESPONSABILITÀ (SRP):
  Contiene SOLO i dati di una sessione: fase corrente, timestamp del verde,
  lista dei risultati. Non contiene logica di timer né di scoring.

CICLO DI VITA DELLA SESSIONE:
  IDLE
    ↓ start_round()       → thread daemon avviato
  WAITING
    ↓ (dopo delay random) → thread imposta phase=GREEN
  GREEN
    ↓ register_click()
  DONE                    → risultato calcolato
    ↓ reset_session()
  IDLE (di nuovo)

ATTRIBUTI:
  id (str)                : UUID della sessione
  phase (SessionPhase)    : Fase corrente (IDLE / WAITING / GREEN / DONE)
  green_at_ms (float|None): Timestamp epoch ms quando il semaforo è diventato verde
  results (List[ReactionResult]): Lista dei risultati dei round precedenti

PERCORSO CHIAMATA:
  ReactionApplicationService.new_session()
    → SessionRepository.create() → Session(id=UUID, phase=IDLE)
  ReactionApplicationService.start_round(sid)
    → session.phase = WAITING
    → Thread daemon → session.phase = GREEN, session.green_at_ms = now
  ReactionApplicationService.register_click(sid, click_at_ms)
    → reaction_ms = click_at_ms - session.green_at_ms
    → session.results.append(ReactionResult(...))
    → session.phase = DONE
"""

import uuid
from enum import Enum
from typing import Optional, List
from .reaction_result import ReactionResult


class SessionPhase(str, Enum):
    """
    Enum per le fasi della sessione Reaction Test.

    Eredita da str per serializzare direttamente come stringa JSON.
    Es: SessionPhase.WAITING.value == "waiting".
    """
    IDLE    = "idle"     # Sessione creata, nessun round avviato
    WAITING = "waiting"  # Countdown in corso (thread in sleep)
    GREEN   = "green"    # Semaforo verde! Aspetta il click dell'utente
    DONE    = "done"     # Click registrato, risultato calcolato


class Session:
    """
    Aggregato che rappresenta lo stato di una sessione del Reaction Test.

    THREAD SAFETY:
      La modifica di phase e green_at_ms avviene dal thread daemon di start_round().
      Python GIL garantisce atomicità per operazioni semplici su attributi Python,
      ma in un sistema multi-worker (es. Gunicorn multi-process) le sessioni in-memory
      non sono condivise. Questa implementazione è corretta per un singolo processo.

    CHIAMATO DA:
      SessionRepository.create()              → crea Session() iniziale
      ReactionApplicationService.start_round() → modifica phase e green_at_ms
      ReactionApplicationService.register_click() → appende a results
      ReactionApplicationService.get_phase()   → legge phase e green_at_ms
      ReactionApplicationService.get_stats()   → legge results
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        :param session_id: UUID della sessione; se None, ne genera uno nuovo
        """
        self.id:          str                = session_id or str(uuid.uuid4())
        self.phase:       SessionPhase       = SessionPhase.IDLE
        self.green_at_ms: Optional[float]    = None    # Impostato dal thread daemon
        self.results:     List[ReactionResult] = []    # Round completati

    def to_dict(self) -> dict:
        """
        Serializza la sessione per la risposta HTTP.

        CHIAMATO DA:
          ReactionApplicationService.new_session() → risposta /reaction/new
          ReactionApplicationService.reset_session() → risposta /reaction/reset
          ReactionApplicationService.get_phase()    → risposta /reaction/phase

        :return: Dizionario JSON-serializzabile
        """
        return {
            "sessionId":  self.id,
            "phase":      self.phase.value,         # "idle" | "waiting" | "green" | "done"
            "greenAtMs":  self.green_at_ms,         # float | null
            "results":    [r.to_dict() for r in self.results],
        }
