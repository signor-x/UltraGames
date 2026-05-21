"""
GameSessionRepository — Persistenza in-memory delle sessioni di gioco Dama (SRP).

RESPONSABILITÀ (SRP):
  Gestisce SOLO lo storage delle sessioni di gioco. Non contiene logica
  di gioco né di validazione. È un semplice dizionario con operazioni CRUD.

STRUTTURA DATI:
  _sessions: Dict[str, dict]
  Chiave: session_id (UUID stringa)
  Valore: {"state": GameState, "difficulty": str}

PERSISTENZA IN-MEMORY:
  Le sessioni vivono solo durante il processo Python. Al riavvio del server
  tutte le sessioni vengono perse. In un sistema di produzione si userebbe
  Redis o un DB per persistenza tra riavvii.

SOLID PRINCIPLES:
  - SRP: Solo storage. Nessuna logica di gioco.
  - DIP: GameApplicationService dipende da questa classe tramite il
    costruttore (iniettata da dama_service_factory.py). Sostituibile
    con un'implementazione Redis senza modificare il servizio.

PERCORSO CHIAMATA:
  dama_service_factory.get_dama_service()
    → GameApplicationService(repository=GameSessionRepository(), ...)
  GameApplicationService.new_game()
    → repository.create(difficulty) → sid
  GameApplicationService.human_move()
    → repository.get(sid) → session
    → repository.update_state(sid, new_state)
  GameApplicationService.reset_game()
    → repository.delete(sid)
    → GameApplicationService.new_game()
"""

import uuid
from typing import Dict, Optional
from ..models.game_state import GameState


class GameSessionRepository:
    """
    Store in-memory per le sessioni di gioco Dama.

    Ogni sessione è un dizionario:
      {"state": GameState, "difficulty": "random"|"minimax"}
    """

    def __init__(self):
        # Dizionario principale: session_id → dati sessione
        self._sessions: Dict[str, dict] = {}

    def create(self, difficulty: str) -> str:
        """
        Crea una nuova sessione con stato iniziale e restituisce il session_id.

        CHIAMATO DA: GameApplicationService.new_game()

        :param difficulty: "random" o "minimax" (strategia AI)
        :return: UUID stringa che identifica la sessione
        """
        sid = str(uuid.uuid4())  # ID univoco per la sessione
        self._sessions[sid] = {
            "state":      GameState(),   # Posizione iniziale (Board.initial(), turno WHITE)
            "difficulty": difficulty,    # Memorizza la difficoltà per reset_game()
        }
        return sid

    def get(self, sid: str) -> Optional[dict]:
        """
        Recupera la sessione per session_id.

        CHIAMATO DA:
          GameApplicationService.human_move() → legge state e difficulty
          GameApplicationService._ai_turn()   → legge state dopo aggiornamento

        :param sid: UUID della sessione
        :return: Dict {"state", "difficulty"} oppure None se non trovata
        """
        return self._sessions.get(sid)

    def update_state(self, sid: str, state: GameState) -> None:
        """
        Aggiorna lo stato di gioco di una sessione esistente.

        CHIAMATO DA:
          GameApplicationService.human_move() → dopo mossa umana
          GameApplicationService._ai_turn()   → dopo mossa AI

        :param sid: UUID della sessione
        :param state: Nuovo GameState da persistere
        :raises KeyError: Se la sessione non esiste (ID invalido)
        """
        if sid not in self._sessions:
            raise KeyError(f"Sessione non trovata: {sid}")
        self._sessions[sid]["state"] = state

    def delete(self, sid: str) -> None:
        """
        Elimina una sessione dal repository.

        CHIAMATO DA: GameApplicationService.reset_game()
        Usa .pop(sid, None) per evitare KeyError se la sessione non esiste.

        :param sid: UUID della sessione da eliminare
        """
        self._sessions.pop(sid, None)
