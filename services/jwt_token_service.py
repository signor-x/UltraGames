"""
JwtTokenService — Generazione e verifica dei token JWT (SRP).

RESPONSABILITÀ (SRP):
  Questo servizio gestisce SOLO la firma e la decodifica dei JWT.
  Non sa nulla di utenti, sessioni Django né cookie.

LIBRERIA: PyJWT (pip install PyJWT)
  Gestisce la generazione e la verifica di JSON Web Tokens standard (RFC 7519).

STRUTTURA DEL JWT:
  Un JWT è composto da tre parti separate da ".":
    HEADER.PAYLOAD.SIGNATURE

  Header:  {"alg": "HS256", "typ": "JWT"}
  Payload: {"sub": "<user_id>", "email": "<email>", "name": "<name>", "exp": <timestamp>}
  Signature: HMAC-SHA256(base64(header) + "." + base64(payload), SECRET_KEY)

  La firma garantisce che il payload non sia stato alterato.
  Il SECRET_KEY è in settings.SECRET_KEY (variabile d'ambiente).

ALGORITMO HS256 (HMAC-SHA256):
  Algoritmo simmetrico: firma e verifica usano la stessa chiave (SECRET_KEY).
  Adeguato per sistemi con un solo server. Per sistemi distribuiti multi-server
  considerare RS256 (asimmetrico: firma con chiave privata, verifica con pubblica).

SOLID PRINCIPLES:
  - SRP: Solo JWT sign/verify. Nessuna logica di business.
  - DIP: AuthService e JwtAuthMiddleware dipendono da JwtTokenService tramite
    il container (non lo istanziano direttamente). Sostituibile con un mock
    nei test (es. MockTokenService che restituisce token hardcoded).

PERCORSO CHIAMATA:
  services/container.py
    → _Container.__init__() → self.token_service = JwtTokenService()
  middleware/jwt_middleware.py
    → get_container().token_service.verify(token) → TokenPayload | eccezione
  services/auth_service.py
    → get_container().token_service.generate(payload) → str (JWT firmato)
"""

import jwt
from datetime import datetime, timezone, timedelta
from django.conf import settings

from models.token_payload import TokenPayload


class JwtTokenService:
    """
    Servizio per la creazione e verifica di JSON Web Tokens.

    DIPENDENZA: settings.py deve definire:
      SECRET_KEY         → chiave segreta per la firma HMAC-SHA256
      JWT_EXPIRY_MINUTES → durata di validità del token in minuti
    """

    def generate(self, payload: TokenPayload) -> str:
        """
        Genera un JWT firmato con i dati dell'utente nel payload.

        FLUSSO:
          1. Costruisce il dizionario claims con sub, email, name, exp
          2. Calcola la scadenza: ora + JWT_EXPIRY_MINUTES minuti
          3. Firma con jwt.encode(claims, SECRET_KEY, algorithm="HS256")
          4. Restituisce il token come stringa

        CLAIMS JWT:
          sub   (subject)   → user_id (UUID dell'utente)
          email             → email normalizzata
          name              → nome utente
          exp  (expiration) → timestamp Unix di scadenza (UTC)
            PyJWT verifica automaticamente exp durante verify()
            (lancia ExpiredSignatureError se il token è scaduto)

        CHIAMATO DA:
          AuthService.login() → dopo verifica credenziali
            → token = token_service.generate(TokenPayload(user_id, email, name))
            → Incluso nel cookie dalla view

        :param payload: TokenPayload con user_id, email, name dell'utente
        :return: Stringa JWT firmata (es. "eyJ0eXA...xyz")
        """
        expiry = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_EXPIRY_MINUTES
        )
        claims = {
            "sub":   payload.user_id,   # Identificatore dell'utente
            "email": payload.email,     # Per @cbv_require_admin
            "name":  payload.name,      # Per MeView.get()
            "exp":   expiry,            # Scadenza (validata da PyJWT in verify)
        }
        # jwt.encode restituisce str in PyJWT >= 2.0 (era bytes in < 2.0)
        return jwt.encode(claims, settings.SECRET_KEY, algorithm="HS256")

    def verify(self, token: str) -> TokenPayload:
        """
        Verifica e decodifica un JWT, restituendo il TokenPayload.

        FLUSSO:
          1. jwt.decode() verifica la firma HMAC-SHA256
          2. jwt.decode() verifica la scadenza (claim "exp")
          3. Se valido: estrae sub, email, name dal payload decodificato
          4. Costruisce e restituisce TokenPayload

        ECCEZIONI GESTITE DA DJANGO JwtAuthMiddleware (try/except generico):
          jwt.ExpiredSignatureError  → token scaduto
          jwt.InvalidTokenError      → firma errata, token malformato
          KeyError                   → claims mancanti nel payload

        ALGORITMS=[]:
          Il parametro algorithms specifica gli algoritmi accettati.
          Limitare ad ["HS256"] previene attacchi "algorithm confusion"
          (es. un attaccante potrebbe inviare un token con alg="none").

        CHIAMATO DA:
          middleware/jwt_middleware.py → get_container().token_service.verify(token)
          Ogni richiesta HTTP con cookie "access_token" presente.

        :param token: Stringa JWT da verificare
        :return: TokenPayload con i dati dell'utente
        :raises jwt.InvalidTokenError: Se il token non è valido (firma, scadenza, etc.)
        """
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return TokenPayload(
            user_id=decoded["sub"],
            email=decoded["email"],
            name=decoded["name"],
        )
