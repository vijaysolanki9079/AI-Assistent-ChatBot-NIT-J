import openpyxl, os, sqlite3

DB_PATH = "data/nitj_placement.db"
DATA_DIR = "NIT-J data"
files = [
    "2020-24 and 2022-24 Batch_Placement Database.xlsx",
    "2021-25 and 2023-25 Batch_Placement Database.xlsx",
    "2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx"
]

SUMMARY_SHEETS = {
    "full details", "count wise details", "count", "copy of full details", "m.tech 23-25 full details"
}

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS student_private_pii (
    student_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    roll_number TEXT NOT NULL,
    personal_email TEXT,
    phone_number TEXT
);
""")

count_inserted = 0
for f in files:
    fpath = os.path.join(DATA_DIR, f)
    wb = openpyxl.load_workbook(fpath, read_only=True)
    for sname in wb.sheetnames:
        s_low = sname.strip().lower()
        if s_low in SUMMARY_SHEETS:
            continue
        sheet = wb[sname]
        h_row = None
        headers = {}
        r_idx = 0
        for row in sheet.iter_rows(values_only=True):
            r_idx += 1
            row_str = [str(v or "").strip().lower() for v in row]
            for c_idx, val in enumerate(row_str):
                if "roll" in val and "no" in val:
                    h_row = r_idx
                    break
            if h_row:
                for c_idx, val in enumerate(row):
                    if val is not None and str(val).strip():
                        headers[c_idx] = str(val).strip().replace("\n", " ").lower()
                break

        if not h_row:
            continue

        for row in sheet.iter_rows(min_row=h_row + 1, values_only=True):
            if not any(row):
                continue
            roll_val = None
            name_val = None
            email_val = None
            phone_val = None

            for c_idx, h_name in headers.items():
                val = row[c_idx] if c_idx < len(row) else None
                if not val:
                    continue
                if "roll" in h_name and "no" in h_name:
                    roll_val = val
                elif "name" in h_name and "company" not in h_name and "father" not in h_name:
                    name_val = val
                elif "email" in h_name or "mail" in h_name:
                    email_val = val
                elif "phone" in h_name or "mobile" in h_name or "contact" in h_name:
                    phone_val = val

            clean_roll = str(roll_val).replace(".0", "").strip() if roll_val is not None else ""
            if clean_roll == "2020 Batch" and name_val and "Santosh" in str(name_val):
                clean_roll = "20103104"

            if not clean_roll or len(clean_roll) < 5 or not clean_roll[:5].isdigit():
                continue

            clean_name = str(name_val).strip() if name_val else ""
            if clean_name and clean_name.lower() not in ["none", "null", "-", "na"]:
                cur.execute("""
                INSERT OR REPLACE INTO student_private_pii 
                (student_id, full_name, roll_number, personal_email, phone_number)
                VALUES (?, ?, ?, ?, ?)
                """, (clean_roll, clean_name, clean_roll, str(email_val or ""), str(phone_val or "")))
                count_inserted += 1

    wb.close()

conn.commit()
print(f"Total student_private_pii rows now: {cur.execute('SELECT COUNT(*) FROM student_private_pii').fetchone()[0]}")
print("Sample 5:", cur.execute("SELECT student_id, full_name, roll_number FROM student_private_pii LIMIT 5").fetchall())
conn.close()

