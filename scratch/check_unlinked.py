import sqlite3
from collections import Counter

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()
cur.execute("SELECT company_name FROM interview_experiences WHERE company_id IS NULL")
unlinked = [r[0] for r in cur.fetchall()]
print(f"Total unlinked entries: {len(unlinked)}")
counts = Counter(unlinked)
for c, cnt in counts.most_common(25):
    print(f"  {c}: {cnt}")
conn.close()

