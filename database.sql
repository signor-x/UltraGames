CREATE TABLE tris_stats (
    user_id VARCHAR(36) PRIMARY KEY,
    wins    INT DEFAULT 0,
    losses  INT DEFAULT 0,
    draws   INT DEFAULT 0,
    CONSTRAINT fk_tris_user
        FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE dama_stats (
    user_id VARCHAR(36) PRIMARY KEY,
    wins    INT DEFAULT 0,
    losses  INT DEFAULT 0,
    CONSTRAINT fk_dama_user
        FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE reaction_stats (
    user_id  VARCHAR(36) PRIMARY KEY,
    best_ms  INT,
    attempts INT DEFAULT 0,
    CONSTRAINT fk_reaction_user
        FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE users (
    id            VARCHAR(36)  PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name          VARCHAR(100) NOT NULL
);

INSERT INTO users (id, email, password_hash, name)
VALUES (
  UUID(),
  'admin@ultragames.local',
  '$2b$12$w3z157sSuN6H9gJwxaTCC.x5sGn.0zKeco1acyOZ9Mm/eOjkcdihe', --(Hash della password")
  'Admin'
);
	