# pid_tuner/storage/reader.py
import sqlite3
import pandas as pd

def get_series(db_path: str, tag_names: list[str], start: float, end: float) -> pd.DataFrame:
    """Return DataFrame with ts_utc and each tag as a column."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # resolve tag IDs
    q = "SELECT tag_id, name FROM tags WHERE name IN (%s)" % (
        ",".join("?"*len(tag_names))
    )
    rows = cur.execute(q, tag_names).fetchall()
    if not rows:
        conn.close()
        raise ValueError("No matching tags found")
    id_to_name = {r[0]: r[1] for r in rows}
    tag_ids = tuple(id_to_name.keys())
    q = f"SELECT ts_utc, tag_id, value FROM samples WHERE tag_id IN ({','.join(['?']*len(tag_ids))}) AND ts_utc BETWEEN ? AND ? ORDER BY ts_utc"
    data = cur.execute(q, (*tag_ids, start, end)).fetchall()
    conn.close()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data, columns=["ts_utc","tag_id","value"])
    df["name"] = df["tag_id"].map(id_to_name)
    df = df.pivot(index="ts_utc", columns="name", values="value")
    df.reset_index(inplace=True)
    return df

def list_sessions(db_path: str):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM sessions ORDER BY started_utc DESC", conn)
    conn.close()
    return df

def list_tags(db_path: str):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM tags", conn)
    conn.close()
    return df
