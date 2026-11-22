import sqlite3

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()

for comp in ["Google", "Uber", "Goldman Sachs", "Cadence", "Amazon", "Microsoft", "Oracle"]:
    cur.execute("SELECT COUNT(*) FROM interview_experiences WHERE company_name LIKE ?", (f"%{comp}%",))
    cnt = cur.fetchone()[0]
    print(f"Company '{comp}': {cnt} experiences")

