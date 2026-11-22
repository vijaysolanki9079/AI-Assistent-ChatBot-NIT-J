import sqlite3

conn = sqlite3.connect('data/nitj_placement.db')
c = conn.cursor()

c.execute("SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name")
items = c.fetchall()

print(f"{'TYPE':<6} | {'NAME':<28} | {'COUNT':<7} | {'COLUMNS'}")
print("-" * 100)
for itype, name in items:
    c.execute(f"PRAGMA table_info('{name}')")
    cols = [r[1] for r in c.fetchall()]
    try:
        c.execute(f"SELECT COUNT(*) FROM '{name}'")
        count = c.fetchone()[0]
    except Exception as e:
        count = f"ERR"
    print(f"{itype.upper():<6} | {name:<28} | {str(count):<7} | {', '.join(cols)}")

