"""
Package dama.models — Entità di dominio della Dama.

MODELLI:
  Piece      → Pezzo immutabile (@dataclass frozen): colore + tipo (pedina/dama)
  Move       → Value Object: percorso + pezzi catturati
  Board      → Scacchiera 8x8 come dizionario sparso {(r,c): Piece}
  GameState  → Stato aggregato: board + turno + status + contatori

NOTA:
  Nessuno di questi modelli è un django.db.models.Model.
  Il progetto usa MariaDB direttamente (InDatabaseUserRepository/StatsRepository).
  Questi sono POPO (Plain Old Python Objects) senza dipendenze Django.
"""
