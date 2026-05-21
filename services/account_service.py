"""
AccountService — Logica di gestione account utente (SRP).

RESPONSABILITÀ (SRP):
  Gestisce i use case dell'account utente autenticato:
    - update_profile:   Aggiorna nome e/o email
    - change_password:  Verifica password attuale e imposta quella nuova
    - delete_account:   Verifica password, elimina stats e utente

  NON gestisce l'autenticazione (→ AuthService), né accesso diretto al DB
  (→ repository), né cookie/JWT (→ view/middleware).

SOLID PRINCIPLES:
  - SRP: Solo gestione account. La logica DB è nei repository.
  - DIP: Dipende da user_repository e stats_repository iniettati dal container.
    Sostituibili con mock nei test.
  - OCP: Aggiungere un nuovo use case (es. update_avatar) non richiede
    modificare quelli esistenti.

PATTERN RESULT OBJECT:
  Tutti i metodi restituiscono un AccountResult (success, error).
  Nessuna eccezione viene propagata alle view: il flusso è sempre esplicito.

PERCORSO CHIAMATA:
  services/container.py
    → _Container.__init__() → AccountService(user_repo, stats_repo)
  apps/account/views/update_profile_view.py
    → get_container().account_service.update_profile(user_id, name, email)
  apps/account/views/change_password_view.py
    → get_container().account_service.change_password(user_id, current_pw, new_pw)
  apps/account/views/delete_account_view.py
    → get_container().account_service.delete_account(user_id, password)
"""

import bcrypt
import re


class AccountResult:
    """
    Value Object: risultato di un'operazione sull'account.

    FACTORY METHODS:
      AccountResult.ok()              → operazione riuscita
      AccountResult.failure(error)    → operazione fallita con messaggio
    """

    def __init__(self, success: bool, error: str = None):
        self.success = success
        self.error   = error

    @classmethod
    def ok(cls) -> "AccountResult":
        return cls(success=True)

    @classmethod
    def failure(cls, error: str) -> "AccountResult":
        return cls(success=False, error=error)


class AccountService:
    """
    Servizio per la gestione del profilo e dell'account utente.

    DIPENDENZE INIETTATE (DIP):
      user_repository:  InDatabaseUserRepository  → CRUD utenti
      stats_repository: InDatabaseStatsRepository → eliminazione stats (delete_account)
    """

    _EMAIL_RE        = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    _MIN_PASSWORD_LEN = 8

    def __init__(self, user_repository, stats_repository):
        self._user_repo  = user_repository
        self._stats_repo = stats_repository

    def update_profile(self, user_id: str, new_name: str, new_email: str) -> AccountResult:
        """
        Aggiorna nome e/o email dell'utente.

        FLUSSO:
          1. Normalizza name e email (strip + lower)
          2. Valida name non vuoto
          3. Valida formato email
          4. Recupera utente dal DB (find_by_id)
          5. Se email cambiata: controlla unicità (exists_by_email escludendo se stesso)
          6. Aggiorna i campi sull'oggetto User
          7. Persiste con user_repository.update()
          8. Restituisce AccountResult.ok()

        CHIAMATO DA: UpdateProfileView.post()

        :param user_id: UUID dal JWT (non da input utente)
        :param new_name: Nuovo nome da impostare
        :param new_email: Nuova email da impostare
        :return: AccountResult
        """
        new_name  = new_name.strip()
        new_email = new_email.strip().lower()

        if not new_name:
            return AccountResult.failure("Il nome non può essere vuoto.")
        if not self._EMAIL_RE.match(new_email):
            return AccountResult.failure("Indirizzo email non valido.")

        user = self._user_repo.find_by_id(user_id)
        if user is None:
            return AccountResult.failure("Utente non trovato.")

        # Controlla unicità solo se l'email sta effettivamente cambiando
        if new_email != user.email and self._user_repo.exists_by_email(new_email):
            return AccountResult.failure("Email già in uso da un altro account.")

        # Aggiorna in-memory e persiste
        user.name  = new_name
        user.email = new_email
        self._user_repo.update(user)
        return AccountResult.ok()

    def change_password(
        self,
        user_id:          str,
        current_password: str,
        new_password:     str,
    ) -> AccountResult:
        """
        Cambia la password dell'utente dopo verifica di quella attuale.

        FLUSSO:
          1. Recupera utente dal DB
          2. Valida lunghezza nuova password
          3. Verifica password attuale con bcrypt.checkpw
          4. Hash della nuova password
          5. Aggiorna e persiste

        SICUREZZA:
          La verifica della password attuale (step 3) garantisce che anche
          se il JWT fosse compromesso, l'attaccante non può cambiare la password
          senza conoscere quella attuale.

        CHIAMATO DA: ChangePasswordView.post()

        :param user_id: UUID dal JWT
        :param current_password: Password attuale in chiaro (per verifica)
        :param new_password: Nuova password in chiaro (verrà hashata)
        :return: AccountResult
        """
        user = self._user_repo.find_by_id(user_id)
        if user is None:
            return AccountResult.failure("Utente non trovato.")

        if len(new_password) < self._MIN_PASSWORD_LEN:
            return AccountResult.failure(
                f"La nuova password deve contenere almeno {self._MIN_PASSWORD_LEN} caratteri."
            )

        # Verifica password attuale: confronto bcrypt in tempo costante
        if not bcrypt.checkpw(
            current_password.encode("utf-8"),
            user.hashed_password.encode("utf-8"),
        ):
            return AccountResult.failure("Password attuale non corretta.")

        # Hash nuova password e aggiorna
        user.hashed_password = bcrypt.hashpw(
            new_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        self._user_repo.update(user)
        return AccountResult.ok()

    def delete_account(self, user_id: str, password: str) -> AccountResult:
        """
        Elimina l'account e tutti i dati correlati dell'utente.

        FLUSSO (ORDINE CRITICO):
          1. Recupera utente dal DB
          2. Verifica password (conferma esplicita prima di eliminare)
          3. Elimina statistiche (stats_repository.delete_user_stats)
          4. Elimina utente (user_repository.delete)

        ORDINE ELIMINAZIONE:
          Le statistiche vengono eliminate PRIMA dell'utente.
          Se le tabelle *_stats avessero FOREIGN KEY verso users.id,
          eliminare prima l'utente causerebbe un errore di integrità.
          Questo ordine è corretto anche senza FK esplicite.

        CHIAMATO DA: DeleteAccountView.post()

        :param user_id: UUID dal JWT
        :param password: Password in chiaro (conferma prima dell'eliminazione)
        :return: AccountResult
        """
        user = self._user_repo.find_by_id(user_id)
        if user is None:
            return AccountResult.failure("Utente non trovato.")

        # Richiede conferma password prima dell'eliminazione irreversibile
        if not bcrypt.checkpw(
            password.encode("utf-8"),
            user.hashed_password.encode("utf-8"),
        ):
            return AccountResult.failure("Password non corretta.")

        # 1. Elimina stats (tris_stats, dama_stats, reaction_stats)
        self._stats_repo.delete_user_stats(user_id)
        # 2. Elimina utente (users)
        self._user_repo.delete(user_id)
        return AccountResult.ok()
