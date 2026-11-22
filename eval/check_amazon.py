import sqlite3

conn = sqlite3.connect('data/nitj_placement.db')
c = conn.cursor()

c.execute("SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies comp ON o.company_id = comp.company_id WHERE comp.canonical_name = 'Amazon' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');")
print('Amazon distinct placed students (FTE/PPO):', c.fetchone()[0])

c.execute("SELECT COUNT(o.offer_id) FROM offers o JOIN companies comp ON o.company_id = comp.company_id WHERE comp.canonical_name = 'Amazon';")
print('Amazon total offers (all types):', c.fetchone()[0])

c.execute("SELECT s.batch_id, o.offer_type, COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies comp ON o.company_id = comp.company_id WHERE comp.canonical_name = 'Amazon' GROUP BY s.batch_id, o.offer_type;")
for r in c.fetchall():
    print(r)

