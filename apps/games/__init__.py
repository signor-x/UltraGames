"""
Package apps.games — App Django per i giochi (Dama, Tris, Reaction Test).

Contiene le view HTTP per tutti e tre i giochi. Ogni gioco ha
la propria factory di servizio (singleton lazy) e le proprie URL.

CONTENUTO:
  views/         → CBV per tutti i giochi
  urls_dama.py   → /dama/*
  urls_tris.py   → /tris/*
  urls_reaction.py → /reaction/*
"""
