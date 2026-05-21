"""
Package tris.models — Modelli di dominio del Tris.

MODELLI:
  GameState → Board (9 stringhe), current_turn (Player), status (GameStatus),
              winner_combo (List[int] | None)
  Player    → Enum: HUMAN="X", AI="O", EMPTY=""
  GameStatus → Enum: ONGOING, HUMAN_WIN, AI_WIN, DRAW
"""
