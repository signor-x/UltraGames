"""
InDatabaseUserRepository - Implementazione Repository pattern con MariaDB.

PATTERN ARCHITETTURALE: Repository (Data Mapper)
  Il Repository isola la logica di accesso ai dati (SQL/MariaDB) dalla logica
  di business (AuthService, AccountService). Le classi di servizio conoscono
  solo l'interfaccia del repository, non come i dati vengono effettivamente
  letti o scritti.

  Flusso di chiamata tipico (SRP):
    LoginView
      → get_container().auth_service           (services/container.py)
      → AuthService.login()                    (services/auth_service.py)
      → InDatabaseUserRepository.find_by_email() ← questo file
      → _get_connection() [MariaDB]

SOLID PRINCIPLES APPLICATI:
  - SRP (Single Responsibility): Questo file gestisce SOLO la persistenza degli
    utenti. La logica di validazione vive in AuthService; il mapping degli oggetti
    vive in _row_to_user().
  - DIP (Dependency Inversion): AuthService e AccountService dipendono da questa
    classe tramite il container (non la istanziano direttamente), rendendo
    possibile sostituirla con un mock nei test.
  - OCP (Open/Closed): Per aggiungere un nuovo backend (es. PostgreSQL) basta
    creare una nuova classe analoga senza modificare i servizi che la usano.

CONNESSIONE DATABASE:
  - Driver: python-mariadb (accesso diretto, NO Django ORM)
  - Config: settings.DATABASES["default"] (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)
  - Ogni metodo apre/chiude la propria connessione (no pool)
  - Nota: in produzione è preferibile un connection pool (es. mariadb.ConnectionPool)

SCHEMA TABELLA users (attesa nel DB):
  CREATE TABLE users (
    id            VARCHAR(36)  PRIMARY KEY,  -- UUID v4
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name          VARCHAR(100) NOT NULL
  );
"""

from typing import Optional
import mariadb
from django.conf import settings

from models.user import User


def _get_connection():
    """
    Crea e restituisce una connessione al database MariaDB.

    FLUSSO:
      1. Legge le credenziali da settings.DATABASES["default"]
         (ultragames_django/settings.py, popolato da variabili d'ambiente)
      2. Apre la connessione MariaDB con SSL disabilitato (sviluppo)
      3. Restituisce l'oggetto connessione

    UTILIZZO CONTEXT MANAGER:
      with _get_connection() as conn:
          cur = conn.cursor()
          ...
      # La connessione viene chiusa automaticamente all'uscita dal blocco with

    NOTA SICUREZZA:
      ssl=False è adeguato per ambienti di sviluppo o reti private.
      In produzione impostare ssl=True (o passare un dict con il certificato CA).

    :return: Oggetto connessione MariaDB attiva
    :rtype: mariadb.connection
    """
    db = settings.DATABASES["default"]
    return mariadb.connect(
        user=db["USER"],
        password=db["PASSWORD"],
        host=db["HOST"],
        port=int(db["PORT"]),   # la config Django lo conserva come stringa
        database=db["NAME"],
        ssl=False,
    )


class InDatabaseUserRepository:
    """
    Implementazione concreta del repository utenti su MariaDB.

    RESPONSABILITÀ (SRP):
      Traduce operazioni CRUD (Create / Read / Update / Delete) su oggetti User
      in query SQL parametrizzate. Non contiene logica di business.

    METODI:
      find_by_email  → SELECT per login e verifica unicità email
      find_by_id     → SELECT per operazioni account (update, delete)
      create         → INSERT per la registrazione
      update         → UPDATE per cambio profilo / password
      delete         → DELETE per cancellazione account
      exists_by_email→ COUNT(*) per verifica unicità rapida
      find_all       → SELECT tutti per pannello admin

    CHIAMATO DA:
      services/container.py  → istanziato in _Container.__init__
      services/auth_service.py    → find_by_email, exists_by_email, create
      services/account_service.py → find_by_id, update, delete
      apps/admin_panel/views/ban_user_view.py → find_by_id, delete
      apps/admin_panel/views/user_list_view.py → find_all
    """

    def find_by_email(self, email: str) -> Optional[User]:
        """
        Cerca un utente per indirizzo email (case-insensitive grazie a .lower()).

        UTILIZZO:
          AuthService.login() → verifica credenziali durante il login
          AuthService.register() → non usato direttamente, usa exists_by_email

        QUERY:
          SELECT id, email, password_hash, name FROM users WHERE email = ?

        Parametro '?' → query parametrizzata: previene SQL injection.

        :param email: Email normalizzata a lowercase (AuthService la normalizza prima)
        :return: User se trovato, None altrimenti
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, email, password_hash, name FROM users WHERE email = ?",
                (email.lower(),),
            )
            row = cur.fetchone()
        return self._row_to_user(row) if row else None

    def find_by_id(self, user_id: str) -> Optional[User]:
        """
        Cerca un utente per UUID.

        UTILIZZO:
          AccountService.update_profile() / change_password() / delete_account()
          BanUserView → verifica che l'utente da bannare esista prima di eliminarlo

        :param user_id: UUID dell'utente (stringa)
        :return: User se trovato, None altrimenti
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, email, password_hash, name FROM users WHERE id = ?",
                (user_id,),
            )
            row = cur.fetchone()
        return self._row_to_user(row) if row else None

    def create(self, user: User) -> User:
        """
        Inserisce un nuovo utente nel database.

        UTILIZZO:
          AuthService.register() → dopo hash della password e validazione

        TRANSAZIONE:
          conn.commit() rende la INSERT permanente. Se il commit non viene
          chiamato (es. eccezione prima), la riga non viene salvata (rollback
          automatico alla chiusura della connessione).

        :param user: Oggetto User con id (UUID4), email, hashed_password, name
        :return: Lo stesso oggetto User passato come input (invariato)
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)",
                (user.id, user.email.lower(), user.hashed_password, user.name),
            )
            conn.commit()
        return user

    def update(self, user: User) -> User:
        """
        Aggiorna email, password_hash e name di un utente esistente.

        UTILIZZO:
          AccountService.update_profile()  → aggiorna name e/o email
          AccountService.change_password() → aggiorna hashed_password

        :param user: Oggetto User con i campi già modificati in memoria
        :return: Lo stesso oggetto User aggiornato
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET email = ?, password_hash = ?, name = ? WHERE id = ?",
                (user.email.lower(), user.hashed_password, user.name, user.id),
            )
            conn.commit()
        return user

    def delete(self, user_id: str) -> None:
        """
        Elimina un utente dal database (azione irreversibile).

        UTILIZZO:
          AccountService.delete_account() → dopo verifica password + eliminazione stats
          BanUserView.post()              → dopo delete_user_stats

        ORDINE CHIAMATE (AccountService.delete_account):
          1. stats_repository.delete_user_stats(user_id)  ← prima le FK
          2. user_repository.delete(user_id)              ← poi l'utente

        :param user_id: UUID dell'utente da eliminare
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

    def exists_by_email(self, email: str) -> bool:
        """
        Verifica se un'email è già registrata nel sistema.

        UTILIZZO:
          AuthService.register()          → prima di creare l'utente
          AccountService.update_profile() → se l'utente vuole cambiare email

        Più efficiente di find_by_email(): COUNT(*) non trasferisce dati di riga.

        :param email: Email da verificare (normalizzata a lowercase)
        :return: True se l'email è già presente, False altrimenti
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM users WHERE email = ?", (email.lower(),))
            (count,) = cur.fetchone()
        return count > 0

    def find_all(self) -> list:
        """
        Restituisce tutti gli utenti ordinati alfabeticamente per nome.

        UTILIZZO:
          UserListView.get() → pannello amministratore per la lista utenti

        :return: Lista di oggetti User (può essere vuota se non ci sono utenti)
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, email, password_hash, name FROM users ORDER BY name ASC")
            rows = cur.fetchall()
        return [self._row_to_user(row) for row in rows]

    @staticmethod
    def _row_to_user(row: tuple) -> User:
        """
        Converte una riga SQL (tupla) in un oggetto User di dominio.

        PATTERN DATA MAPPER:
          Questa funzione isola la conoscenza dello schema SQL dal resto
          del codice. Se si rinomina una colonna del DB, si modifica solo qui.

        CAMPI RIGA: (id, email, password_hash, name)
          In questo ordine per tutte le SELECT del repository.

        :param row: Tupla (id, email, password_hash, name) dalla query
        :return: Istanza User con i campi mappati
        """
        user_id, email, password_hash, name = row
        return User(id=user_id, email=email, hashed_password=password_hash, name=name)
