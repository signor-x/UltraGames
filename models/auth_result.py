"""
AuthResult — Value Object per il risultato del login (SRP).

RESPONSABILITÀ (SRP):
  Incapsula il risultato di un tentativo di login (successo + token, o fallimento + errore).
  Elimina l'uso di eccezioni per il controllo del flusso nel login.

PATTERN RESULT OBJECT:
  Invece di:
    try: token = auth_service.login(email, pw)
    except BadCredentials: ...

  Si usa:
    result = auth_service.login(email, pw)
    if result.success: ...   ← flusso esplicito, testabile, senza eccezioni

FACTORY METHODS:
  AuthResult.success(token) → login riuscito con JWT
  AuthResult.failure(error) → login fallito con messaggio di errore

PERCORSO CHIAMATA:
  AuthService.login()   → restituisce AuthResult
  LoginView.post()      → controlla result.success → imposta cookie o restituisce 401
"""


class AuthResult:
    """
    Risultato immutabile di un tentativo di login.

    ATTRIBUTI:
      success (bool): True se il login è riuscito
      token   (str):  JWT firmato (solo se success=True)
      error   (str):  Messaggio di errore (solo se success=False)
    """

    def __init__(self, success: bool, token: str = None, error: str = None):
        self.success = success
        self.token   = token
        self.error   = error

    @classmethod
    def success(cls, token: str) -> "AuthResult":
        """Login riuscito: restituisce AuthResult con il JWT."""
        return cls(success=True, token=token)

    @classmethod
    def failure(cls, error: str) -> "AuthResult":
        """Login fallito: restituisce AuthResult con il messaggio di errore."""
        return cls(success=False, error=error)
