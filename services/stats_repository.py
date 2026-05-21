"""
InDatabaseStatsRepository - Repository per le statistiche dei giochi su MariaDB.

PATTERN ARCHITETTURALE: Repository (SRP)
  Incapsula tutto l'accesso SQL alle tre tabelle di statistiche:
    - tris_stats     (wins, losses, draws)
    - dama_stats     (wins, losses)
    - reaction_stats (best_ms, attempts)

  Le view dei giochi non toccano mai direttamente il DB: chiamano questo
  repository tramite il container dopo la fine di ogni partita.

SOLID PRINCIPLES APPLICATI:
  - SRP: Questo file è responsabile SOLO di leggere/scrivere statistiche.
    La logica di gioco è nei rispettivi servizi (dama/, tris/, reaction_test/).
  - DIP: Le view e i servizi dipendono dall'istanza iniettata dal container,
    non da questa classe concreta.
  - OCP: Per aggiungere statistiche di un quarto gioco è sufficiente aggiungere
    nuovi metodi senza modificare quelli esistenti.

FLUSSO DI CHIAMATA:
  DamaMoveView.post()
    → get_container().stats_repository.record_dama_result(user_id, won=True)
      ← questo file

  UserListView.get()
    → get_container().stats_repository.get_user_stats(u.id)
      ← questo file

  AccountService.delete_account()
    → stats_repository.delete_user_stats(user_id)
      ← questo file (prima di eliminare l'utente)

SCHEMA TABELLE (attese nel DB):
  CREATE TABLE tris_stats (
    user_id VARCHAR(36) PRIMARY KEY,
    wins INT DEFAULT 0, losses INT DEFAULT 0, draws INT DEFAULT 0,
    CONSTRAINT fk_tris_user FOREIGN KEY (user_id) REFERENCES users(id)
  );
  CREATE TABLE dama_stats (
    user_id VARCHAR(36) PRIMARY KEY,
    wins INT DEFAULT 0, losses INT DEFAULT 0,
    CONSTRAINT fk_dama_user FOREIGN KEY (user_id) REFERENCES users(id)
  );
  CREATE TABLE reaction_stats (
    user_id VARCHAR(36) PRIMARY KEY,
    best_ms INT,
    attempts INT DEFAULT 0,
    CONSTRAINT fk_reaction_user FOREIGN KEY (user_id) REFERENCES users(id)
  );

  NOTA: le FK non usano ON DELETE CASCADE deliberatamente.
  AccountService.delete_account() e BanUserView eliminano sempre le stats
  PRIMA dell'utente (ordine già garantito nel codice), quindi il vincolo
  di integrità referenziale è rispettato senza affidarsi a CASCADE.
  Questo rende esplicita la dipendenza nell'application layer e facilita
  il debug in caso di eliminazioni parziali.
"""

# _get_connection è definita in user_repository per evitare duplicazione (DRY).
# Entrambi i repository condividono la stessa logica di connessione al DB.
from services.user_repository import _get_connection


class InDatabaseStatsRepository:
    """
    Implementazione concreta del repository statistiche su MariaDB.

    METODI PUBBLICI:
      record_tris_result     → chiamato da TrisMoveView alla fine di una partita
      record_dama_result     → chiamato da DamaMoveView alla fine di una partita
      record_reaction_ms     → chiamato da ReactionClickView dopo un click valido
      get_user_stats         → chiamato da MyStatsView e UserListView
      get_tris_ranking       → chiamato da RankingView (game="tris")
      get_dama_ranking       → chiamato da RankingView (game="dama")
      get_reaction_ranking   → chiamato da RankingView (game="reaction")
      delete_user_stats      → chiamato da AccountService e BanUserView
      set_user_stats         → chiamato da UpdateStatsView (admin)
    """

    def record_tris_result(self, user_id: str, won: bool, draw: bool = False) -> None:
        """
        Registra il risultato di una partita di Tris per l'utente.

        LOGICA SQL (upsert):
          1. INSERT ... ON DUPLICATE KEY: crea la riga se non esiste
          2. Secondo UPDATE: incrementa il contatore corretto (wins/draws/losses)

        CHIAMATO DA:
          apps/games/views/tris_move_view.py → TrisMoveView.post()
          dopo che result["status"] ∈ {"human_win", "ai_win", "draw"}

        :param user_id: UUID dell'utente autenticato (da request.current_user)
        :param won: True se l'utente ha vinto (status == "human_win")
        :param draw: True se la partita è finita in pareggio (status == "draw")
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            # Garantisce che la riga esista senza modificare i valori esistenti
            cur.execute(
                "INSERT INTO tris_stats (user_id, wins, losses, draws) VALUES (?, 0, 0, 0) "
                "ON DUPLICATE KEY UPDATE user_id = user_id",
                (user_id,),
            )
            if won:
                cur.execute("UPDATE tris_stats SET wins = wins + 1 WHERE user_id = ?", (user_id,))
            elif draw:
                cur.execute("UPDATE tris_stats SET draws = draws + 1 WHERE user_id = ?", (user_id,))
            else:
                cur.execute("UPDATE tris_stats SET losses = losses + 1 WHERE user_id = ?", (user_id,))
            conn.commit()

    def record_dama_result(self, user_id: str, won: bool) -> None:
        """
        Registra il risultato di una partita di Dama per l'utente.

        CHIAMATO DA:
          apps/games/views/dama_move_view.py → DamaMoveView.post()
          dopo che result["status"] ∈ {"white_wins", "black_wins"}
          (white = umano, quindi won = status == "white_wins")

        :param user_id: UUID dell'utente autenticato
        :param won: True se il giocatore umano (white) ha vinto
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO dama_stats (user_id, wins, losses) VALUES (?, 0, 0) "
                "ON DUPLICATE KEY UPDATE user_id = user_id",
                (user_id,),
            )
            if won:
                cur.execute("UPDATE dama_stats SET wins = wins + 1 WHERE user_id = ?", (user_id,))
            else:
                cur.execute("UPDATE dama_stats SET losses = losses + 1 WHERE user_id = ?", (user_id,))
            conn.commit()

    def record_reaction_ms(self, user_id: str, reaction_ms: int) -> None:
        """
        Registra il tempo di reazione di un round e aggiorna il record personale.

        LOGICA SQL (upsert con confronto):
          - Se è il primo tentativo: inserisce best_ms = reaction_ms, attempts = 1
          - Se non è il primo:
              best_ms = IF(? < best_ms, ?, best_ms)  ← aggiorna solo se migliore
              attempts = attempts + 1

        CHIAMATO DA:
          apps/games/views/reaction_click_view.py → ReactionClickView.post()
          solo se reaction_ms > 0 (scarta click anticipati)

        :param user_id: UUID dell'utente autenticato
        :param reaction_ms: Tempo di reazione in millisecondi (già intero)
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO reaction_stats (user_id, best_ms, attempts) VALUES (?, ?, 1) "
                "ON DUPLICATE KEY UPDATE "
                "best_ms = IF(best_ms IS NULL OR ? < best_ms, ?, best_ms), "
                "attempts = attempts + 1",
                (user_id, reaction_ms, reaction_ms, reaction_ms),
            )
            conn.commit()

    def get_user_stats(self, user_id: str) -> dict:
        """
        Restituisce le statistiche aggregate dell'utente per tutti e tre i giochi.

        STRUTTURA RISPOSTA:
          {
            "tris":     {"wins": int, "losses": int, "draws": int},
            "dama":     {"wins": int, "losses": int},
            "reaction": {"best_ms": int|None, "attempts": int}
          }

        CHIAMATO DA:
          apps/stats/views/my_stats_view.py → MyStatsView.get()
          apps/admin_panel/views/user_list_view.py → UserListView.get()

        NOTE:
          - Se l'utente non ha mai giocato a un gioco, la riga non esiste:
            fetchone() restituisce None e il fallback "or (0, 0, 0)" garantisce
            valori zero.

        :param user_id: UUID dell'utente
        :return: Dizionario con statistiche per tris, dama e reaction
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT wins, losses, draws FROM tris_stats WHERE user_id = ?", (user_id,))
            tris_row = cur.fetchone() or (0, 0, 0)
            cur.execute("SELECT wins, losses FROM dama_stats WHERE user_id = ?", (user_id,))
            dama_row = cur.fetchone() or (0, 0)
            cur.execute("SELECT best_ms, attempts FROM reaction_stats WHERE user_id = ?", (user_id,))
            react_row = cur.fetchone() or (None, 0)
        return {
            "tris":     {"wins": tris_row[0], "losses": tris_row[1], "draws": tris_row[2]},
            "dama":     {"wins": dama_row[0], "losses": dama_row[1]},
            "reaction": {"best_ms": react_row[0], "attempts": react_row[1]},
        }

    def get_tris_ranking(self) -> list:
        """
        Classifica globale per il Tris, ordinata per vittorie DESC poi sconfitte ASC.

        CHIAMATO DA:
          apps/stats/views/ranking_view.py → RankingView.get(game="tris")

        JOIN con users per ottenere il nome visualizzato al posto dell'UUID.

        :return: Lista di dict {"name", "wins", "losses", "draws"} ordinata
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT u.name, t.wins, t.losses, t.draws "
                "FROM tris_stats t JOIN users u ON t.user_id = u.id "
                "ORDER BY t.wins DESC, t.losses ASC"
            )
            rows = cur.fetchall()
        return [{"name": r[0], "wins": r[1], "losses": r[2], "draws": r[3]} for r in rows]

    def get_dama_ranking(self) -> list:
        """
        Classifica globale per la Dama, ordinata per vittorie DESC poi sconfitte ASC.

        CHIAMATO DA:
          apps/stats/views/ranking_view.py → RankingView.get(game="dama")

        :return: Lista di dict {"name", "wins", "losses"} ordinata
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT u.name, d.wins, d.losses "
                "FROM dama_stats d JOIN users u ON d.user_id = u.id "
                "ORDER BY d.wins DESC, d.losses ASC"
            )
            rows = cur.fetchall()
        return [{"name": r[0], "wins": r[1], "losses": r[2]} for r in rows]

    def get_reaction_ranking(self) -> list:
        """
        Classifica globale per il Test di Reazione, ordinata per tempo migliore ASC.

        CHIAMATO DA:
          apps/stats/views/ranking_view.py → RankingView.get(game="reaction")

        WHERE best_ms IS NOT NULL: esclude utenti che non hanno mai completato
        un round valido (solo click anticipati → best_ms rimane NULL).

        :return: Lista di dict {"name", "best_ms", "attempts"} ordinata
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT u.name, r.best_ms, r.attempts "
                "FROM reaction_stats r JOIN users u ON r.user_id = u.id "
                "WHERE r.best_ms IS NOT NULL "
                "ORDER BY r.best_ms ASC"
            )
            rows = cur.fetchall()
        return [{"name": r[0], "best_ms": r[1], "attempts": r[2]} for r in rows]

    def delete_user_stats(self, user_id: str) -> None:
        """
        Elimina tutte le statistiche dell'utente da tutte e tre le tabelle.

        CHIAMATO DA (in questo ordine):
          AccountService.delete_account() → prima di user_repository.delete()
          BanUserView.post()              → prima di user_repository.delete()

        MOTIVO DELL'ORDINE:
          Se le tabelle avessero FOREIGN KEY su users.id, eliminare l'utente
          prima delle sue stats causerebbe un errore di integrità referenziale.
          L'eliminazione delle stats prima è quindi la sequenza corretta.

        :param user_id: UUID dell'utente da eliminare
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM tris_stats WHERE user_id = ?", (user_id,))
            cur.execute("DELETE FROM dama_stats WHERE user_id = ?", (user_id,))
            cur.execute("DELETE FROM reaction_stats WHERE user_id = ?", (user_id,))
            conn.commit()

    def set_user_stats(self, user_id: str, stats: dict) -> None:
        """
        Sovrascrive manualmente le statistiche di un utente (uso amministrativo).

        CHIAMATO DA:
          apps/admin_panel/views/update_stats_view.py → UpdateStatsView.post()

        STRUTTURA INPUT stats:
          {
            "tris":     {"wins": int, "losses": int, "draws": int},   # opzionale
            "dama":     {"wins": int, "losses": int},                  # opzionale
            "reaction": {"best_ms": int|None, "attempts": int}         # opzionale
          }

        Ogni sezione è opzionale: se la chiave non è presente nel dict,
        la corrispondente tabella non viene aggiornata (gestione granulare).

        UPSERT: INSERT ... ON DUPLICATE KEY UPDATE sovrascrive i valori
        esistenti, o crea la riga se assente.

        :param user_id: UUID dell'utente target
        :param stats: Dizionario con le statistiche da impostare
        """
        with _get_connection() as conn:
            cur = conn.cursor()
            if "tris" in stats:
                t = stats["tris"]
                w, l, d = int(t.get("wins", 0)), int(t.get("losses", 0)), int(t.get("draws", 0))
                cur.execute(
                    "INSERT INTO tris_stats (user_id, wins, losses, draws) VALUES (?, ?, ?, ?) "
                    "ON DUPLICATE KEY UPDATE wins = ?, losses = ?, draws = ?",
                    (user_id, w, l, d, w, l, d),
                )
            if "dama" in stats:
                d2 = stats["dama"]
                w, l = int(d2.get("wins", 0)), int(d2.get("losses", 0))
                cur.execute(
                    "INSERT INTO dama_stats (user_id, wins, losses) VALUES (?, ?, ?) "
                    "ON DUPLICATE KEY UPDATE wins = ?, losses = ?",
                    (user_id, w, l, w, l),
                )
            if "reaction" in stats:
                r = stats["reaction"]
                bm = r.get("best_ms")
                att = int(r.get("attempts", 0))
                if bm is not None:
                    bm = int(bm)
                cur.execute(
                    "INSERT INTO reaction_stats (user_id, best_ms, attempts) VALUES (?, ?, ?) "
                    "ON DUPLICATE KEY UPDATE best_ms = ?, attempts = ?",
                    (user_id, bm, att, bm, att),
                )
            conn.commit()
