"""
ReactionScoringService — Calcolo del rating dal tempo di reazione (SRP).

RESPONSABILITÀ (SRP):
  Contiene SOLO la logica di rating: dato un tempo in ms, restituisce
  una valutazione (label + emoji). Non gestisce sessioni né statistiche.

SOLID PRINCIPLES:
  - SRP: Una sola responsabilità → calcolare il rating.
  - OCP: Per aggiungere nuove fasce di rating (es. "SOVRUMANO" < 150ms),
    basta aggiungere una tupla a _THRESHOLDS senza modificare il metodo rate().
  - DIP: ReactionApplicationService riceve ReactionScoringService come
    dipendenza iniettata dalla factory, non la istanzia internamente.

THRESHOLDS:
  Lista di (soglia_ms, label, emoji) ordinata dal più veloce al più lento.
  rate() restituisce la prima soglia che reaction_ms non supera.

PERCORSO CHIAMATA:
  reaction_service_factory.get_reaction_service()
    → ReactionApplicationService(scoring_service=ReactionScoringService(), ...)
  ReactionApplicationService.register_click(sid, click_at_ms)
    → rating = self._scoring.rate(reaction_ms)  ← questo file
    → Incluso nella risposta /reaction/click
"""

from typing import Optional


class ReactionScoringService:
    """
    Servizio di rating per il Reaction Test.

    THRESHOLDS (fasce di valutazione):
      ≤ 200ms → FULMINE   ⚡ (riflessi eccezionali)
      ≤ 300ms → ECCELLENTE 🚀
      ≤ 400ms → BUONO     👍
      ≤ 500ms → NORMALE   😐
       > 500ms → LENTO    🐢

    CHIAMATO DA:
      ReactionApplicationService.register_click()
    """

    # Lista ordinata dal più veloce al più lento.
    # Ogni elemento: (soglia_ms, label, emoji)
    # rate() usa il primo elemento con soglia >= reaction_ms.
    _THRESHOLDS = [
        (200, "FULMINE",    "⚡"),
        (300, "ECCELLENTE", "🚀"),
        (400, "BUONO",      "👍"),
        (500, "NORMALE",    "😐"),
    ]
    _FALLBACK = ("LENTO", "🐢")   # Usato se reaction_ms supera tutti i threshold

    def rate(self, reaction_ms: int) -> Optional[dict]:
        """
        Calcola il rating per il tempo di reazione dato.

        ALGORITMO:
          Scorre _THRESHOLDS in ordine crescente.
          Restituisce la prima fascia il cui threshold >= reaction_ms.
          Se reaction_ms > 500: restituisce il fallback "LENTO".
          Se reaction_ms <= 0 (early click): restituisce None.

        CHIAMATO DA:
          ReactionApplicationService.register_click()
            → rating = scoring_service.rate(reaction_ms)
            → incluso nel dict di risposta come "rating"

        :param reaction_ms: Tempo di reazione in ms (0 se early click)
        :return: {"label": str, "emoji": str} oppure None se early click
        """
        # Early click o valore non valido: nessun rating
        if reaction_ms <= 0:
            return None

        for threshold, label, emoji in self._THRESHOLDS:
            if reaction_ms <= threshold:
                return {"label": label, "emoji": emoji}

        # Superati tutti i threshold: rating minimo
        label, emoji = self._FALLBACK
        return {"label": label, "emoji": emoji}
