"""
Package models — Entità e Value Object del dominio core.

MODELLI:
  User          → Entità utente: id (UUID), email, hashed_password, name
  TokenPayload  → Value Object JWT: user_id, email, name (dal payload JWT decodificato)
  AuthResult    → Result Object login: success, token | error

NOTA:
  Questi modelli NON sono django.db.models.Model.
  Sono POPO senza ORM, persistiti tramite InDatabaseUserRepository (MariaDB diretto).
"""
