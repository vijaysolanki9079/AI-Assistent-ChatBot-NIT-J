import sqlite3

con = sqlite3.connect('data/nitj_placement.db')
cur = con.cursor()

cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY type, name;")
items = cur.fetchall()

print("=== TABLES & VIEWS ===")
for name, itype in items:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {name};")
        cnt = cur.fetchone()[0]
    except Exception as e:
        cnt = f"Error: {e}"
    cur.execute(f"PRAGMA table_info({name});")
    cols = [r[1] for r in cur.fetchall()]
    print(f"[{itype.upper()}] {name} ({cnt} rows)")
    print(f"   Cols: {', '.join(cols)}")
