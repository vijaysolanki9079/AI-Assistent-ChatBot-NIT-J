import sqlite3

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()

# Check if Uber and Goldman Sachs exist in companies
cur.execute("SELECT canonical_name FROM companies WHERE canonical_name IN ('Uber', 'Goldman Sachs')")
print("Companies in DB:", cur.fetchall())

