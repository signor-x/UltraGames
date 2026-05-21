"""
Package di esportazione delle view del frontend (pages app).

VIEW ESPORTATA:
  PagesView → raggruppa tutti gli endpoint di serving del frontend:
    root()           → GET /              (redirect a /login)
    login_page()     → GET /login         (serve login.html)
    register_page()  → GET /register      (serve register.html)
    home_page()      → GET /home          (serve home.html, richiede JWT)
    admin_page()     → GET /admin         (serve admin.html, richiede JWT + admin)
    serve_script()   → GET /script/<file> (serve JS da frontend/static/js/)
    serve_style()    → GET /style/<file>  (serve CSS da frontend/static/css/)

PERCORSO FILE:
  PagesView           ← apps/pages/views/pages_views.py
  TemplateReaderMixin ← apps/pages/views/template_reader_mixin.py  (invariato)
"""

from .pages_views import PagesView

__all__ = ["PagesView"]
