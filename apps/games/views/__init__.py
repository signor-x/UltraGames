"""
Package di esportazione delle view dell'app games (Dama, Tris, Reaction Test).

PATTERN __init__.py:
  Ri-esporta le classi gestore e i metodi as_view() usati dai file urls_*.py.
  Ogni gioco ha ora un'unica classe che raggruppa tutti i suoi endpoint:

    TrisView     (tris_views.py)     → health, new, move, reset
    DamaView     (dama_views.py)     → health, new, moves, move, reset
    ReactionView (reaction_views.py) → health, new, start, phase, click, stats, reset

VIEWS ESPORTATE PER GIOCO:

  TRIS (urls_tris.py):
    TrisView.health  → GET  /tris/health  (health check, no auth)
    TrisView.new     → POST /tris/new     (nuova partita)
    TrisView.move    → POST /tris/move    (esegui mossa + AI risponde)
    TrisView.reset   → POST /tris/reset   (reset partita)

  DAMA (urls_dama.py):
    DamaView.health  → GET  /dama/health  (health check, no auth)
    DamaView.new     → POST /dama/new     (nuova partita)
    DamaView.moves   → GET  /dama/moves   (mosse legali)
    DamaView.move    → POST /dama/move    (esegui mossa + AI risponde)
    DamaView.reset   → POST /dama/reset   (reset partita)

  REACTION TEST (urls_reaction.py):
    ReactionView.health → GET  /reaction/health (health check, no auth)
    ReactionView.new    → POST /reaction/new    (nuova sessione)
    ReactionView.start  → POST /reaction/start  (avvia countdown)
    ReactionView.phase  → GET  /reaction/phase  (polling fase corrente)
    ReactionView.click  → POST /reaction/click  (registra click)
    ReactionView.stats  → GET  /reaction/stats  (statistiche sessione)
    ReactionView.reset  → POST /reaction/reset  (reset sessione)

PERCORSO FILE:
  TrisView     ← apps/games/views/tris_views.py
  DamaView     ← apps/games/views/dama_views.py
  ReactionView ← apps/games/views/reaction_views.py
"""

from .tris_views     import TrisView
from .dama_views     import DamaView
from .reaction_views import ReactionView

__all__ = ["TrisView", "DamaView", "ReactionView"]
