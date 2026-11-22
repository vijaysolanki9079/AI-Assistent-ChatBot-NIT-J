import sqlite3

conn = sqlite3.connect('data/nitj_placement.db')
cur = conn.cursor()
cur.execute("SELECT name, sql FROM sqlite_master WHERE type IN ('table', 'view')")
rows = cur.fetchall()
for name, sql in rows:
    print("NAME:", name)
    print(sql)
    print("-" * 50)
conn.close()

