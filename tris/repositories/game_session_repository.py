"""
GameSessionRepository (Tris) — Persistenza in-memory delle sessioni Tris (SRP).

RESPONSABILITÀ (SRP):
  Gestisce SOLO lo storage in-memory delle sessioni di Tris.
  Analogo a dama/repositories/game_session_repository.py, ma per il Tris.

STRUTTURA DATI:
  _sessions: Dict[str, dict]
  Chiave: session_id (UUID stringa)
  Valore: {"state": GameState, "difficulty": str}

SOLID PRINCIPLES:
  - SRP: Solo storage. Nessuna logica di gioco.
  - DIP: GameApplicationService (Tris) riceve questa classe come dipendenza
    iniettata dalla factory (tris_service_factory.py).

PERCORSO CHIAMATA:
  tris_service_factory.get_tris_service()
    → GameApplicationService(repository=GameSessionRepository(), ...)
  GameApplicationService.new_game()
    → repository.create(difficulty) → session_id
  GameApplicationService.human_move()
    → repository.get(session_id) → session
    → repository.update(session_id, new_state)
  GameApplicationService.reset_game()
    → repository.delete(session_id)
"""

import uuid
from typing import Dict, Optional
from tris.models.game_state import GameState


class GameSessionRepository:
    """Store in-memory per le sessioni di gioco Tris."""

    def __init__(self):
        self._sessions: Dict[str, dict] = {}

    def create(self, difficulty: str) -> str:
        """
        Crea una nuova sessione Tris e restituisce il session_id.

        :param difficulty: "random" o "minimax"
        :return: UUID stringa della nuova sessione
        """
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "state":      GameState(),   # Board vuota, turno HUMAN
            "difficulty": difficulty,
        }
        return session_id

    def get(self, session_id: str) -> Optional[dict]:
        """
        Recupera la sessione per ID.

        :return: {"state": GameState, "difficulty": str} oppure None
        """
        return self._sessions.get(session_id)

    def update(self, session_id: str, state: GameState) -> None:
        """
        Aggiorna lo stato di una sessione esistente.

        :raises KeyError: Se session_id non esiste nel repository
        """
        if session_id not in self._sessions:
            raise KeyError(f"Sessione non trovata: {session_id}")
        self._sessions[session_id]["state"] = state

    def delete(self, session_id: str) -> None:
        """Elimina una sessione. Silenzioso se non esiste."""
        self._sessions.pop(session_id, None)
