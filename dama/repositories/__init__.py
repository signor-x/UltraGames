"""
Package dama.repositories — Persistenza delle sessioni Dama.

REPOSITORY:
  GameSessionRepository → Dizionario in-memory {session_id: {state, difficulty}}

Implementa il pattern Repository (SRP): isola lo storage
dalla logica di business. Sostituibile con Redis o DB senza
modificare GameApplicationService.
"""
