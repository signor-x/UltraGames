"""
Mixin condivisi tra le game views.

PATTERN MIXIN:
  Un Mixin è una classe progettata per essere usata in ereditarietà multipla
  insieme a un'altra classe base (es. View). Aggiunge funzionalità senza
  estendere la classe principale.

  Utilizzo:
    class DamaNewView(JsonBodyMixin, View):
        def post(self, request):
            body = self._parse_body(request)  ← metodo da JsonBodyMixin

SOLID PRINCIPLES:
  - SRP: JsonBodyMixin gestisce SOLO il parsing del body JSON. Non contiene
    logica di business né accesso al database.
  - DRY: Evita la duplicazione del blocco try/except JSON in ogni view di gioco.
    Senza questo mixin, ogni view avrebbe dovuto ripetere lo stesso codice.

PERCORSO CHIAMATA:
  Ogni game view che usa JsonBodyMixin chiama self._parse_body(request)
  nel proprio metodo post() per ottenere il dizionario del body.
  Es: DamaNewView, DamaMoveView, DamaResetView, TrisNewView, TrisMoveView,
      TrisResetView, ReactionStartView, ReactionClickView, ReactionResetView.
"""

import json


class JsonBodyMixin:
    """
    Mixin che fornisce il metodo _parse_body() per leggere JSON dal body HTTP.

    COMPORTAMENTO:
      - Se il body è vuoto: restituisce {}
      - Se il body è JSON valido: restituisce il dizionario Python corrispondente
      - Se il body non è JSON valido (JSONDecodeError) o non è UTF-8
        (UnicodeDecodeError): restituisce {} silenziosamente

    NOTA SUL FALLBACK SILENZIOSO:
      In caso di errore di parsing, viene restituito {} invece di sollevare
      un'eccezione o restituire un errore HTTP. Le view che chiamano questo
      metodo sono responsabili di validare i campi obbligatori e restituire
      un errore 400 se mancanti (es. "sessionId e move obbligatori").
    """

    def _parse_body(self, request) -> dict:
        """
        Decodifica il body JSON della richiesta HTTP.

        CHIAMATO DA:
          DamaNewView.post(), DamaMoveView.post(), DamaResetView.post()
          TrisNewView.post(), TrisMoveView.post(), TrisResetView.post()
          ReactionStartView.post(), ReactionClickView.post(), ReactionResetView.post()

        :param request: HttpRequest Django con body (bytes)
        :return: Dizionario Python dal JSON, oppure {} in caso di errore
        :rtype: dict
        """
        try:
            # request.body è bytes. Viene decodificato se non vuoto.
            # json.loads() supporta sia str che bytes (Python 3.6+).
            return json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Body malformato o non UTF-8: restituisce dizionario vuoto.
            # Le view valideranno i campi obbligatori e risponderanno con 400.
            return {}
