import sqlite3
import os
import glob
import pandas as pd
import yaml

print("--- 1. CHECK ADOBE IN DATABASE ---")
conn = sqlite3.connect('data/nitj_placement.db')
c = conn.cursor()

c.execute("SELECT * FROM companies WHERE LOWER(canonical_name) LIKE '%adobe%'")
adobe_companies = c.fetchall()
print("Companies matching adobe:", adobe_companies)

c.execute("SELECT ca.alias, c.canonical_name FROM company_aliases ca JOIN companies c ON ca.company_id = c.company_id WHERE LOWER(ca.alias) LIKE '%adobe%' OR LOWER(c.canonical_name) LIKE '%adobe%'")
adobe_aliases = c.fetchall()
print("Aliases matching adobe:", adobe_aliases)

c.execute("""
    SELECT o.offer_id, o.ctc_lpa, o.offer_type, c.canonical_name, s.batch_id, s.branch_code 
    FROM offers o 
    JOIN companies c ON o.company_id = c.company_id 
    JOIN students s ON o.student_id = s.student_id 
    WHERE LOWER(c.canonical_name) LIKE '%adobe%'
""")
adobe_offers = c.fetchall()
print("Offers matching adobe:", len(adobe_offers), adobe_offers)

print("\n--- 2. CHECK ADOBE IN RAW EXCEL FILES ---")
for f in glob.glob("NIT-J data/*.xlsx"):
    xl = pd.ExcelFile(f)
    print("File:", os.path.basename(f), "Sheets:", xl.sheet_names)
    for s in xl.sheet_names:
        df = xl.parse(s)
        # Search all columns
        mask = df.astype(str).apply(lambda col: col.str.contains('adobe', case=False, na=False))
        if mask.any().any():
            matched_rows = df[mask.any(axis=1)]
            print(f"  -> Found in sheet '{s}': {len(matched_rows)} rows")
            for idx, r in matched_rows.iterrows():
                # print relevant columns
                cols_preview = {k: v for k, v in r.items() if pd.notna(v) and str(v).strip()}
                print("     Row:", cols_preview)

print("\n--- 3. TEST PLANNER EXECUTION FOR ADOBE ---")
import sys
sys.path.insert(0, ".")
from src.nlp.query_planner import QueryPlanner

planner = QueryPlanner()
res = planner.plan_and_execute("adobe placements stats")
print("Status:", res.get("status"))
print("Spec:", res.get("query_spec"))
print("SQL:", res.get("sql"))
print("Answer:", res.get("answer"))

print("\n--- 4. TEST PLANNER FOR 25' BATCH ECE ---")
res2 = planner.plan_and_execute("list me the companies that visited for ECE branch for 25' batch")
print("Spec 2:", res2.get("query_spec"))
print("SQL 2:", res2.get("sql"))
print("Answer 2:", res2.get("answer"))
