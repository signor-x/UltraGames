"""
TimerStrategy — Strategia per il delay del semaforo verde (OCP + DIP + LSP).

PATTERN STRATEGY (GoF):
  Definisce l'interfaccia TimerStrategy (ABC) per calcolare il delay prima
  che il semaforo diventi verde. RandomTimerStrategy è l'implementazione
  di default; FixedTimerStrategy può essere usata nei test (DIP).

SOLID PRINCIPLES:
  - OCP: Aggiungere nuovi comportamenti di delay (es. delay crescente con
    l'esperienza dell'utente) richiede solo una nuova classe che implementa
    TimerStrategy. Nessuna modifica a ReactionApplicationService.
  - LSP: Qualsiasi implementazione di TimerStrategy è intercambiabile.
    ReactionApplicationService funziona identicamente con Random o Fixed.
  - DIP: ReactionApplicationService dipende da TimerStrategy (astrazione),
    non da RandomTimerStrategy (concreta).

PERCORSO CHIAMATA:
  reaction_service_factory.get_reaction_service()
    → ReactionApplicationService(timer_strategy=RandomTimerStrategy(), ...)
  ReactionApplicationService.start_round(sid)
    → delay = self._timer.delay_seconds()       ← questo file
    → Thread(target=_set_green, args=(session, delay)).start()
"""

import random
from abc import ABC, abstractmethod


class TimerStrategy(ABC):
    """
    Interfaccia astratta per la strategia di delay del Reaction Test (DIP).
    Garantisce LSP: ogni implementazione è usabile dove è attesa TimerStrategy.
    """

    @abstractmethod
    def delay_seconds(self) -> float:
        """
        Restituisce il numero di secondi di attesa prima del semaforo verde.

        :return: Durata del delay in secondi (float)
        """
        ...


class RandomTimerStrategy(TimerStrategy):
    """
    Delay casuale tra MIN_DELAY e MAX_DELAY secondi.

    UTILIZZO: Implementazione di default in produzione.
    Il range casuale impedisce all'utente di anticipare il verde.

    ATTRIBUTI DI CLASSE:
      MIN_DELAY: Minimo tempo di attesa (evita click troppo veloci)
      MAX_DELAY: Massimo tempo di attesa (non annoiare l'utente)
    """

    MIN_DELAY = 2.0   # Secondi minimi di attesa
    MAX_DELAY = 5.0   # Secondi massimi di attesa

    def delay_seconds(self) -> float:
        """
        Genera un delay casuale nell'intervallo [MIN_DELAY, MAX_DELAY].

        CHIAMATO DA:
          ReactionApplicationService.start_round()
            → delay_ms = timer.delay_seconds() * 1000
            → Thread(..., delay=delay_ms).start()

        :return: Float in [2.0, 5.0] secondi
        """
        return random.uniform(self.MIN_DELAY, self.MAX_DELAY)


class FixedTimerStrategy(TimerStrategy):
    """
    Delay fisso, utile per test deterministici.

    UTILIZZO: Nei test unitari, sostituisce RandomTimerStrategy per
    avere comportamento prevedibile (DIP + LSP).

    ESEMPIO TEST:
      service = ReactionApplicationService(
          ...,
          timer_strategy=FixedTimerStrategy(delay=0.01),  # 10ms nei test
      )
    """

    def __init__(self, delay: float = 1.0):
        """
        :param delay: Delay fisso in secondi (default 1.0)
        """
        self._delay = delay

    def delay_seconds(self) -> float:
        """Restituisce sempre il delay fisso specificato nel costruttore."""
        return self._delay
