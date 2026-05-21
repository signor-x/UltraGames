"""
AuthService — Logica di autenticazione e registrazione utenti (SRP).

RESPONSABILITÀ (SRP):
  Gestisce SOLO i use case di autenticazione:
    - login:    Verifica credenziali e genera JWT
    - register: Valida dati, hash password, crea utente

  NON gestisce cookie (→ view), sessioni Django (non usate),
  né accesso diretto al DB (→ InDatabaseUserRepository).

SOLID PRINCIPLES:
  - SRP: Solo logica di autenticazione. Zero accesso diretto al DB.
  - DIP: Dipende da astrazioni iniettate nel costruttore:
      user_repository → InDatabaseUserRepository
      token_service   → JwtTokenService
    Sostituibili con mock nei test unitari senza modificare AuthService.
  - OCP: Per aggiungere autenticazione OAuth (es. Google), si aggiunge
    un metodo senza modificare login() o register().

LIBRERIA BCRYPT:
  bcrypt.hashpw(password.encode(), bcrypt.gensalt()):
    - gensalt(): Genera un salt casuale (costo default=12 rounds)
    - hashpw(): PBKDF con HMAC-SHA256 + salt → hash sicuro
    - Il salt è incluso nell'hash risultante (no storage separato del salt)
  bcrypt.checkpw(password.encode(), stored_hash):
    - Estrae il salt dall'hash, ricalcola e confronta
    - Resistente ad attacchi timing (confronto costante)

PERCORSO CHIAMATA:
  services/container.py
    → _Container.__init__() → AuthService(user_repo, token_svc)
  apps/auth_app/views/login_view.py
    → get_container().auth_service.login(email, password) → AuthResult
  apps/auth_app/views/register_view.py
    → get_container().auth_service.register(email, password, name) → RegisterResult
"""

import uuid
import bcrypt
import re

from models.user import User
from models.auth_result import AuthResult
from models.token_payload import TokenPayload


class AuthService:
    """
    Servizio di autenticazione: login e registrazione.

    DIPENDENZE INIETTATE (DIP):
      user_repository: Per cercare/creare utenti nel DB
      token_service:   Per generare JWT dopo login riuscito
    """

    # Pattern email RFC 5322 semplificato (accetta la maggior parte degli indirizzi validi)
    _EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    _MIN_PASSWORD_LEN = 8

    def __init__(self, user_repository, token_service):
        """
        :param user_repository: InDatabaseUserRepository (iniettato dal container)
        :param token_service: JwtTokenService (iniettato dal container)
        """
        self._user_repo    = user_repository
        self._token_svc    = token_service

    def login(self, email: str, password: str) -> AuthResult:
        """
        Verifica le credenziali e restituisce un JWT se valide.

        FLUSSO:
          1. Normalizza email (strip + lowercase)
          2. Cerca utente per email nel DB (user_repository.find_by_email)
          3. Se non trovato → AuthResult.failure("Credenziali non valide.")
          4. Verifica password con bcrypt.checkpw
          5. Se errata → AuthResult.failure("Credenziali non valide.")
          6. Genera JWT con token_service.generate(TokenPayload)
          7. Restituisce AuthResult.success(token=JWT)

        MESSAGGIO GENERICO DI ERRORE:
          "Credenziali non valide." è usato sia per email non trovata
          che per password errata. Questo previene l'enumerazione degli
          utenti: un attaccante non può sapere se l'email esiste o meno.

        CHIAMATO DA: LoginView.post()

        :param email: Email inserita dall'utente (non ancora normalizzata)
        :param password: Password in chiaro inserita dall'utente
        :return: AuthResult con success=True e token JWT, oppure success=False e error
        """
        email = email.strip().lower()

        # Cerca l'utente nel DB tramite repository (DIP: no SQL diretto)
        user = self._user_repo.find_by_email(email)
        if user is None:
            # Non rivela se l'email esiste o no (security by obscurity)
            return AuthResult.failure("Credenziali non valide.")

        # Verifica la password con bcrypt (confronto in tempo costante)
        if not bcrypt.checkpw(password.encode("utf-8"), user.hashed_password.encode("utf-8")):
            return AuthResult.failure("Credenziali non valide.")

        # Credenziali corrette: genera il JWT con i dati dell'utente
        payload = TokenPayload(user_id=user.id, email=user.email, name=user.name)
        token   = self._token_svc.generate(payload)
        return AuthResult.success(token=token)

    def register(self, email: str, password: str, name: str) -> "RegisterResult":
        """
        Valida i dati di registrazione e crea un nuovo utente.

        FLUSSO:
          1. Normalizza email e name (strip + lowercase)
          2. Valida name (non vuoto)
          3. Valida email (formato regex)
          4. Valida password (lunghezza minima)
          5. Controlla unicità email (user_repository.exists_by_email)
          6. Hash della password con bcrypt
          7. Crea oggetto User con UUID generato
          8. Persiste nel DB (user_repository.create)
          9. Restituisce RegisterResult.success(user_id)

        BCRYPT HASH:
          bcrypt.gensalt() genera un salt casuale di 22 caratteri base64.
          Il costo di default (rounds=12) causa ~100-300ms per hash,
          rendendo gli attacchi brute-force economicamente non conveniente.
          Il salt è incorporato nell'hash risultante (stringa da 60 caratteri).

        CHIAMATO DA: RegisterView.post()

        :param email: Email da registrare
        :param password: Password in chiaro (verrà hashata)
        :param name: Nome visualizzato dell'utente
        :return: RegisterResult con user_id se successo, oppure error
        """
        name  = name.strip()
        email = email.strip().lower()

        # Validazioni sequenziali: la prima che fallisce interrompe
        if not name:
            return RegisterResult.failure("Il nome è obbligatorio.")
        if not self._EMAIL_RE.match(email):
            return RegisterResult.failure("Indirizzo email non valido.")
        if len(password) < self._MIN_PASSWORD_LEN:
            return RegisterResult.failure(
                f"La password deve contenere almeno {self._MIN_PASSWORD_LEN} caratteri."
            )

        # Controlla unicità email PRIMA di hashare la password (risparmio CPU)
        if self._user_repo.exists_by_email(email):
            return RegisterResult.failure("Un account con questa email esiste già.")

        # Hash sicuro della password: PBKDF + salt casuale
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Crea l'oggetto User con ID univoco (UUID4)
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=hashed,
            name=name,
        )
        self._user_repo.create(user)

        return RegisterResult.success(user_id=user.id)


class RegisterResult:
    """
    Value Object che rappresenta il risultato di un tentativo di registrazione.

    PATTERN RESULT OBJECT (invece di eccezioni):
      Restituisce un oggetto con success e error/user_id invece di lanciare
      eccezioni. Questo rende il flusso esplicito e facilita il test.

    FACTORY METHODS:
      RegisterResult.success(user_id) → registrazione riuscita
      RegisterResult.failure(error)   → registrazione fallita con messaggio

    CHIAMATO DA:
      AuthService.register() → crea e restituisce RegisterResult
      RegisterView.post()    → controlla result.success → risposta HTTP
    """

    def __init__(self, success: bool, user_id: str = None, error: str = None):
        self.success = success
        self.user_id = user_id
        self.error   = error

    @classmethod
    def success(cls, user_id: str) -> "RegisterResult":
        """Registrazione riuscita con l'UUID del nuovo utente."""
        return cls(success=True, user_id=user_id)

    @classmethod
    def failure(cls, error: str) -> "RegisterResult":
        """Registrazione fallita con messaggio di errore leggibile."""
        return cls(success=False, error=error)
