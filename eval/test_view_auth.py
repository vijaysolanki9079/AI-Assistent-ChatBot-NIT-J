import sqlite3

conn = sqlite3.connect(':memory:')
cur = conn.cursor()

cur.executescript("""
CREATE TABLE student_private_pii (
    student_id INTEGER PRIMARY KEY,
    full_name TEXT,
    roll_number TEXT,
    personal_email TEXT,
    phone_number TEXT
);
CREATE TABLE students (
    student_id TEXT PRIMARY KEY,
    batch_id TEXT,
    branch_code TEXT
);
CREATE TABLE offers (
    offer_id INTEGER PRIMARY KEY,
    student_id TEXT,
    company_name TEXT,
    role TEXT,
    offer_type TEXT
);

INSERT INTO student_private_pii VALUES (1, 'Alice Smith', '21103001', 'alice@gmail.com', '9876543210');
INSERT INTO students VALUES ('1', '2021-2025', '103');
INSERT INTO offers VALUES (10, '1', 'Google', 'SDE', 'FTE');

CREATE VIEW v_selected_students_public AS
SELECT 
    p.full_name AS student_name,
    s.branch_code AS branch,
    s.batch_id AS batch,
    o.company_name AS company,
    o.role AS role,
    o.offer_type AS offer_type
FROM offers o
JOIN students s ON o.student_id = s.student_id
JOIN student_private_pii p ON p.student_id = s.student_id;
""")

log = []
def auth(action, arg1, arg2, db, trigger):
    log.append((action, arg1, arg2, db, trigger))
    return sqlite3.SQLITE_OK

conn.set_authorizer(auth)
res = conn.execute("SELECT student_name, company FROM v_selected_students_public").fetchall()
print("Query result:", res)
for entry in log:
    print("Action:", entry)

