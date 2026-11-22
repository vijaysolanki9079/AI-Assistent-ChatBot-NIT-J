import sqlite3

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()

cur.execute("SELECT company_name, title FROM interview_experiences WHERE full_text LIKE '%Uber%'")
print("Uber in full_text:", cur.fetchall())

cur.execute("SELECT company_name, title FROM interview_experiences WHERE full_text LIKE '%Goldman%'")
print("Goldman in full_text:", cur.fetchall())

