import sqlite3

def create_views_and_aliases(db_path="data/nitj_placement.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. Create v_offers_flat
    cur.execute("DROP VIEW IF EXISTS v_offers_flat;")
    cur.execute("""
    CREATE VIEW v_offers_flat AS
    SELECT 
        o.offer_id,
        o.student_id,
        c.canonical_name AS company,
        c.sector AS sector,
        b.short_name AS branch_short_name,
        b.canonical_name AS branch_full_name,
        b.degree AS degree,
        s.batch_id AS batch_id,
        bt.passout_year AS passout_year,
        o.offer_type AS offer_type,
        o.ctc_lpa AS ctc_lpa,
        o.stipend_monthly_inr AS stipend_monthly_inr,
        o.profile AS profile,
        o.offer_date AS offer_date
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN branches b ON s.branch_code = b.branch_code
    JOIN companies c ON o.company_id = c.company_id
    LEFT JOIN batches bt ON s.batch_id = bt.batch_id;
    """)
    print("Created view v_offers_flat")
    
    # 2. Create v_selected_students_public
    # Safe public view: student_name, branch, batch, company, role, offer_type
    # STRICTLY NO roll numbers, phones, emails, addresses, parents, HR contacts.
    cur.execute("DROP VIEW IF EXISTS v_selected_students_public;")
    cur.execute("""
    CREATE VIEW v_selected_students_public AS
    SELECT 
        p.full_name AS student_name,
        b.short_name AS branch,
        s.batch_id AS batch,
        c.canonical_name AS company,
        o.profile AS role,
        o.offer_type AS offer_type
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN branches b ON s.branch_code = b.branch_code
    JOIN companies c ON o.company_id = c.company_id
    JOIN student_private_pii p ON p.student_id = s.student_id;
    """)
    print("Created view v_selected_students_public")
    
    # 3. Create batch_aliases table
    cur.execute("DROP TABLE IF EXISTS batch_aliases;")
    cur.execute("""
    CREATE TABLE batch_aliases (
        alias TEXT PRIMARY KEY,
        batch_id TEXT REFERENCES batches(batch_id)
    );
    """)
    
    # Populate batch_aliases
    aliases = [
        # 2021-2025 (Class of 2025)
        ("25'", "2021-2025"),
        ("'25", "2021-2025"),
        ("25", "2021-2025"),
        ("2025", "2021-2025"),
        ("2025 batch", "2021-2025"),
        ("batch of 2025", "2021-2025"),
        ("batch 2025", "2021-2025"),
        ("2021-25", "2021-2025"),
        ("21-25", "2021-2025"),
        ("class of 25", "2021-2025"),
        ("class of 2025", "2021-2025"),
        ("2021-2025", "2021-2025"),
        ("2021-2025 batch", "2021-2025"),
        ("2021-25 batch", "2021-2025"),
        ("passing 2025", "2021-2025"),
        ("passout 2025", "2021-2025"),
        ("2025 passout", "2021-2025"),
        
        # 2020-2024 (Class of 2024)
        ("24'", "2020-2024"),
        ("'24", "2020-2024"),
        ("24", "2020-2024"),
        ("2024", "2020-2024"),
        ("2024 batch", "2020-2024"),
        ("batch of 2024", "2020-2024"),
        ("batch 2024", "2020-2024"),
        ("2020-24", "2020-2024"),
        ("20-24", "2020-2024"),
        ("class of 24", "2020-2024"),
        ("class of 2024", "2020-2024"),
        ("2020-2024", "2020-2024"),
        ("2020-2024 batch", "2020-2024"),
        ("2020-24 batch", "2020-2024"),
        ("passing 2024", "2020-2024"),
        ("passout 2024", "2020-2024"),
        ("2024 passout", "2020-2024"),
        
        # 2022-2026 (Class of 2026)
        ("26'", "2022-2026"),
        ("'26", "2022-2026"),
        ("26", "2022-2026"),
        ("2026", "2022-2026"),
        ("2026 batch", "2022-2026"),
        ("batch of 2026", "2022-2026"),
        ("batch 2026", "2022-2026"),
        ("2022-26", "2022-2026"),
        ("22-26", "2022-2026"),
        ("class of 26", "2022-2026"),
        ("class of 2026", "2022-2026"),
        ("2022-2026", "2022-2026"),
        ("2022-2026 batch", "2022-2026"),
        ("2022-26 batch", "2022-2026"),
        ("passing 2026", "2022-2026"),
        ("passout 2026", "2022-2026"),
        ("2026 passout", "2022-2026"),

        # 2023-2027 (Class of 2027)
        ("27'", "2023-2027"),
        ("'27", "2023-2027"),
        ("27", "2023-2027"),
        ("2027", "2023-2027"),
        ("2027 batch", "2023-2027"),
        ("batch of 2027", "2023-2027"),
        ("batch 2027", "2023-2027"),
        ("2023-27", "2023-2027"),
        ("23-27", "2023-2027"),
        ("class of 27", "2023-2027"),
        ("class of 2027", "2023-2027"),
        ("2023-2027", "2023-2027"),
        ("2023-2027 batch", "2023-2027"),
        ("2023-27 batch", "2023-2027"),
        ("passing 2027", "2023-2027"),
        ("passout 2027", "2023-2027"),
        ("2027 passout", "2023-2027")
    ]
    cur.executemany("INSERT OR REPLACE INTO batch_aliases (alias, batch_id) VALUES (?, ?)", aliases)
    conn.commit()
    print(f"Populated batch_aliases with {len(aliases)} mappings.")
    
    # Quick sanity tests
    cur.execute("SELECT COUNT(*) FROM v_offers_flat")
    print("v_offers_flat row count:", cur.fetchone()[0])
    
    cur.execute("SELECT COUNT(*) FROM v_selected_students_public")
    print("v_selected_students_public row count:", cur.fetchone()[0])
    
    cur.execute("SELECT * FROM batch_aliases WHERE alias IN ('25''', '''25', '2025')")
    print("Sample batch_aliases:", cur.fetchall())
    
    conn.close()

if __name__ == "__main__":
    create_views_and_aliases()

