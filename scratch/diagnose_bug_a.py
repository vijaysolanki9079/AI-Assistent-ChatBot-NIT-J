import sys
import os
sys.path.insert(0, os.path.abspath("."))
import sqlite3
import json
from src.nlp.query_planner import QueryPlanner

planner = QueryPlanner()
question = "name of ppl who got into IndiaMART in CSE"

print("==================================================")
print("1. REPRODUCTION OF THE BUG")
print("==================================================")
print(f"User Query: '{question}'\n")

res = planner.plan_and_execute(question)
print("Bot Stated Answer:")
print(res.get("answer"))
print()
print("Executed SQL Query for Count:")
count_sql = res.get("sql")
print(count_sql)
print()
print("Raw Result from Count Query:")
print(res.get("raw_result"))

print("\n==================================================")
print("2. DATABASE AUDIT & CAUSE OF INCONSISTENCY")
print("==================================================")
conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()

# Run count query directly
cur.execute(count_sql)
count_rows = cur.fetchall()
print("Count Query Raw Rows Returned:")
print(count_rows)

# Inspect offers table for IndiaMart in CSE
cur.execute("""
    SELECT s.student_id, s.batch_id, b.short_name, o.offer_type, o.ctc_lpa
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN branches b ON s.branch_code = b.branch_code
    JOIN companies c ON o.company_id = c.company_id
    WHERE c.canonical_name = 'IndiaMart'
      AND b.short_name = 'CSE'
      AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');
""")
offers_rows = cur.fetchall()
print("\nOffers Table Raw Rows (Count = 3):")
for r in offers_rows:
    print(" ", r)

# Inspect the separate query used for names in query_planner:
auth_sql = "SELECT DISTINCT author, branch, batch, role FROM interview_experiences WHERE company_name LIKE '%IndiaMart%' AND author IS NOT NULL AND TRIM(author) != '' ORDER BY author ASC LIMIT 8;"
print("\nSeparate Names Query (from interview_experiences table):")
print(auth_sql)

cur.execute(auth_sql)
names_rows = cur.fetchall()
print("Names Query Raw Rows Returned (Count = 2):")
for r in names_rows:
    print(" ", r)

print("\nCheck Branch of the 2 authors:")
for a, br, bat, rol in names_rows:
    print(f"  Author: '{a}', Branch: '{br}', Batch: '{bat}'")

conn.close()
