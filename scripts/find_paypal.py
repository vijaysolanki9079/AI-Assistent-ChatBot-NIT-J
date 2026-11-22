import sqlite3, json

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()
cur.execute("SELECT company_id, canonical_name FROM companies WHERE canonical_name LIKE '%pay%' OR canonical_name LIKE '%pal%'")
print("Companies with pay/pal:", cur.fetchall())

# Also check raw companies json
with open("scripts/all_raw_companies.json") as f:
    comps = json.load(f)
for c in comps:
    if "pay" in c.lower() or "pal" in c.lower():
        print("Raw company:", repr(c))

conn.close()

