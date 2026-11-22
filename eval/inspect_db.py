import sqlite3

conn = sqlite3.connect('data/nitj_placement.db')
cur = conn.cursor()

for row in cur.execute("SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL"):
    print(f"--- {row[0].upper()}: {row[1]} ---")
    print(row[2])
    print()

