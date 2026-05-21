"""
User — Entità di dominio utente (SRP).

RESPONSABILITÀ (SRP):
  Rappresenta SOLO i dati di un utente come entità di dominio.
  Non contiene logica di persistenza (→ InDatabaseUserRepository),
  autenticazione (→ AuthService) né serializzazione HTTP (→ view).

NOTA DJANGO:
  Questo NON è un modello Django (django.db.models.Model).
  Il progetto usa MariaDB direttamente (python-mariadb) invece dell'ORM Django.
  User è un POPO (Plain Old Python Object) senza alcuna dipendenza Django.

  VANTAGGI DI QUESTO APPROCCIO:
    - Nessuna migrazione Django da gestire
    - Query SQL totalmente controllate (nessuna query N+1 nascosta dall'ORM)
    - Portabilità: User può essere usato senza Django installato

  SVANTAGGI:
    - Nessuna integrazione con Django admin
    - Nessun supporto automatico per le migrazioni
    - Più codice SQL manuale da mantenere

PERCORSO CHIAMATA:
  InDatabaseUserRepository._row_to_user(row) → User(...)
  AuthService.login()         → user = repo.find_by_email() → User
  AuthService.register()      → user = User(...) → repo.create(user)
  AccountService.*()          → user = repo.find_by_id() → modifica → repo.update(user)
  BanUserView.post()          → user = repo.find_by_id() → user.name (per messaggio)
  UserListView.get()          → users = repo.find_all() → [User]
"""


class User:
    """
    Entità di dominio che rappresenta un utente registrato.

    ATTRIBUTI:
      id (str)              : UUID v4 come stringa (es. "550e8400-e29b-41d4-a716-446655440000")
      email (str)           : Email normalizzata a lowercase (chiave univoca nel DB)
      hashed_password (str) : Hash bcrypt della password (60 caratteri)
      name (str)            : Nome visualizzato dell'utente

    NOTA SICUREZZA:
      hashed_password NON viene mai esposto nelle risposte HTTP.
      Le view restituiscono solo id, email, name.
      Solo AuthService e AccountService accedono a hashed_password.
    """

    def __init__(self, id: str, email: str, hashed_password: str, name: str):
        """
        :param id: UUID v4 dell'utente (generato da AuthService.register())
        :param email: Email normalizzata a lowercase
        :param hashed_password: Hash bcrypt (non la password in chiaro)
        :param name: Nome dell'utente
        """
        self.id:              str = id
        self.email:           str = email
        self.hashed_password: str = hashed_password
        self.name:            str = name
