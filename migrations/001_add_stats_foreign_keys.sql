-- Migrazione 001: aggiunge relazioni FK dalle tabelle *_stats verso users
--
-- PREREQUISITI:
--   - La tabella `users` deve esistere con `id VARCHAR(36) PRIMARY KEY`.
--   - Le tabelle *_stats devono esistere (o vengono create qui sotto).
--
-- STRATEGIA FK (no CASCADE):
--   AccountService.delete_account() e BanUserView eliminano le stats
--   PRIMA dell'utente, quindi l'integrità referenziale è garantita
--   dall'application layer. Non usiamo ON DELETE CASCADE per rendere
--   esplicita questa dipendenza e semplificare il debug.
--
-- ESECUZIONE:
--   mysql -u <user> -p <database> < migrations/001_add_stats_foreign_keys.sql

-- ─── Creazione tabelle (se non esistono già) ────────────────────────────────

CREATE TABLE IF NOT EXISTS tris_stats (
    user_id VARCHAR(36) PRIMARY KEY,
    wins    INT DEFAULT 0,
    losses  INT DEFAULT 0,
    draws   INT DEFAULT 0,
    CONSTRAINT fk_tris_user
        FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS dama_stats (
    user_id VARCHAR(36) PRIMARY KEY,
    wins    INT DEFAULT 0,
    losses  INT DEFAULT 0,
    CONSTRAINT fk_dama_user
        FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS reaction_stats (
    user_id  VARCHAR(36) PRIMARY KEY,
    best_ms  INT,
    attempts INT DEFAULT 0,
    CONSTRAINT fk_reaction_user
        FOREIGN KEY (user_id) REFERENCES users (id)
);

-- ─── Aggiunta FK su tabelle già esistenti ───────────────────────────────────
-- Esegui questi ALTER solo se le tabelle erano già presenti senza FK.
-- Se hai usato i CREATE TABLE IF NOT EXISTS qui sopra su un DB vuoto,
-- le FK sono già incluse e puoi saltare questa sezione.

-- ALTER TABLE tris_stats
--     ADD CONSTRAINT fk_tris_user
--         FOREIGN KEY (user_id) REFERENCES users (id);

-- ALTER TABLE dama_stats
--     ADD CONSTRAINT fk_dama_user
--         FOREIGN KEY (user_id) REFERENCES users (id);

-- ALTER TABLE reaction_stats
--     ADD CONSTRAINT fk_reaction_user
--         FOREIGN KEY (user_id) REFERENCES users (id);
