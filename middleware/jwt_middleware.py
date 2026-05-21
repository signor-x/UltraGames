"""
JwtAuthMiddleware — Middleware Django per l'autenticazione JWT tramite cookie.

PATTERN MIDDLEWARE DJANGO:
  Django processa ogni richiesta HTTP attraverso una catena di middleware
  (definita in settings.MIDDLEWARE) prima di consegnarla alla view.
  L'ordine in settings.MIDDLEWARE è IMPORTANTE: JwtAuthMiddleware deve
  essere incluso PRIMA di qualsiasi view che usa @cbv_require_auth.

  FLUSSO DJANGO: Request → [Middleware 1] → [JwtAuthMiddleware] → [View] → Response

RESPONSABILITÀ (SRP):
  Questo middleware ha UNA sola responsabilità:
    Estrarre il JWT dal cookie "access_token", decodificarlo e iniettare
    il TokenPayload (o None) in request.current_user.
  NON decide se bloccare la richiesta: questa decisione è di @cbv_require_auth.

SEPARAZIONE DELLE RESPONSABILITÀ:
  JwtAuthMiddleware  → "Chi è l'utente?" (autenticazione)
  @cbv_require_auth  → "Può accedere?" (autorizzazione)
  @cbv_require_admin → "È un amministratore?" (autorizzazione elevata)

  Questo rispetta SRP e DIP: le view non devono sapere come funziona il JWT,
  ricevono solo request.current_user pronto all'uso.

SOLID PRINCIPLES:
  - SRP: Solo parsing del JWT. La decodifica è in JwtTokenService.
  - DIP: Usa get_container().token_service (iniettato), non JwtTokenService direttamente.
  - OCP: Per aggiungere autenticazione Bearer token (header Authorization),
    si aggiunge la logica di estrazione senza modificare il codice esistente.

PERCORSO CHIAMATA:
  Django dispatch → JwtAuthMiddleware.__call__(request)
    → request.COOKIES.get("access_token")
    → get_container().token_service.verify(token)
      [services/jwt_token_service.py → JwtTokenService.verify()]
    → request.current_user = TokenPayload | None
    → self.get_response(request)  ← continua la catena middleware → view
"""

from services.container import get_container


class JwtAuthMiddleware:
    """
    Middleware Django che autentica le richieste tramite JWT nel cookie.

    CONFIGURAZIONE IN settings.py:
      MIDDLEWARE = [
          ...
          "middleware.jwt_middleware.JwtAuthMiddleware",
          ...
      ]

    COME FUNZIONA:
      Per ogni richiesta HTTP:
        1. Legge il cookie "access_token"
        2. Se presente: chiama JwtTokenService.verify(token)
             - Token valido e non scaduto → request.current_user = TokenPayload
             - Token invalido o scaduto  → request.current_user = None
        3. Se assente: request.current_user = None
        4. Passa la richiesta al prossimo middleware / alla view

      La view (o @cbv_require_auth) decide cosa fare con current_user.

    NESSUNA RISPOSTA DIRETTA:
      Il middleware NON restituisce mai 401 direttamente. Aggiunge solo
      l'attributo current_user. Questo garantisce che endpoint pubblici
      (es. /dama/health, /api/auth/login) funzionino senza token.
    """

    def __init__(self, get_response):
        """
        Costruttore Django per i middleware.

        PATTERN MIDDLEWARE DJANGO:
          get_response è un callable che rappresenta la catena di middleware
          successiva (o la view finale). Il middleware chiama get_response(request)
          per passare la richiesta avanti nella catena.

        :param get_response: Callable Django fornito automaticamente dal framework
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Entry point del middleware, chiamato da Django per ogni richiesta HTTP.

        FLUSSO:
          1. Estrae "access_token" dai cookie della richiesta
          2. Se presente: tenta verifica con JwtTokenService
               - Successo → request.current_user = TokenPayload(user_id, email, name)
               - Fallimento → request.current_user = None (token invalido/scaduto)
          3. Se assente: request.current_user = None
          4. Chiama self.get_response(request) → passa al middleware successivo/view
          5. Restituisce la response senza modificarla

        GESTIONE ECCEZIONI:
          Il try/except generico cattura qualsiasi errore di decodifica JWT
          (firma errata, token malformato, payload mancante, etc.) e imposta
          current_user=None senza propagare l'eccezione. Questo garantisce
          che un token corrotto non causi un crash del server.

        :param request: HttpRequest Django (oggetto mutabile)
        :return: HttpResponse prodotta dalla view o dai middleware successivi
        """
        token = request.COOKIES.get("access_token")

        if token:
            try:
                # JwtTokenService.verify() decodifica e valida il JWT.
                # Restituisce TokenPayload o lancia eccezione se invalido.
                request.current_user = get_container().token_service.verify(token)
            except Exception:
                # Token corrotto, firma errata, scaduto: utente non autenticato
                request.current_user = None
        else:
            # Nessun cookie: richiesta anonima (login, register, health check)
            request.current_user = None

        # Passa la richiesta (con current_user già impostato) alla view
        return self.get_response(request)
