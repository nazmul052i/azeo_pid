# pid_tuner/storage/writer.py
import sqlite3, threading, queue, time, json, os
from pathlib import Path

class SamplesWriter:
    def __init__(self, db_path: str = "pid_tuner.db", schema_path: str | None = None):
        self.db_path = Path(db_path)
        self.schema_path = schema_path or (Path(__file__).with_name("schema.sql"))
        self._ensure_schema()
        self._q = queue.Queue(maxsize=10000)
        self._stop = threading.Event()
        self._thr = threading.Thread(target=self._worker, daemon=True)
        self._thr.start()
        self._tag_cache = {}

    # --- setup ----------------------------------------------------------
    def _ensure_schema(self):
        conn = sqlite3.connect(self.db_path)
        with open(self.schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        conn.executescript(sql)
        conn.commit()
        conn.close()

    # --- tag helpers ----------------------------------------------------
    def get_tag_id(self, name: str, role: str = "OTHER", eu: str | None = None) -> int:
        if name in self._tag_cache:
            return self._tag_cache[name]
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT tag_id FROM tags WHERE name=?", (name,))
        row = cur.fetchone()
        if row:
            tid = row[0]
        else:
            cur.execute("INSERT INTO tags(name, role, eu, meta_json) VALUES (?,?,?,?)",
                        (name, role, eu, None))
            conn.commit()
            tid = cur.lastrowid
        conn.close()
        self._tag_cache[name] = tid
        return tid

    def new_session(self, note: str | None = None) -> int:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO sessions(started_utc, note) VALUES (?,?)", (time.time(), note))
        conn.commit()
        sid = cur.lastrowid
        conn.close()
        return sid

    def end_session(self, session_id: int):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE sessions SET ended_utc=? WHERE session_id=?", (time.time(), session_id))
        conn.commit()
        conn.close()

    # --- queue interface -----------------------------------------------
    def write_sample(self, ts: float, tag: str, value: float, quality: int = 192,
                     session_id: int | None = None):
        """Queue one sample"""
        self._q.put_nowait((ts, tag, value, quality, session_id))

    def write_batch(self, rows: list[tuple]):
        """Direct insert for external batch"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO samples(ts_utc, tag_id, value, quality, session_id) VALUES (?,?,?,?,?)",
            rows
        )
        conn.commit()
        conn.close()

    # --- worker thread --------------------------------------------------
    def _worker(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cur = conn.cursor()
        batch = []
        while not self._stop.is_set():
            try:
                item = self._q.get(timeout=1)
                ts, tag, val, q, sid = item
                tid = self.get_tag_id(tag)
                batch.append((ts, tid, val, q, sid))
                if len(batch) >= 200:
                    cur.executemany(
                        "INSERT INTO samples(ts_utc, tag_id, value, quality, session_id) VALUES (?,?,?,?,?)",
                        batch
                    )
                    conn.commit()
                    batch.clear()
            except queue.Empty:
                if batch:
                    cur.executemany(
                        "INSERT INTO samples(ts_utc, tag_id, value, quality, session_id) VALUES (?,?,?,?,?)",
                        batch
                    )
                    conn.commit()
                    batch.clear()
        conn.close()

    def close(self):
        self._stop.set()
        self._thr.join(timeout=2)
