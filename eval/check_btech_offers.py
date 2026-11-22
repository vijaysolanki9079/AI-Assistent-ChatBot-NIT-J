import sqlite3

conn = sqlite3.connect('data/nitj_placement.db')
cur = conn.cursor()

# B.Tech in 3 main cohorts
cur.execute("""
    SELECT s.batch_id, COUNT(o.offer_id)
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN branches b ON s.branch_code = b.branch_code
    WHERE b.degree = 'B.Tech' AND s.batch_id IN ('2020-2024', '2021-2025', '2022-2026')
    GROUP BY s.batch_id
""")
for bid, cnt in cur.fetchall():
    print(f"B.Tech {bid}: {cnt} offers")

