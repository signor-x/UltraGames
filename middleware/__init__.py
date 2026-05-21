"""
Package middleware — Middleware Django personalizzati.

MIDDLEWARE:
  JwtAuthMiddleware → Legge il cookie "access_token", verifica il JWT con
    JwtTokenService e inietta request.current_user = TokenPayload | None
    prima che ogni richiesta raggiunga la view.

    Deve essere registrato in settings.MIDDLEWARE dopo i middleware Django
    standard e prima delle view che usano @cbv_require_auth.
"""
