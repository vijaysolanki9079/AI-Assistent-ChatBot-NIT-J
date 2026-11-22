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
    roll_no TEXT,
    email TEXT,
    phone TEXT,
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
INSERT INTO students VALUES ('1', '21103001', 'alice@gmail.com', '9876543210', '2021-2025', '103');
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

WRITE_OPS = {
    sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
    sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_INDEX,
    sqlite3.SQLITE_CREATE_VIEW, sqlite3.SQLITE_CREATE_TRIGGER,
    sqlite3.SQLITE_CREATE_VTABLE,
    sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_INDEX,
    sqlite3.SQLITE_DROP_VIEW, sqlite3.SQLITE_DROP_TRIGGER,
    sqlite3.SQLITE_DROP_VTABLE,
    sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH
}

FORBIDDEN_COLUMNS = {
    "roll_no", "roll_number", "email", "personal_email", "phone", "phone_number"
}

def readonly_authorizer(action, arg1, arg2, db, trigger):
    if action in WRITE_OPS:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_READ:
        table = (arg1 or "").lower()
        col = (arg2 or "").lower()
        # Direct access to student_private_pii is denied
        if table == "student_private_pii" and trigger != "v_selected_students_public":
            return sqlite3.SQLITE_DENY
        # Any access to roll numbers, emails, phone numbers is strictly denied
        if col in FORBIDDEN_COLUMNS:
            return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK

conn.set_authorizer(readonly_authorizer)

# 1. Test public view works
res = conn.execute("SELECT student_name, company FROM v_selected_students_public").fetchall()
print("1. View query (should succeed):", res)

# 2. Test direct access to student_private_pii is denied
try:
    conn.execute("SELECT * FROM student_private_pii").fetchall()
    print("2. Direct PII read: FAILED TO BLOCK!")
except sqlite3.DatabaseError as e:
    print("2. Direct PII read correctly blocked:", e)

# 3. Test direct access to students.roll_no is denied
try:
    conn.execute("SELECT roll_no FROM students").fetchall()
    print("3. Roll no read: FAILED TO BLOCK!")
except sqlite3.DatabaseError as e:
    print("3. Roll no read correctly blocked:", e)

# 4. Test write is denied
try:
    conn.execute("INSERT INTO offers (offer_id) VALUES (99)")
    print("4. Insert: FAILED TO BLOCK!")
except sqlite3.DatabaseError as e:
    print("4. Insert correctly blocked:", e)

try:
    conn.execute("DROP TABLE offers")
    print("5. Drop table: FAILED TO BLOCK!")
except sqlite3.DatabaseError as e:
    print("5. Drop table correctly blocked:", e)
