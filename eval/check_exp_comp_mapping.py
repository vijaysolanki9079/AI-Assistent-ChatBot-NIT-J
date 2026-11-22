import sqlite3

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()

cur.execute("""
    SELECT DISTINCT ie.company_name, c.canonical_name 
    FROM interview_experiences ie
    LEFT JOIN companies c ON ie.company_id = c.company_id
    LIMIT 20
""")
for r in cur.fetchall():
    print(r)

