-- pid_tuner/storage/schema.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tags(
  tag_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT UNIQUE NOT NULL,
  role       TEXT CHECK(role IN ('PV','SP','OP','MODE','BKCAL','CAS_IN','OTHER')) NOT NULL,
  eu         TEXT,
  meta_json  TEXT
);

CREATE TABLE IF NOT EXISTS sessions(
  session_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  started_utc  REAL NOT NULL,
  ended_utc    REAL,
  note         TEXT
);

CREATE TABLE IF NOT EXISTS samples(
  ts_utc      REAL NOT NULL,
  tag_id      INTEGER NOT NULL,
  value       REAL,
  quality     INTEGER,
  session_id  INTEGER,
  FOREIGN KEY(tag_id) REFERENCES tags(tag_id),
  FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);
CREATE INDEX IF NOT EXISTS ix_samples_tag_time ON samples(tag_id, ts_utc);

CREATE TABLE IF NOT EXISTS step_tests(
  step_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  INTEGER,
  tag_id_step INTEGER,
  t0_utc      REAL,
  du          REAL,
  pre_mean    REAL,
  post_mean   REAL,
  note        TEXT,
  FOREIGN KEY(session_id) REFERENCES sessions(session_id),
  FOREIGN KEY(tag_id_step) REFERENCES tags(tag_id)
);

CREATE TABLE IF NOT EXISTS model_fits(
  fit_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  step_id     INTEGER,
  model       TEXT CHECK(model IN ('FOPDT','SOPDT','INT')),
  K           REAL, tau REAL, tau1 REAL, tau2 REAL, theta REAL, kprime REAL,
  sse         REAL,
  algo        TEXT,
  created_utc REAL,
  FOREIGN KEY(step_id) REFERENCES step_tests(step_id)
);
