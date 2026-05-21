"""
Package di esportazione delle view dell'app stats.

VIEW ESPORTATA:
  StatsView → raggruppa tutti gli endpoint delle statistiche:
    my_stats() → GET /api/stats/me               (statistiche personali)
    ranking()  → GET /api/stats/ranking/<game>   (classifica globale)

  Entrambi richiedono JWT valido (@cbv_require_auth).

PERCORSO FILE:
  StatsView ← apps/stats/views/stats_views.py
"""

from .stats_views import StatsView

__all__ = ["StatsView"]
