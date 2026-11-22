import sqlite3

conn = sqlite3.connect('data/nitj_placement.db')
cur = conn.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')").fetchall()]
print("Tables and views:", tables)
for t in tables:
    cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})").fetchall()]
    print(f"{t}: {cols}")

