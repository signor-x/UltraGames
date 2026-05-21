#!/usr/bin/env python
"""
manage.py — Django Command Line Utility per sviluppo e amministrazione.

SCOPO:
  Script Python eseguibile che permette di lanciare comandi Django da terminale.
  È l'interfaccia di sviluppo: non viene usato in produzione (→ wsgi.py).

COMANDI PRINCIPALI:
  python manage.py runserver          → Server sviluppo su http://127.0.0.1:8000
  python manage.py runserver 0.0.0.0:8080 → Server su tutte le interfacce, porta 8080
  python manage.py shell              → Shell Python interattiva con Django caricato
  python manage.py check              → Verifica configurazione Django senza avviare
  python manage.py migrate            → Applica migrazioni (non usato: no Django ORM)
  python manage.py collectstatic      → Raccoglie file statici (non usato: view dedicate)

FLUSSO DI AVVIO (runserver):
  1. manage.py main():
       os.environ["DJANGO_SETTINGS_MODULE"] = "ultragames_django.settings"
       execute_from_command_line(["manage.py", "runserver"])
  2. Django carica settings.py (MIDDLEWARE, INSTALLED_APPS, ROOT_URLCONF)
  3. Django costruisce la catena middleware (incluso JwtAuthMiddleware)
  4. Django avvia il server HTTP di sviluppo su 127.0.0.1:8000
  5. Per ogni richiesta:
       Django middleware chain → JwtAuthMiddleware → router → view → response

VARIABILE DJANGO_SETTINGS_MODULE:
  Identica a wsgi.py: punta a ultragames_django/settings.py.
  Può essere sovrascritta prima di eseguire manage.py:
    DJANGO_SETTINGS_MODULE=ultragames_django.settings_test python manage.py shell

SOLID PRINCIPLES:
  - SRP: Questo file espone solo il punto di ingresso per i comandi Django.
    Tutta la logica applicativa è nei moduli del progetto.
"""

import os
import sys


def main():
    """
    Entry point principale per i comandi di gestione Django.

    FLUSSO:
      1. Imposta DJANGO_SETTINGS_MODULE se non già definito nell'ambiente
      2. Importa execute_from_command_line da django.core.management
         (se Django non è installato → ImportError con messaggio utile)
      3. Passa sys.argv a execute_from_command_line:
           sys.argv[0] = "manage.py"
           sys.argv[1] = comando (es. "runserver")
           sys.argv[2+] = argomenti del comando (es. "8080")
      4. Django interpreta il comando e lo esegue

    GESTIONE IMPORTERROR:
      Se Django non è nel virtualenv attivo, l'import fallisce.
      Il messaggio di errore guida l'utente all'installazione delle dipendenze.
    """
    # Imposta il modulo settings Django. setdefault non sovrascrive se già impostato.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ultragames_django.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Impossibile importare Django. Verifica che Django sia installato "
            "e che il virtualenv sia attivato (pip install -r requirements.txt)."
        ) from exc

    # Esegue il comando Django passato dalla riga di comando.
    # sys.argv: lista di argomenti, es. ["manage.py", "runserver", "--port=8080"]
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
