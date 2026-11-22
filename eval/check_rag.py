import sqlite3
import json

conn = sqlite3.connect('data/nitj_placement.db')
c = conn.cursor()

print("--- MICROSOFT EXPERIENCES ---")
c.execute("SELECT technical_topics, rounds_json, preparation_tips FROM interview_experiences WHERE company_name = 'Microsoft' LIMIT 2;")
for r in c.fetchall():
    print("Topics:", r[0])
    print("Rounds:", r[1])
    print("Tips:", r[2])

print("\n--- AMAZON EXPERIENCES ---")
c.execute("SELECT technical_topics, rounds_json, key_questions_json FROM interview_experiences WHERE company_name = 'Amazon' LIMIT 2;")
for r in c.fetchall():
    print("Topics:", r[0])
    print("Rounds:", r[1])
    print("Questions:", r[2])

print("\n--- ORACLE EXPERIENCES ---")
c.execute("SELECT technical_topics, rounds_json, preparation_tips FROM interview_experiences WHERE company_name = 'Oracle' LIMIT 2;")
for r in c.fetchall():
    print("Topics:", r[0])
    print("Rounds:", r[1])
    print("Tips:", r[2])
