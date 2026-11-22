import sys
sys.path.insert(0, ".")
import sqlite3
import pandas as pd
from eval.oracle import PlacementOracle

oracle = PlacementOracle()
o_df = oracle.filter_df(batch='2020-2024')

conn = sqlite3.connect('data/nitj_placement.db')
cur = conn.cursor()
cur.execute("""
    SELECT s.student_id, c.canonical_name, o.offer_type
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN companies c ON o.company_id = c.company_id
    WHERE s.batch_id = '2020-2024' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
""")
db_set = set((r[0].replace('.0', ''), r[1].lower()) for r in cur.fetchall())

diff = []
for _, row in o_df.iterrows():
    sid = str(row['student_id']).replace('.0', '')
    comp = str(row['company']).lower()
    if (sid, comp) not in db_set:
        diff.append((sid, row['name'], row['branch'], row['company'], row['company_raw']))

print(f"Difference count: {len(diff)}")
for d in diff[:10]:
    print(d)
