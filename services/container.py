"""
Container — Dependency Injection Container per i servizi core (DIP + SRP).

PATTERN DEPENDENCY INJECTION CONTAINER:
  Il container è responsabile di costruire e collegare tutte le dipendenze
  dell'applicazione (user_repository, stats_repository, token_service,
  auth_service, account_service) in un unico posto.

  Questo elimina l'accoppiamento diretto tra le classi: nessuna view o
  middleware crea direttamente i propri servizi. Si affidano al container.

PATTERN SINGLETON:
  _container_instance è la singola istanza globale del Container.
  get_container() crea il container solo alla prima chiamata (lazy init)
  e restituisce la stessa istanza a tutte le chiamate successive.

  PERCHÉ SINGLETON:
    - I servizi (InDatabaseUserRepository, AuthService, etc.) sono stateless:
      non mantengono stato tra le richieste, quindi una sola istanza è sufficiente.
    - Evita il costo di ricostruzione del grafo di dipendenze ad ogni richiesta.

SOLID PRINCIPLES:
  - SRP: Il container gestisce SOLO la costruzione e il cablaggio dei servizi.
  - DIP: Le view e il middleware dipendono dal container (astrazione di accesso),
    non dalle classi concrete dei servizi.
  - OCP: Per aggiungere un nuovo servizio, si aggiunge un attributo al costruttore
    senza modificare le classi esistenti.

PERCORSO CHIAMATA:
  Django startup (settings.py importa INSTALLED_APPS)
    → Prima chiamata a get_container() da JwtAuthMiddleware o da una view
      → _Container() costruisce il grafo di dipendenze
  Ogni view/middleware:
    → get_container().auth_service / account_service / stats_repository / etc.

GRAFO DI DIPENDENZE COSTRUITO:
  _Container
    ├── user_repository:   InDatabaseUserRepository()   [MariaDB]
    ├── stats_repository:  InDatabaseStatsRepository()  [MariaDB]
    ├── token_service:     JwtTokenService()             [PyJWT]
    ├── auth_service:      AuthService(user_repo, token_svc)
    └── account_service:   AccountService(user_repo, stats_repo)
"""

from services.user_repository   import InDatabaseUserRepository
from services.stats_repository  import InDatabaseStatsRepository
from services.jwt_token_service import JwtTokenService
from services.auth_service      import AuthService
from services.account_service   import AccountService


class _Container:
    """
    Contenitore delle dipendenze core dell'applicazione.

    Non è una classe pubblica (prefisso underscore): l'accesso esterno
    avviene tramite get_container(), non istanziando direttamente _Container.

    ATTRIBUTI PUBBLICI (acceduti dalle view e dal middleware):
      user_repository:   Accesso CRUD agli utenti nel DB
      stats_repository:  Accesso CRUD alle statistiche nel DB
      token_service:     Generazione e verifica JWT
      auth_service:      Login, logout, registrazione
      account_service:   Cambio profilo, password, eliminazione account
    """

    def __init__(self):
        """
        Costruisce il grafo completo di dipendenze una sola volta.

        ORDINE DI COSTRUZIONE:
          1. Repository (foglie del grafo: non dipendono da altri servizi)
          2. token_service (dipende solo dalla config in settings)
          3. auth_service (dipende da user_repository e token_service)
          4. account_service (dipende da user_repository e stats_repository)
        """
        # ── Livello 1: Repository (nessuna dipendenza da altri servizi) ──
        self.user_repository   = InDatabaseUserRepository()   # MariaDB users
        self.stats_repository  = InDatabaseStatsRepository()  # MariaDB *_stats

        # ── Livello 2: Infrastruttura (indipendente dai repository) ──
        self.token_service     = JwtTokenService()            # JWT sign/verify

        # ── Livello 3: Servizi applicativi (dipendono dai livelli 1 e 2) ──
        self.auth_service      = AuthService(
            user_repository=self.user_repository,
            token_service=self.token_service,
        )
        self.account_service   = AccountService(
            user_repository=self.user_repository,
            stats_repository=self.stats_repository,
        )


# Singleton: inizializzato a None, creato alla prima chiamata di get_container()
_container_instance: _Container = None


def get_container() -> _Container:
    """
    Restituisce il singleton del container di dipendenze.

    PATTERN LAZY SINGLETON:
      Prima chiamata: crea _Container() e lo salva in _container_instance
      Chiamate successive: restituisce l'istanza già creata (O(1))

    THREAD SAFETY:
      In un server Django single-process (sviluppo con runserver), il singleton
      è thread-safe grazie al GIL di Python. In produzione multi-worker
      (Gunicorn), ogni worker ha il suo processo e quindi il proprio singleton
      (comportamento corretto: ogni worker ha le proprie connessioni DB).

    CHIAMATO DA:
      middleware/jwt_middleware.py  → token_service
      apps/auth_app/views/*.py      → auth_service
      apps/account/views/*.py       → account_service
      apps/admin_panel/views/*.py   → user_repository, stats_repository
      apps/stats/views/*.py         → stats_repository
      apps/games/views/dama_*_view.py → stats_repository
      apps/games/views/tris_*_view.py → stats_repository
      apps/games/views/reaction_*_view.py → stats_repository

    :return: Istanza singleton di _Container
    """
    global _container_instance
    if _container_instance is None:
        _container_instance = _Container()
    return _container_instance
