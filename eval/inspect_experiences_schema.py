import sqlite3
import json

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM interview_experiences")
print("Total interview experiences:", cur.fetchone()[0])

cur.execute("SELECT experience_id, company_name, role, source_file, batch, branch, rounds_json, key_questions_json FROM interview_experiences LIMIT 3")
for r in cur.fetchall():
    print(f"\nID: {r[0]} | Comp: {r[1]} | Role: {r[2]} | File: {r[3]} | Batch: {r[4]} | Branch: {r[5]}")
    rounds = json.loads(r[6]) if r[6] else []
    print(f"Rounds ({len(rounds)}):", [rd.get("name") or rd.get("title") for rd in rounds[:3]])
    qs = json.loads(r[7]) if r[7] else []
    print(f"Questions ({len(qs)}):", qs[:2])

cur.execute("SELECT DISTINCT company_name FROM interview_experiences ORDER BY company_name")
comps = [r[0] for r in cur.fetchall()]
print(f"\nDistinct companies in interview_experiences ({len(comps)}):", comps[:20])

