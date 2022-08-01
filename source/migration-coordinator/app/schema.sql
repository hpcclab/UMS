DROP TABLE IF EXISTS migration;
DROP TABLE IF EXISTS message;

CREATE TABLE migration
(
    id TEXT UNIQUE NOT NULL
);

CREATE TABLE message
(
    message      TEXT,
    migration_id TEXT
);