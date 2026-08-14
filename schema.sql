CREATE TABLE IF NOT EXISTS feeds (
    url        TEXT PRIMARY KEY,
    fetched_at REAL NOT NULL,
    body       BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS takes (
    headline   TEXT NOT NULL,
    model      TEXT NOT NULL,
    character  TEXT NOT NULL,
    source     TEXT,
    take       TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (headline, model, character)
);
CREATE INDEX IF NOT EXISTS takes_by_date ON takes (created_at DESC);
