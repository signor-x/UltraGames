"""
action_view.py — Mixin base per il routing action-based nelle classi gestore.

PROBLEMA RISOLTO:
  Django's View.dispatch() instrada le richieste HTTP per verbo (get → self.get(),
  post → self.post(), ecc.). Questo funziona bene con classi che hanno un solo
  metodo per verbo, ma non permette di avere più metodi POST o GET nella stessa
  classe (es. TrisView.new, TrisView.move, TrisView.reset sono tutti POST).

SOLUZIONE — PATTERN ACTION DISPATCH:
  ActionView sovrascrive dispatch() per leggere self.action (un nome di metodo)
  e chiamarlo direttamente, ignorando il verbo HTTP come meccanismo di routing.

  Utilizzo negli URL:
    path("new",   TrisView.as_view(action="new")),
    path("move",  TrisView.as_view(action="move")),
    path("reset", TrisView.as_view(action="reset")),

  Django's View.__init__ setta i kwarg di as_view() come attributi dell'istanza:
    TrisView.as_view(action="new") → self.action = "new"
  Poi ActionView.dispatch() chiama self.new(request, *args, **kwargs).

CSRF:
  @method_decorator(csrf_exempt, name="dispatch") applicato sulle classi gestore
  continua a funzionare: csrf_exempt decora dispatch(), che ora è questo metodo.
  Il wrapper csrf_exempt non cambia il comportamento del routing; disabilita solo
  la verifica del token CSRF per le richieste POST.

COMPATIBILITÀ:
  ActionView è pensato per essere combinato con django.views.View:
    class TrisView(JsonBodyMixin, ActionView, View): ...
  MRO garantisce che ActionView.dispatch() venga trovato prima di View.dispatch().

SOLID PRINCIPLES:
  - SRP: Gestisce SOLO il meccanismo di routing action-based.
  - OCP: Le classi gestore aggiungono metodi senza dover modificare questo mixin.
  - DRY: Il dispatch action-based è scritto una sola volta, riusato da tutte le classi.
"""


class ActionView:
    """
    Mixin che aggiunge il routing action-based alle Django Class-Based View.

    UTILIZZO:
      class MyView(ActionView, View):
          def my_action(self, request):
              ...

      # urls.py
      path("my-url", MyView.as_view(action="my_action"))

    ATTRIBUTO action:
      Viene impostato da View.__init__ tramite as_view(action="nome_metodo").
      Se non specificato, dispatch() restituisce 405 Method Not Allowed.
    """

    action:          str  = ""   # Impostato da as_view(action="...") tramite View.__init__
    allowed_methods: list = []  # Metodi HTTP accettati per questa action ([] = qualsiasi)

    def dispatch(self, request, *args, **kwargs):
        """
        Instrada la richiesta al metodo specificato da self.action,
        dopo aver verificato che il verbo HTTP sia tra quelli consentiti.

        FLUSSO:
          1. Legge self.action (impostato da as_view(action="..."))
          2. Se allowed_methods è definito, verifica che request.method sia ammesso
             → Se no: restituisce 405 Method Not Allowed
          3. Cerca il metodo corrispondente nella classe (getattr)
          4. Se trovato → chiama il metodo con request + args/kwargs URL
          5. Se non trovato → restituisce 405 Method Not Allowed

        :param request: HttpRequest Django
        :param args: Argomenti posizionali da URL (es. parametri di path)
        :param kwargs: Argomenti keyword da URL (es. <str:user_id>)
        :return: HttpResponse dal metodo dell'azione
        """
        if self.action:
            # Valida il verbo HTTP se la route specifica allowed_methods
            if self.allowed_methods and request.method not in self.allowed_methods:
                return self.http_method_not_allowed(request, *args, **kwargs)
            handler = getattr(self, self.action, None)
            if handler is not None:
                return handler(request, *args, **kwargs)

        # Fallback: nessuna action impostata o metodo non trovato → 405
        return self.http_method_not_allowed(request, *args, **kwargs)
