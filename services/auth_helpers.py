"""
auth_helpers — Decoratori di autorizzazione per le Class-Based Views Django.

RESPONSABILITÀ (SRP):
  Fornisce decoratori riutilizzabili che verificano l'autenticazione e
  l'autorizzazione prima che il metodo della view venga eseguito.

  cbv_require_auth  → Verifica JWT valido (request.current_user non None)
  cbv_require_admin → Verifica JWT valido E email = ADMIN_EMAIL

PATTERN DECORATOR:
  Un decorator Python è una funzione che riceve una funzione e ne restituisce
  un'altra con comportamento aggiuntivo (wrapper).

  @cbv_require_auth applicato a un metodo CBV:
    1. Sostituisce il metodo con wrapper()
    2. Ogni volta che la view viene chiamata, Django esegue wrapper()
    3. wrapper() verifica current_user e:
         - Se None → restituisce 401 senza eseguire il metodo originale
         - Se valido → esegue il metodo originale (fn(self, request, *args, **kwargs))

DIFFERENZA CON @method_decorator(login_required):
  Django built-in login_required usa le sessioni Django.
  cbv_require_auth usa request.current_user impostato da JwtAuthMiddleware.
  Nessuna sessione Django è necessaria (autenticazione stateless con JWT).

SOLID PRINCIPLES:
  - SRP: Ogni decorator ha una sola responsabilità (auth vs admin).
  - OCP: Per aggiungere un nuovo livello di autorizzazione (es. @require_staff),
    si aggiunge un nuovo decorator senza modificare quelli esistenti.
  - DRY: Il controllo if request.current_user is None è scritto una volta
    in cbv_require_auth e riutilizzato in tutti i metodi delle view.

PERCORSO UTILIZZO:
  Definiti qui → importati nelle view:
    apps/auth_app/views/me_view.py             → @cbv_require_auth
    apps/account/views/*.py                    → @cbv_require_auth
    apps/admin_panel/views/*.py                → @cbv_require_admin
    apps/stats/views/*.py                      → @cbv_require_auth
    apps/games/views/dama_*_view.py            → @cbv_require_auth
    apps/games/views/tris_*_view.py            → @cbv_require_auth
    apps/games/views/reaction_*_view.py        → @cbv_require_auth

DIPENDENZA DA JwtAuthMiddleware:
  I decorator assumono che JwtAuthMiddleware abbia già impostato
  request.current_user prima dell'esecuzione della view.
  Se il middleware non è nella catena (settings.MIDDLEWARE), i decorator
  farebbero crash con AttributeError. L'ordine in MIDDLEWARE è critico.
"""

import functools
from django.conf import settings
from django.http import JsonResponse


def cbv_require_auth(fn):
    """
    Decorator per verificare che l'utente sia autenticato (JWT valido).

    COMPORTAMENTO:
      Se request.current_user is None:
        → Restituisce 401 {"error": "Non autenticato."}
        → Il metodo originale NON viene eseguito
      Se request.current_user è un TokenPayload:
        → Esegue il metodo originale con tutti i suoi argomenti

    UTILIZZO SU CBV:
      class MeView(View):
          @cbv_require_auth      ← decoratore applicato al metodo specifico
          def get(self, request):
              u = request.current_user   ← TokenPayload garantito non-None
              return JsonResponse({"id": u.user_id})

    FUNZIONAMENTO INTERNO (functools.wraps):
      @functools.wraps(fn) preserva il nome e la docstring del metodo originale.
      Senza wraps, il metodo si chiamerebbe "wrapper" invece di "get"/"post",
      causando problemi con il debug e con strumenti di introspezione.

    :param fn: Metodo della view (get, post, etc.) da proteggere
    :return: Funzione wrapper che verifica l'autenticazione prima di chiamare fn
    """
    @functools.wraps(fn)
    def wrapper(self, request, *args, **kwargs):
        # request.current_user è impostato da JwtAuthMiddleware.
        # None = nessun cookie, cookie scaduto, o firma JWT non valida.
        if request.current_user is None:
            return JsonResponse({"error": "Non autenticato."}, status=401)
        # Autenticato: esegui il metodo originale
        return fn(self, request, *args, **kwargs)
    return wrapper


def cbv_require_admin(fn):
    """
    Decorator per verificare che l'utente sia autenticato E amministratore.

    COMPORTAMENTO:
      1. Se request.current_user is None → 401 (non autenticato)
      2. Se email != settings.ADMIN_EMAIL → 403 (non autorizzato)
      3. Se entrambe le verifiche passano → esegue il metodo originale

    VERIFICA ADMIN:
      L'admin è identificato dall'email nel payload JWT confrontata con
      settings.ADMIN_EMAIL (variabile d'ambiente ADMIN_EMAIL in .env).
      Non c'è un flag "is_admin" nel DB: l'email è l'unica verifica.

      Implicazione: se ADMIN_EMAIL viene cambiata in .env, il vecchio admin
      perde i privilegi al prossimo deploy senza modifiche al DB.

    UTILIZZO:
      class UserListView(View):
          @cbv_require_admin
          def get(self, request):
              ...  ← eseguito solo se admin verificato

    :param fn: Metodo della view da proteggere
    :return: Funzione wrapper con doppia verifica auth + admin
    """
    @functools.wraps(fn)
    def wrapper(self, request, *args, **kwargs):
        # Verifica 1: autenticazione (stessa logica di cbv_require_auth)
        if request.current_user is None:
            return JsonResponse({"error": "Non autenticato."}, status=401)

        # Verifica 2: autorizzazione admin
        # Confronto email (già normalizzata a lowercase nel token e nel setting)
        if request.current_user.email != settings.ADMIN_EMAIL:
            return JsonResponse({"error": "Accesso non autorizzato."}, status=403)

        # Entrambe le verifiche passate: esegui il metodo admin
        return fn(self, request, *args, **kwargs)
    return wrapper
