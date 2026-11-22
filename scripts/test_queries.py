import sqlite3

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()

print("--- 1. Microsoft package for CSE ---")
cur.execute("""
SELECT b.short_name, c.canonical_name, o.ctc_lpa, o.offer_type, s.batch_id, COUNT(*)
FROM offers o
JOIN students s ON o.student_id = s.student_id
JOIN branches b ON s.branch_code = b.branch_code
JOIN companies c ON o.company_id = c.company_id
WHERE c.canonical_name = 'Microsoft' AND b.short_name = 'CSE'
GROUP BY b.short_name, c.canonical_name, o.ctc_lpa, o.offer_type, s.batch_id;
""")
for r in cur.fetchall():
    print(r)

print("\n--- 2. How many students from IT got placed in Amazon? ---")
cur.execute("""
SELECT COUNT(DISTINCT s.student_id)
FROM offers o
JOIN students s ON o.student_id = s.student_id
JOIN branches b ON s.branch_code = b.branch_code
JOIN companies c ON o.company_id = c.company_id
WHERE c.canonical_name = 'Amazon' AND b.short_name = 'IT'
  AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');
""")
print("Amazon placed IT students:", cur.fetchone()[0])

print("\n--- 3. Top 5 companies by highest package ---")
cur.execute("""
SELECT c.canonical_name, MAX(o.ctc_lpa) as max_ctc
FROM offers o
JOIN companies c ON o.company_id = c.company_id
WHERE o.ctc_lpa IS NOT NULL
GROUP BY c.canonical_name
ORDER BY max_ctc DESC
LIMIT 5;
""")
for r in cur.fetchall():
    print(r)

print("\n--- 4. Placement % by Branch for 2020-2024 batch ---")
cur.execute("""
SELECT branch_short, total_students, placed_students, total_offers, placement_pct, avg_ctc_lpa, max_ctc_lpa
FROM v_branch_year_stats
WHERE batch_id = '2020-2024'
ORDER BY placement_pct DESC;
""")
for r in cur.fetchall():
    print(r)

print("\n--- 5. PayPal hiring by branch ---")
cur.execute("""
SELECT b.short_name, COUNT(DISTINCT s.student_id) as placed_count
FROM branches b
LEFT JOIN students s ON b.branch_code = s.branch_code
LEFT JOIN offers o ON s.student_id = o.student_id AND o.company_id = (SELECT company_id FROM companies WHERE canonical_name = 'PayPal')
GROUP BY b.short_name
HAVING placed_count > 0;
""")
for r in cur.fetchall():
    print("Hired by PayPal:", r)

conn.close()

