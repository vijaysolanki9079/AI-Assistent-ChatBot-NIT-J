import sqlite3

conn = sqlite3.connect('data/nitj_placement.db')
cur = conn.cursor()

cur.execute("""
    SELECT o.source_sheet, COUNT(*)
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    WHERE s.batch_id = '2021-2025'
    GROUP BY o.source_sheet
""")
for sname, cnt in cur.fetchall():
    print(f"  - Sheet '{sname}': {cnt} offers")

