import sys
sys.path.insert(0, ".")
import sqlite3
import pandas as pd
from eval.oracle import PlacementOracle

oracle = PlacementOracle()
df = oracle.filter_df(company='Amazon', branch='CSE')
print("Oracle Amazon CSE offers:")
print(df[['batch', 'student_id', 'name', 'company_raw', 'ctc_lpa']])

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()
cur.execute("""
    SELECT s.batch_id, s.student_id, c.canonical_name, c.raw_name, o.ctc_lpa, o.offer_type
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN branches b ON s.branch_code = b.branch_code
    JOIN companies c ON o.company_id = c.company_id
    WHERE c.canonical_name LIKE 'Amazon' AND b.short_name = 'CSE'
""")
db_rows = cur.fetchall()
print("\nDB Amazon CSE offers (count={}):".format(len(db_rows)))
for r in db_rows:
    print(r)
