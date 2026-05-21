"""
TokenPayload — Value Object per il payload del JWT (SRP).

RESPONSABILITÀ (SRP):
  Incapsula i dati estratti dal JWT verificato.
  È il "biglietto" dell'utente autenticato: contiene user_id, email, name.

  NON contiene il token JWT stesso (quello è nella stringa firmata).
  NON contiene dati sensibili come la password (mai nel JWT).

IMMUTABILITÀ:
  TokenPayload è pensato come oggetto immutabile (Value Object).
  Una volta creato da JwtTokenService.verify(), i suoi attributi non dovrebbero
  essere modificati. In Python non c'è keyword `readonly`, ma la convenzione
  è non modificarli mai dopo la creazione.

PERCORSO CHIAMATA:
  JwtTokenService.generate(payload: TokenPayload) → str (JWT firmato)
    ← AuthService.login() crea TokenPayload prima di generate()
  JwtTokenService.verify(token) → TokenPayload
    ← JwtAuthMiddleware assegna a request.current_user
  MeView.get()
    → request.current_user (TokenPayload) → {"id", "email", "name"}
  @cbv_require_admin
    → request.current_user.email confrontata con settings.ADMIN_EMAIL
"""


class TokenPayload:
    """
    Payload del JWT: dati dell'utente autenticato.

    ATTRIBUTI:
      user_id (str): UUID dell'utente (claim "sub" nel JWT)
      email   (str): Email normalizzata (claim "email")
      name    (str): Nome dell'utente (claim "name")

    ACCEDUTO DA:
      request.current_user.user_id → tutte le view protette (per operazioni DB)
      request.current_user.email   → @cbv_require_admin (confronto ADMIN_EMAIL)
      request.current_user.name    → MeView.get() (risposta /api/auth/me)
    """

    def __init__(self, user_id: str, email: str, name: str):
        """
        :param user_id: UUID dell'utente (dal claim "sub" del JWT)
        :param email: Email normalizzata a lowercase
        :param name: Nome visualizzato dell'utente
        """
        self.user_id: str = user_id
        self.email:   str = email
        self.name:    str = name
