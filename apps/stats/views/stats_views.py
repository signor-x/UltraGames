"""
stats_views.py — Gestore unificato delle view per le statistiche di gioco.

STRUTTURA DEL FILE:
  StatsView → classe gestore con i metodi HTTP dell'area statistiche:
                my_stats()  GET /api/stats/me
                ranking()   GET /api/stats/ranking/<game>

PERCORSO CHIAMATA (URL → metodo):
  ultragames_django/urls.py
    → include("apps.stats.urls")    [apps/stats/urls.py]
      → StatsView.my_stats()  GET /api/stats/me
      → StatsView.ranking()   GET /api/stats/ranking/<game>

PATTERN OCP (Open/Closed Principle) in ranking():
  _RANKING_HANDLERS è un dizionario {game: lambda} che mappa il nome del
  gioco alla funzione del repository corrispondente.
  Per aggiungere la classifica di un nuovo gioco (es. "scacchi"):
    - Aggiungere "scacchi": lambda repo: repo.get_scacchi_ranking()
    - NON modificare la classe StatsView né il metodo ranking()

SOLID PRINCIPLES:
  - SRP: Ogni metodo gestisce un solo endpoint; la logica DB è nei repository.
  - DIP: Usa get_container() per ottenere stats_repository iniettato.
  - OCP: Nuovo gioco = nuova entry in _RANKING_HANDLERS, zero modifiche alla classe.
"""

from django.http import JsonResponse
from django.views import View
from apps.core.action_view import ActionView

from services.container import get_container
from services.auth_helpers import cbv_require_auth

# Mappa: nome gioco → funzione handler che riceve il repository e restituisce la classifica.
# Pattern OCP: aggiungere un nuovo gioco richiede solo una nuova entry qui.
# Il lambda mantiene il riferimento al metodo del repository senza istanziarlo subito
# (lazy binding: il repository viene ottenuto al momento della chiamata tramite get_container()).
_RANKING_HANDLERS = {
    "tris":     lambda repo: repo.get_tris_ranking(),
    "dama":     lambda repo: repo.get_dama_ranking(),
    "reaction": lambda repo: repo.get_reaction_ranking(),
}


class StatsView(ActionView, View):
    """
    Gestore unificato delle view per le statistiche di gioco.

    Raccoglie in un'unica classe gli endpoint delle statistiche,
    condividendo le dipendenze (get_container, cbv_require_auth) senza duplicazioni.

    ENDPOINT GESTITI:
      GET /api/stats/me               → my_stats()  (statistiche personali)
      GET /api/stats/ranking/<game>   → ranking()   (classifica globale)

    Entrambi richiedono JWT valido (@cbv_require_auth nel metodo).
    """

    # ── my_stats ──────────────────────────────────────────────────────────────

    @cbv_require_auth
    def my_stats(self, request):
        """
        Restituisce le statistiche di gioco dell'utente autenticato.

        ENDPOINT: GET /api/stats/me
        AUTENTICAZIONE: Richiesta (@cbv_require_auth → JWT valido nel cookie).

        RISPOSTA SUCCESSO (200):
          {
            "tris":     {"wins": 5, "losses": 3, "draws": 1},
            "dama":     {"wins": 2, "losses": 4},
            "reaction": {"best_ms": 210, "attempts": 15}
          }

        RISPOSTA ERRORE (401): {"error": "Non autenticato."}

        DIFFERENZA CON /reaction/stats:
          Questo endpoint restituisce le statistiche globali dal DATABASE
          (best_ms assoluto, numero totale di tentativi su tutte le sessioni).
          /reaction/stats restituisce le statistiche della sessione corrente in-memory.

        NOTA: Se l'utente non ha mai giocato a un gioco, i contatori saranno
        zero (il repository usa valori di fallback se la riga è assente).

        PERCORSO:
          → get_container().stats_repository.get_user_stats(user_id)
            [services/stats_repository.py]
              → SELECT da tris_stats, dama_stats, reaction_stats
        """
        self.allowed_methods = ["GET"]
        data = get_container().stats_repository.get_user_stats(
            request.current_user.user_id
        )
        return JsonResponse(data)

    # ── ranking ───────────────────────────────────────────────────────────────

    @cbv_require_auth
    def ranking(self, request, game: str):
        """
        Restituisce la classifica globale per il gioco specificato nel path.

        ENDPOINT: GET /api/stats/ranking/<game>
          game = "tris"     → classifica Tris (ordine: wins DESC, losses ASC)
          game = "dama"     → classifica Dama (ordine: wins DESC, losses ASC)
          game = "reaction" → classifica Reaction Test (ordine: best_ms ASC)

        RISPOSTA SUCCESSO (200):
          {"ranking": [{"name": "Mario", "wins": 10, ...}, ...]}

        RISPOSTA ERRORI:
          404 {"error": "Gioco 'xyz' non supportato."}  ← game non in _RANKING_HANDLERS
          401 {"error": "Non autenticato."}

        PATTERN OCP:
          Il routing al metodo repository corretto avviene tramite _RANKING_HANDLERS,
          un dizionario definito a livello di modulo. Aggiungere un nuovo gioco
          richiede solo una nuova entry nel dizionario, senza modificare questo metodo.

        PERCORSO:
          → _RANKING_HANDLERS[game](get_container().stats_repository)
            [services/stats_repository.py]
              → get_tris_ranking() / get_dama_ranking() / get_reaction_ranking()
        """
        self.allowed_methods = ["GET"]
        handler = _RANKING_HANDLERS.get(game)
        if handler is None:
            return JsonResponse(
                {"error": f"Gioco '{game}' non supportato."},
                status=404,
            )

        rows = handler(get_container().stats_repository)
        return JsonResponse({"ranking": rows})
