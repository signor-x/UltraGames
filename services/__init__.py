"""
Package services — Servizi applicativi e infrastrutturali core.

SERVIZI:
  container.py          → Singleton DI container (_Container + get_container())
  auth_service.py       → Login (bcrypt verify + JWT generate) e registrazione
  account_service.py    → Update profile, change password, delete account
  jwt_token_service.py  → JWT sign (generate) e verify (PyJWT HS256)
  user_repository.py    → CRUD utenti su MariaDB (InDatabaseUserRepository)
  stats_repository.py   → CRUD statistiche su MariaDB (InDatabaseStatsRepository)
  auth_helpers.py       → Decorator @cbv_require_auth e @cbv_require_admin

GRAFO DI DIPENDENZE (costruito da container.py):
  _Container
    ├── user_repository   (InDatabaseUserRepository)
    ├── stats_repository  (InDatabaseStatsRepository)
    ├── token_service     (JwtTokenService)
    ├── auth_service      (AuthService ← user_repo + token_svc)
    └── account_service   (AccountService ← user_repo + stats_repo)
"""
