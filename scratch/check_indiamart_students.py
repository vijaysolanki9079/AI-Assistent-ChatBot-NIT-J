import sqlite3
import json

# 1. Search interview_experiences_structured.json
with open("data/interview_experiences_structured.json", "r", encoding="utf-8") as f:
    exps = json.load(f)

print("Total structured experiences:", len(exps))
im_exps = [e for e in exps if "indiamart" in str(e.get("company", "")).lower() or "indiamart" in str(e.get("company_name", "")).lower()]
print(f"IndiaMART structured experiences: {len(im_exps)}")
for e in im_exps:
    print(json.dumps(e, indent=2))

# 2. Check in database for offers source_file and source_row for the 3 students in IndiaMart CSE
conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()
cur.execute("""
    SELECT o.offer_id, s.student_id, s.batch_id, b.short_name, o.source_file, o.source_sheet, o.source_row, o.package_raw
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN branches b ON s.branch_code = b.branch_code
    JOIN companies c ON o.company_id = c.company_id
    WHERE c.canonical_name = 'IndiaMart' AND b.short_name = 'CSE'
""")
print("\nOffers for IndiaMart in CSE:")
for r in cur.fetchall():
    print(r)

# 3. Search students table or any other records for student_id matching Lovkesh or Samarth
cur.execute("SELECT * FROM students WHERE student_id IN ('21103146', '21103010', '21103082')")
print("\nStudents records:")
for r in cur.fetchall():
    print(r)

conn.close()

