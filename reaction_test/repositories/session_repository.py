"""
SessionRepository — Persistenza in-memory delle sessioni Reaction Test (SRP).

RESPONSABILITÀ (SRP):
  Gestisce SOLO lo storage delle sessioni Reaction Test in memoria.
  Non contiene logica di timer, scoring né di fase.

STRUTTURA DATI:
  _sessions: Dict[str, Session]
  Chiave: session_id (UUID stringa)
  Valore: istanza Session (mutabile in-place dal thread daemon)

NOTA THREAD SAFETY:
  Il thread daemon di ReactionApplicationService.start_round() modifica
  session.phase e session.green_at_ms direttamente sull'istanza Session
  già nel dizionario. Non è necessario chiamare save() dopo la modifica
  del thread: l'oggetto nel dizionario è lo stesso (riferimento condiviso).

SOLID PRINCIPLES:
  - SRP: Solo storage. Nessuna logica applicativa.
  - DIP: ReactionApplicationService riceve SessionRepository come dipendenza
    iniettata dalla factory (reaction_service_factory.py).
  - OCP: Per aggiungere persistenza Redis, creare RedisSessionRepository
    con la stessa interfaccia senza modificare il servizio.

PERCORSO CHIAMATA:
  reaction_service_factory.get_reaction_service()
    → ReactionApplicationService(repository=SessionRepository(), ...)
  ReactionApplicationService.new_session()
    → repository.create() → Session
  ReactionApplicationService.start_round(sid)
    → repository.get(sid) → Session  (poi modifica phase in-place)
  ReactionApplicationService.register_click(sid, click_at_ms)
    → repository.get(sid) → Session (poi appende result)
  ReactionApplicationService.reset_session(sid)
    → repository.get(sid) → Session (poi resetta campi)
"""

import uuid
from typing import Dict, Optional
from reaction_test.models.session import Session


class SessionRepository:
    """
    Store in-memory per le sessioni del Reaction Test.

    Le sessioni sono referenziate direttamente: modifiche all'oggetto Session
    restituito da get() si riflettono automaticamente nel repository
    (no copy, no save necessario).
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create(self) -> Session:
        """
        Crea una nuova sessione con phase=IDLE e la salva nel repository.

        CHIAMATO DA: ReactionApplicationService.new_session()

        :return: Istanza Session appena creata (phase=IDLE, results=[])
        """
        session = Session(session_id=str(uuid.uuid4()))
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        """
        Recupera una sessione per ID.

        CHIAMATO DA:
          ReactionApplicationService.start_round()    → modifica phase in-place
          ReactionApplicationService.register_click() → appende result in-place
          ReactionApplicationService.get_phase()      → legge phase e green_at_ms
          ReactionApplicationService.get_stats()      → legge results
          ReactionApplicationService.reset_session()  → resetta campi in-place

        :param session_id: UUID della sessione
        :return: Istanza Session (riferimento diretto) oppure None
        """
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        """
        Elimina una sessione dal repository.

        CHIAMATO DA: ReactionApplicationService.delete_session() (se implementato)
        Usa .pop(None) per evitare KeyError se non esiste.

        :param session_id: UUID della sessione da eliminare
        """
        self._sessions.pop(session_id, None)
