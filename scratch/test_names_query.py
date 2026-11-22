import sqlite3

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()

company = "IndiaMart"
b_code = "CSE"
batches = ["2020-2024", "2021-2025", "2022-2026"]

sql = """
SELECT DISTINCT p.full_name, b.short_name, s.batch_id, c.canonical_name, 
       COALESCE(o.profile, 'Graduate Engineer / Analyst') AS role, o.offer_type
FROM offers o
JOIN students s ON o.student_id = s.student_id
JOIN student_private_pii p ON s.student_id = p.student_id
JOIN branches b ON s.branch_code = b.branch_code
JOIN companies c ON o.company_id = c.company_id
WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
  AND c.canonical_name LIKE ?
  AND b.short_name = ?
ORDER BY p.full_name ASC;
"""
cur.execute(sql, [company, b_code])
rows = cur.fetchall()
print(f"Results with LIKE for {company} {b_code}: {len(rows)}")
for r in rows:
    print(" ", r)

# Now test what was passed in spec
print("\nExact match test:")
cur.execute("SELECT canonical_name FROM companies WHERE canonical_name LIKE '%indiamart%'")
print("Companies in DB:", cur.fetchall())
conn.close()
