"""
Package reaction_test.repositories — Persistenza delle sessioni Reaction Test.

REPOSITORY:
  SessionRepository → Dict in-memory {session_id: Session}
  Le sessioni sono referenziate direttamente: modifiche al thread daemon
  (phase, green_at_ms) si riflettono automaticamente (stesso oggetto).
"""
