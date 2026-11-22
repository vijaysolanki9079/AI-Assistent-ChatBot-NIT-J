import sqlite3

conn = sqlite3.connect('data/nitj_placement.db')
cur = conn.cursor()

for cname in ['Google', 'Microsoft', 'Amazon']:
    cur.execute(f'''
        SELECT COUNT(DISTINCT s.student_id) 
        FROM offers o 
        JOIN students s ON o.student_id = s.student_id 
        JOIN companies c ON o.company_id = c.company_id 
        WHERE c.canonical_name = "{cname}" 
          AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
    ''')
    total_placed = cur.fetchone()[0]

    cur.execute(f'''
        SELECT DISTINCT author, branch, batch, role 
        FROM interview_experiences 
        WHERE company_name LIKE "%{cname}%" 
          AND author IS NOT NULL AND TRIM(author) != "" 
        ORDER BY author ASC
    ''')
    authors = cur.fetchall()
    print(f"Company: {cname} | Total Placed: {total_placed}")
    for a in authors[:4]:
        name, branch, batch, role = a
        details = []
        if branch: details.append(branch)
        if batch: details.append(batch)
        if role: details.append(role)
        detail_str = f" ({', '.join(details)})" if details else ""
        print(f"  • {name.title()}{detail_str}")
    print()

conn.close()

