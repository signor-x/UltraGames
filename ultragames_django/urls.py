"""
URL Configuration principale del progetto UltraGames.

STRUTTURA GERARCHICA URL:
  Django processa le URL dall'alto verso il basso.
  La prima corrispondenza vince (nessun fallback automatico).

  Ogni include() delega il routing al file urls.py dell'app corrispondente.
  I prefissi sono cumulativi: "api/auth/" + "login" → /api/auth/login

MAPPA COMPLETA DEGLI ENDPOINT:

  FRONTEND HTML (apps.pages):
    GET /                    → RootView          (redirect a /login)
    GET /login               → LoginPageView     (pagina HTML login)
    GET /register            → RegisterPageView  (pagina HTML registrazione)
    GET /home                → HomePageView      (home, richiede JWT)
    GET /admin               → AdminPageView     (pannello admin, richiede JWT + admin)
    GET /style/<str:file>    → ServeStyleView    (file CSS statici)
    GET /script/<str:file>   → ServeScriptView   (file JS statici)

  AUTENTICAZIONE (/api/auth/):
    POST /api/auth/register  → RegisterView   [apps/auth_app/views/register_view.py]
    POST /api/auth/login     → LoginView      [apps/auth_app/views/login_view.py]
    POST /api/auth/logout    → LogoutView     [apps/auth_app/views/logout_view.py]
    GET  /api/auth/me        → MeView         [apps/auth_app/views/me_view.py]

  ACCOUNT (/api/account/) [richiede JWT]:
    POST /api/account/profile   → UpdateProfileView  [apps/account/views/]
    POST /api/account/password  → ChangePasswordView [apps/account/views/]
    POST /api/account/delete    → DeleteAccountView  [apps/account/views/]

  STATISTICHE (/api/stats/) [richiede JWT]:
    GET /api/stats/me               → MyStatsView   [apps/stats/views/]
    GET /api/stats/ranking/<game>   → RankingView   [apps/stats/views/]

  ADMIN (/api/admin/) [richiede JWT + email admin]:
    GET  /api/admin/users                    → UserListView    [apps/admin_panel/views/]
    POST /api/admin/users/<user_id>/ban      → BanUserView     [apps/admin_panel/views/]
    POST /api/admin/users/<user_id>/stats    → UpdateStatsView [apps/admin_panel/views/]

  DAMA (/dama/):
    GET  /dama/health  → DamaHealthView  (no auth)
    POST /dama/new     → DamaNewView     [apps/games/views/dama_new_view.py]
    GET  /dama/moves   → DamaMovesView   [apps/games/views/dama_moves_view.py]
    POST /dama/move    → DamaMoveView    [apps/games/views/dama_move_view.py]
    POST /dama/reset   → DamaResetView   [apps/games/views/dama_reset_view.py]

  TRIS (/tris/):
    GET  /tris/health  → TrisHealthView  (no auth)
    POST /tris/new     → TrisNewView     [apps/games/views/tris_new_view.py]
    POST /tris/move    → TrisMoveView    [apps/games/views/tris_move_view.py]
    POST /tris/reset   → TrisResetView   [apps/games/views/tris_reset_view.py]

  REACTION TEST (/reaction/):
    GET  /reaction/health → ReactionHealthView  (no auth)
    POST /reaction/new    → ReactionNewView     [apps/games/views/reaction_new_view.py]
    POST /reaction/start  → ReactionStartView   [apps/games/views/reaction_start_view.py]
    GET  /reaction/phase  → ReactionPhaseView   [apps/games/views/reaction_phase_view.py]
    POST /reaction/click  → ReactionClickView   [apps/games/views/reaction_click_view.py]
    GET  /reaction/stats  → ReactionStatsView   [apps/games/views/reaction_stats_view.py]
    POST /reaction/reset  → ReactionResetView   [apps/games/views/reaction_reset_view.py]

DJANGO URL ROUTING:
  include(module): Carica il file urls.py del modulo specificato e
    aggiunge il prefisso della path() corrente agli URL interni.
  path(prefix, include(...)): Il prefisso viene rimosso dalla URL prima
    di passarla al modulo incluso.
    Es: path("api/auth/", include("apps.auth_app.urls"))
        Richiesta: /api/auth/login → app.auth_app.urls riceve "login"

ORDINE DELLE ROUTE:
  Le rotte più specifiche (con prefisso "api/") vengono prima delle
  rotte generiche (prefisso "" per le pagine HTML). Questo evita
  che una richiesta a /api/auth/login venga gestita dalle pagine.
"""

from django.urls import path, include

urlpatterns = [
    # ── API CORE ─────────────────────────────────────────────────────────
    path("api/auth/",    include("apps.auth_app.urls")),     # Login, register, logout, me
    path("api/account/", include("apps.account.urls")),      # Gestione account (richiede JWT)
    path("api/stats/",   include("apps.stats.urls")),        # Statistiche e classifiche
    path("api/admin/",   include("apps.admin_panel.urls")),  # Pannello admin (richiede admin)

    # ── GIOCHI ───────────────────────────────────────────────────────────
    path("dama/",     include("apps.games.urls_dama")),      # Gioco Dama
    path("tris/",     include("apps.games.urls_tris")),      # Gioco Tris
    path("reaction/", include("apps.games.urls_reaction")),  # Test di Reazione

    # ── FRONTEND HTML ─────────────────────────────────────────────────────
    # Prefisso vuoto: cattura / /login /register /home /admin /style/* /script/*
    # DEVE essere ULTIMA: le route con prefisso specifico vanno prima.
    path("",          include("apps.pages.urls")),           # Pagine HTML + asset statici
]
