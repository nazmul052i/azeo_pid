from __future__ import annotations
import sqlite3, json, os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS tags(
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  kind TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions(
  id INTEGER PRIMARY KEY,
  start_ts REAL NOT NULL,
  end_ts REAL,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS samples(
  id INTEGER PRIMARY KEY,
  session_id INTEGER NOT NULL,
  ts REAL NOT NULL,
  tag_id INTEGER NOT NULL,
  value REAL NOT NULL,
  quality INTEGER DEFAULT 192,
  FOREIGN KEY(session_id) REFERENCES sessions(id),
  FOREIGN KEY(tag_id) REFERENCES tags(id)
);
CREATE INDEX IF NOT EXISTS idx_samples_session_ts ON samples(session_id, ts);
CREATE INDEX IF NOT EXISTS idx_samples_tag ON samples(tag_id);

CREATE TABLE IF NOT EXISTS step_tests(
  id INTEGER PRIMARY KEY,
  session_id INTEGER NOT NULL,
  t0 REAL NOT NULL,
  tag_op INTEGER NOT NULL,
  tag_pv INTEGER NOT NULL,
  du REAL NOT NULL,
  pv0 REAL NOT NULL,
  op0 REAL NOT NULL,
  idx0 INTEGER NOT NULL,
  idx1 INTEGER NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(id),
  FOREIGN KEY(tag_op) REFERENCES tags(id),
  FOREIGN KEY(tag_pv) REFERENCES tags(id)
);

CREATE TABLE IF NOT EXISTS model_fits(
  id INTEGER PRIMARY KEY,
  session_id INTEGER NOT NULL,
  step_id INTEGER,
  model_type TEXT NOT NULL, -- FOPDT|SOPDT|Integrating
  params_json TEXT NOT NULL,
  stats_json TEXT NOT NULL,
  created_ts REAL NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(id),
  FOREIGN KEY(step_id) REFERENCES step_tests(id)
);
"""


@dataclass(slots=True)
class Sample:
    ts: float
    tag: str
    value: float
    quality: int = 192


class StorageService:
    """
    SQLite historian + derived tables (step tests, model fits).
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, isolation_level=None, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys=ON;")
        for statement in filter(None, SCHEMA.split(";")):
            self.conn.execute(statement)

    # -------- tags --------
    def _get_or_add_tag(self, name: str, kind: str) -> int:
        cur = self.conn.execute("SELECT id FROM tags WHERE name=?", (name,))
        row = cur.fetchone()
        if row:
            return int(row[0])
        cur = self.conn.execute("INSERT INTO tags(name, kind) VALUES(?,?)", (name, kind))
        return int(cur.lastrowid)

    def ensure_tags(self, mapping: Dict[str, str]) -> Dict[str, int]:
        """
        mapping: {"TCAF":"PV", "TCAF.SP":"SP", "PCAF":"OP"}
        returns: {"TCAF":1, "TCAF.SP":2, "PCAF":3}
        """
        out: Dict[str, int] = {}
        for name, kind in mapping.items():
            out[name] = self._get_or_add_tag(name, kind)
        return out

    # -------- sessions --------
    def start_session(self, start_ts: float, notes: str = "") -> int:
        cur = self.conn.execute("INSERT INTO sessions(start_ts, notes) VALUES(?,?)", (start_ts, notes))
        return int(cur.lastrowid)

    def end_session(self, session_id: int, end_ts: float):
        self.conn.execute("UPDATE sessions SET end_ts=? WHERE id=?", (end_ts, session_id))

    # -------- samples --------
    def insert_samples(self, session_id: int, samples: Iterable[Sample]):
        # batch insert; ensure tags exist on the fly
        names = {s.tag for s in samples}
        # need to iterate twice: convert to list
        samples = list(samples)
        tag_ids = {n: self._get_or_add_tag(n, "PV") for n in names}  # default kind PV if unknown
        rows = [(session_id, s.ts, tag_ids[s.tag], s.value, s.quality) for s in samples]
        self.conn.executemany(
            "INSERT INTO samples(session_id, ts, tag_id, value, quality) VALUES(?,?,?,?,?)",
            rows,
        )

    def read_series(self, session_id: int, tag: str, t_min: float | None = None, t_max: float | None = None) -> List[Tuple[float, float]]:
        cur = self.conn.execute("SELECT id FROM tags WHERE name=?", (tag,))
        r = cur.fetchone()
        if not r:
            return []
        tag_id = int(r[0])
        q = "SELECT ts, value FROM samples WHERE session_id=? AND tag_id=?"
        params: List[float | int] = [session_id, tag_id]
        if t_min is not None:
            q += " AND ts>=?"
            params.append(t_min)
        if t_max is not None:
            q += " AND ts<=?"
            params.append(t_max)
        q += " ORDER BY ts ASC"
        return [(float(ts), float(val)) for ts, val in self.conn.execute(q, params)]

    # -------- step tests --------
    def record_step_test(self, session_id: int, t0: float, tag_op: str, tag_pv: str, du: float, pv0: float, op0: float, idx0: int, idx1: int) -> int:
        op_id = self._get_or_add_tag(tag_op, "OP")
        pv_id = self._get_or_add_tag(tag_pv, "PV")
        cur = self.conn.execute(
            "INSERT INTO step_tests(session_id,t0,tag_op,tag_pv,du,pv0,op0,idx0,idx1) VALUES(?,?,?,?,?,?,?,?,?)",
            (session_id, t0, op_id, pv_id, du, pv0, op0, idx0, idx1),
        )
        return int(cur.lastrowid)

    def list_step_tests(self, session_id: int) -> List[Dict]:
        out = []
        cur = self.conn.execute(
            """SELECT st.id, st.t0, topt.name, tpv.name, st.du, st.pv0, st.op0, st.idx0, st.idx1
               FROM step_tests st
               JOIN tags topt ON st.tag_op = topt.id
               JOIN tags tpv ON st.tag_pv = tpv.id
               WHERE st.session_id=?
               ORDER BY st.t0""",
            (session_id,),
        )
        for row in cur.fetchall():
            out.append({
                "id": int(row[0]), "t0": float(row[1]), "tag_op": row[2], "tag_pv": row[3],
                "du": float(row[4]), "pv0": float(row[5]), "op0": float(row[6]),
                "idx0": int(row[7]), "idx1": int(row[8]),
            })
        return out

    # -------- model fits --------
    def insert_model_fit(self, session_id: int, model_type: str, params: Dict, stats: Dict, step_id: int | None, created_ts: float) -> int:
        cur = self.conn.execute(
            "INSERT INTO model_fits(session_id, step_id, model_type, params_json, stats_json, created_ts) VALUES(?,?,?,?,?,?)",
            (session_id, step_id, model_type, json.dumps(params), json.dumps(stats), created_ts),
        )
        return int(cur.lastrowid)

    def list_model_fits(self, session_id: int) -> List[Dict]:
        cur = self.conn.execute(
            "SELECT id, step_id, model_type, params_json, stats_json, created_ts FROM model_fits WHERE session_id=? ORDER BY created_ts DESC",
            (session_id,),
        )
        out = []
        for r in cur.fetchall():
            out.append({
                "id": int(r[0]),
                "step_id": None if r[1] is None else int(r[1]),
                "model_type": str(r[2]),
                "params": json.loads(r[3]),
                "stats": json.loads(r[4]),
                "created_ts": float(r[5]),
            })
        return out

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
