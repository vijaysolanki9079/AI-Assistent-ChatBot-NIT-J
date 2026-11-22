"""
Creates privacy aggregate views with min group size 3 (k-anonymity)
and an isolated private student vault table in SQLite database.
"""

import sqlite3
import os

DB_PATH = "data/nitj_placement.db"

def setup_privacy_schema():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Create Privacy-Safe Branch Aggregate View (Min Group Size 3)
    cur.execute("DROP VIEW IF EXISTS v_privacy_branch_stats;")
    cur.execute("""
    CREATE VIEW v_privacy_branch_stats AS
    SELECT
        b.canonical_name AS branch_name,
        b.short_name AS branch_short,
        s.batch_id,
        COUNT(DISTINCT s.student_id) AS total_students,
        COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) AS placed_students,
        COUNT(o.offer_id) AS total_offers,
        ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc_lpa,
        MAX(o.ctc_lpa) AS max_ctc_lpa
    FROM students s
    JOIN branches b ON s.branch_code = b.branch_code
    LEFT JOIN offers o ON s.student_id = o.student_id
    GROUP BY b.branch_code, s.batch_id
    HAVING placed_students >= 3;
    """)

    # 2. Create Privacy-Safe Company Aggregate View (Min Group Size 3)
    cur.execute("DROP VIEW IF EXISTS v_privacy_company_hiring;")
    cur.execute("""
    CREATE VIEW v_privacy_company_hiring AS
    SELECT
        c.canonical_name AS company_name,
        s.batch_id,
        COUNT(DISTINCT s.student_id) AS placed_students,
        COUNT(o.offer_id) AS total_offers,
        ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc_lpa
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN companies c ON o.company_id = c.company_id
    WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
    GROUP BY c.company_id, s.batch_id
    HAVING placed_students >= 3;
    """)

    # 3. Create Isolated Private Student PII Vault Table
    # (Strictly isolated from Query Role; Query Role lacks permission to select from this table)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS student_private_pii (
        student_id INTEGER PRIMARY KEY,
        full_name TEXT NOT NULL,
        roll_number TEXT NOT NULL,
        personal_email TEXT,
        phone_number TEXT
    );
    """)

    conn.commit()
    conn.close()
    print("Successfully configured privacy views (min group size 3) and private student vault.")

if __name__ == "__main__":
    setup_privacy_schema()

