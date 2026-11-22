import sqlite3

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()

# Query without FTE filter or with FTE filter
cur.execute("""
    SELECT COUNT(*) FROM (
        SELECT student_id 
        FROM v_offers_flat 
        WHERE offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
          AND batch_id IN ('2020-2024', '2021-2025', '2022-2026')
        GROUP BY student_id 
        HAVING COUNT(offer_id) > 1
    )
""")
print("FTE multi-offer in 3 batches:", cur.fetchone()[0])

cur.execute("""
    SELECT COUNT(*) FROM (
        SELECT student_id 
        FROM offers
        GROUP BY student_id 
        HAVING COUNT(offer_id) > 1
    )
""")
print("All offers multi-offer in DB:", cur.fetchone()[0])

cur.execute("""
    SELECT COUNT(*) FROM (
        SELECT student_id 
        FROM v_offers_flat
        WHERE batch_id IN ('2020-2024', '2021-2025', '2022-2026')
        GROUP BY student_id 
        HAVING COUNT(offer_id) > 1
    )
""")
print("All offers multi-offer in 3 batches:", cur.fetchone()[0])

