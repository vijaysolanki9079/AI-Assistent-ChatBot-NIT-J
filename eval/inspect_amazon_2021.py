import sqlite3

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()

rows = cur.execute("""
    SELECT o.offer_id, o.student_id, p.full_name, b.short_name, s.batch_id, 
           c.canonical_name, o.offer_type, o.ctc_lpa, o.package_raw, o.source_sheet, o.source_row
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN branches b ON s.branch_code = b.branch_code
    JOIN companies c ON o.company_id = c.company_id
    LEFT JOIN student_private_pii p ON p.student_id = s.student_id
    WHERE c.canonical_name = 'Amazon' AND s.batch_id = '2021-2025'
""").fetchall()

print(f"Amazon 2021-2025 offers in DB: {len(rows)}")
for r in rows:
    print(r)

