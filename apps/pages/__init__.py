"""
Package apps.pages — App Django per il frontend HTML.

Gestisce la visualizzazione delle pagine HTML e la distribuzione degli
asset statici (CSS, JS). Tutte le view leggono file dal filesystem
tramite TemplateReaderMixin (no Django template engine).

CONTENUTO:
  views/   → CBV per le pagine HTML e gli asset statici
  urls.py  → routing delle pagine (/, /login, /home, /admin, /style/<f>, /script/<f>)
"""
