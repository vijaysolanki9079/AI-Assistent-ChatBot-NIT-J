import openpyxl, os, re, sqlite3
from collections import defaultdict, Counter
import json

DATA_DIR = "NIT-J data"
DB_PATH = "data/nitj_placement.db"
os.makedirs("data", exist_ok=True)

files = [
    "2020-24 and 2022-24 Batch_Placement Database.xlsx",
    "2021-25 and 2023-25 Batch_Placement Database.xlsx",
    "2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx"
]

SUMMARY_SHEETS = {
    "full details", "count wise details", "count", "copy of full details", "m.tech 23-25 full details"
}

# 1. Branch code to Canonical Branch metadata
BRANCH_MASTER = {
    "102": {"name": "Civil Engineering", "short": "CE", "degree": "B.Tech", "division": "Core"},
    "103": {"name": "Computer Science and Engineering", "short": "CSE", "degree": "B.Tech", "division": "Circuit"},
    "104": {"name": "Electronics and Communication Engineering", "short": "ECE", "degree": "B.Tech", "division": "Circuit"},
    "106": {"name": "Instrumentation and Control Engineering", "short": "ICE", "degree": "B.Tech", "division": "Circuit"},
    "109": {"name": "Mechanical Engineering", "short": "ME", "degree": "B.Tech", "division": "Core"},
    "110": {"name": "Textile Technology", "short": "TT", "degree": "B.Tech", "division": "Core"},
    "111": {"name": "Biotechnology", "short": "BT", "degree": "B.Tech", "division": "Core"},
    "112": {"name": "Chemical Engineering", "short": "CHE", "degree": "B.Tech", "division": "Core"},
    "113": {"name": "Industrial and Production Engineering", "short": "IPE", "degree": "B.Tech", "division": "Core"},
    "117": {"name": "Data Science and Engineering", "short": "DSE", "degree": "B.Tech", "division": "Circuit"},
    "118": {"name": "Electronics and VLSI Engineering", "short": "VLSI", "degree": "B.Tech", "division": "Circuit"},
    "124": {"name": "Information Technology", "short": "IT", "degree": "B.Tech", "division": "Circuit"},
    "126": {"name": "Electrical Engineering", "short": "EE", "degree": "B.Tech", "division": "Circuit"},
    "311": {"name": "Chemistry", "short": "CY", "degree": "M.Sc", "division": "Sciences"},
    "312": {"name": "Mathematics", "short": "MA", "degree": "M.Sc", "division": "Sciences"},
    "313": {"name": "Physics", "short": "PH", "degree": "M.Sc", "division": "Sciences"},
    "701": {"name": "Humanities and Management (MBA)", "short": "MBA", "degree": "MBA", "division": "Management"},
    # M.Tech Codes
    "201": {"name": "M.Tech Artificial Intelligence", "short": "MTech AI", "degree": "M.Tech", "division": "Circuit"},
    "901": {"name": "M.Tech Artificial Intelligence", "short": "MTech AI", "degree": "M.Tech", "division": "Circuit"},
    "202": {"name": "M.Tech Structural and Construction Engineering", "short": "MTech CE", "degree": "M.Tech", "division": "Core"},
    "902": {"name": "M.Tech Structural and Construction Engineering", "short": "MTech CE", "degree": "M.Tech", "division": "Core"},
    "203": {"name": "M.Tech Computer Science & Engineering", "short": "MTech CSE", "degree": "M.Tech", "division": "Circuit"},
    "903": {"name": "M.Tech Computer Science & Engineering", "short": "MTech CSE", "degree": "M.Tech", "division": "Circuit"},
    "204": {"name": "M.Tech VLSI Design", "short": "MTech VLSI", "degree": "M.Tech", "division": "Circuit"},
    "904": {"name": "M.Tech VLSI Design", "short": "MTech VLSI", "degree": "M.Tech", "division": "Circuit"},
    "205": {"name": "M.Tech Industrial Engineering and Data Analytics", "short": "MTech IPE", "degree": "M.Tech", "division": "Core"},
    "905": {"name": "M.Tech Industrial Engineering and Data Analytics", "short": "MTech IPE", "degree": "M.Tech", "division": "Core"},
    "206": {"name": "M.Tech Control and Instrumentation Engineering", "short": "MTech ICE", "degree": "M.Tech", "division": "Circuit"},
    "906": {"name": "M.Tech Control and Instrumentation Engineering", "short": "MTech ICE", "degree": "M.Tech", "division": "Circuit"},
    "209": {"name": "M.Tech Thermal and Energy Engineering", "short": "MTech ME", "degree": "M.Tech", "division": "Core"},
    "909": {"name": "M.Tech Thermal and Energy Engineering", "short": "MTech ME", "degree": "M.Tech", "division": "Core"},
    "210": {"name": "M.Tech Textile Engineering and Management", "short": "MTech TT", "degree": "M.Tech", "division": "Core"},
    "910": {"name": "M.Tech Textile Engineering and Management", "short": "MTech TT", "degree": "M.Tech", "division": "Core"}
}

# 2. Company Aliases & Overrides
with open("scripts/company_normalized_map.json") as f:
    COMP_MAP_DATA = json.load(f)
COMPANY_NORMALIZER = COMP_MAP_DATA["raw_to_canonical"]

# 3. Status normalizer
def normalize_status(raw_status, date_val=""):
    s = (raw_status or "").strip()
    d = (date_val or "").strip().lower()
    low = s.lower()
    
    # Check if PPO is in date or status
    is_ppo = "ppo" in low or "ppo" in d
    is_offcampus = "offcampus" in low or "offcampus" in d or "off-campus" in low or "off campus" in low
    
    if "intern+ppo" in low or "inter+ppo" in low or "intern + ppo" in low or "intern+ ppo" in low:
        return "Intern+PPO", "Off-campus" if is_offcampus else "On-campus"
    if "intern+fte" in low or "intern + fte" in low or "long intern (full time confirmed)" in low:
        return "Intern+FTE", "Off-campus" if is_offcampus else "On-campus"
    if is_ppo and ("placed" in low or "engineer" in low or not low):
        return "PPO", "Off-campus" if is_offcampus else "On-campus"
    if "long intern" in low or "11 month" in low or "one year" in low or "1 year" in low:
        return "Long Intern", "Off-campus" if is_offcampus else "On-campus"
    if "summer intern" in low or "interned" in low or low == "intern":
        return "Intern", "Off-campus" if is_offcampus else "On-campus"
    if "placed" in low or "fte" in low:
        return "FTE", "Off-campus" if is_offcampus else "On-campus"
    if is_offcampus:
        return "FTE", "Off-campus"
    if not s and (d or date_val):
        return "FTE", "On-campus"
    return "FTE", "On-campus"

# 4. Package parser
def parse_package(pkg_val, comp_name="", is_stipend_col=False):
    if pkg_val is None:
        return None, None, "NULL", "undisclosed"
    raw = str(pkg_val).strip()
    if not raw or raw in ["-", "NULL", "None", "NA", "N.A", "na"]:
        return None, None, raw, "undisclosed"
    if raw.lower() == "unpaid":
        return None, 0.0, raw, "unpaid"
    if raw == "2023-12-18 00:00:00":
        return None, None, raw, "unconfirmed_date_in_package"
        
    # Compound checks
    # e.g. 40K+12.8LPA -> ctc=12.8, stipend=40000
    m_comp = re.search(r'(\d+)\s*[kK]\s*[\+,]\s*(\d+(?:\.\d+)?)\s*(?:lpa|lac)?', raw, re.I)
    if m_comp:
        stipend_k = float(m_comp.group(1))
        ctc = float(m_comp.group(2))
        return ctc, stipend_k * 1000.0, raw, "compound_split"
        
    m_convert = re.search(r'(\d+)\s*[kK].*?(\d+(?:\.\d+)?)\s*lpa', raw, re.I)
    if m_convert:
        stipend_k = float(m_convert.group(1))
        ctc = float(m_convert.group(2))
        return ctc, stipend_k * 1000.0, raw, "compound_split"
        
    # Pure stipend checks (e.g. 45K, 1.25Lac PM, 75K PM)
    m_pm = re.search(r'(\d+(?:\.\d+)?)\s*(?:lac|lakh)\s*pm', raw, re.I)
    if m_pm:
        stipend_lac = float(m_pm.group(1))
        return None, stipend_lac * 100000.0, raw, "stipend_only"
        
    m_k = re.match(r'^(\d+(?:\.\d+)?)\s*[kK](?:\s*pm|\s*per month)?$', raw, re.I)
    if m_k:
        stipend_k = float(m_k.group(1))
        return None, stipend_k * 1000.0, raw, "stipend_only"

    # If column was explicitly named 'Stipend' (e.g. B.Tech 2023-27 summer intern, 3rd year internship)
    clean_num = re.sub(r'(?i)\s*lpa', '', raw).strip()
    try:
        val = float(clean_num)
        if is_stipend_col:
            if val <= 5.0:
                # e.g. 1.25 Lac PM -> 125,000 INR
                return None, val * 100000.0, raw, "stipend_only"
            elif val <= 500.0:
                # e.g. 45 -> 45,000 INR
                return None, val * 1000.0, raw, "stipend_only"
            else:
                return None, val, raw, "stipend_only"

        # In standard Package column:
        if val >= 1000.0:
            return None, val, raw, "stipend_only"
        return val, None, raw, "verified_ctc"
    except ValueError:
        return None, None, raw, "unparseable_string"

# 5. Date normalizer
def normalize_date(date_val):
    if not date_val:
        return None
    s = str(date_val).strip()
    if s.upper() in ["GENERAL", "OBC-NCL", "SC", "ST", "GEN-EWS", "GEN", "EWS", "OBC"]:
        return None
    # Remove PPO / Offcampus from date
    s = re.sub(r'(?i)\s*(ppo|offcampus|intern)', '', s).strip()
    if not s:
        return None
    # Handle typos e.g. 10.012.2024 -> 10.12.2024
    s = s.replace(".012.", ".12.").replace(".011.", ".11.")
    
    # Check dd.mm.yyyy or dd/mm/yyyy
    m = re.match(r'^(\d{1,2})[\.\/-](\d{1,2})[\.\/-](\d{2,4})', s)
    if m:
        day, month, year = m.groups()
        if len(year) == 2:
            year = "20" + year
        try:
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        except ValueError:
            return None
            
    # Check yyyy-mm-dd
    m_iso = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})', s)
    if m_iso:
        y, m, d = m_iso.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        
    return None

def build_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Create tables
    cur.executescript("""
    DROP VIEW IF EXISTS v_placed_students;
    DROP VIEW IF EXISTS v_fte_ppo_offers;
    DROP VIEW IF EXISTS v_internship_offers;
    DROP VIEW IF EXISTS v_branch_year_stats;
    DROP TABLE IF EXISTS offers;
    DROP TABLE IF EXISTS students;
    DROP TABLE IF EXISTS company_aliases;
    DROP TABLE IF EXISTS companies;
    DROP TABLE IF EXISTS branch_aliases;
    DROP TABLE IF EXISTS branches;
    DROP TABLE IF EXISTS batches;

    CREATE TABLE batches (
        batch_id TEXT PRIMARY KEY,
        admission_year INTEGER,
        passout_year INTEGER,
        degree TEXT
    );

    CREATE TABLE branches (
        branch_code TEXT PRIMARY KEY,
        canonical_name TEXT NOT NULL,
        short_name TEXT NOT NULL,
        degree TEXT NOT NULL,
        division TEXT
    );

    CREATE TABLE branch_aliases (
        alias TEXT PRIMARY KEY,
        branch_code TEXT REFERENCES branches(branch_code)
    );

    CREATE TABLE companies (
        company_id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_name TEXT UNIQUE NOT NULL,
        sector TEXT DEFAULT 'Other'
    );

    CREATE TABLE company_aliases (
        alias TEXT PRIMARY KEY,
        company_id INTEGER REFERENCES companies(company_id)
    );

    CREATE TABLE students (
        student_id TEXT PRIMARY KEY,
        batch_id TEXT REFERENCES batches(batch_id),
        branch_code TEXT REFERENCES branches(branch_code),
        gender TEXT,
        category TEXT,
        source_branch_raw TEXT,
        is_branch_conflict INTEGER DEFAULT 0
    );

    CREATE TABLE offers (
        offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT REFERENCES students(student_id),
        company_id INTEGER REFERENCES companies(company_id),
        offer_type TEXT NOT NULL,
        ctc_lpa REAL,
        stipend_monthly_inr REAL,
        package_raw TEXT,
        package_reason TEXT,
        offer_date TEXT,
        offer_mode TEXT,
        profile TEXT,
        source_file TEXT,
        source_sheet TEXT,
        source_row INTEGER,
        UNIQUE(student_id, company_id, offer_type, offer_date)
    );
    """)
    
    # Populate branches
    for bcode, meta in BRANCH_MASTER.items():
        cur.execute("INSERT OR REPLACE INTO branches VALUES (?, ?, ?, ?, ?)",
                    (bcode, meta["name"], meta["short"], meta["degree"], meta["division"]))
                    
    # Insert common branch aliases
    aliases = [
        ("CSE", "103"), ("Computer Science", "103"), ("Computer Science and Engineering", "103"),
        ("IT", "124"), ("Information Technology", "124"),
        ("ECE", "104"), ("Electronics", "104"), ("Electronics and Communication Engineering", "104"),
        ("EE", "126"), ("Electrical", "126"), ("Electrical Engineering", "126"),
        ("ICE", "106"), ("Instrumentation", "106"), ("Instrumentation and Control Engineering", "106"),
        ("ME", "109"), ("Mechanical", "109"), ("Mechanical Engineering", "109"),
        ("CE", "102"), ("Civil", "102"), ("Civil Engineering", "102"),
        ("CHE", "112"), ("Chemical", "112"), ("Chemical Engineering", "112"),
        ("IPE", "113"), ("Industrial", "113"), ("Industrial and Production Engineering", "113"),
        ("BT", "111"), ("Biotechnology", "111"), ("Bio Technology", "111"),
        ("TT", "110"), ("Textile", "110"), ("Textile Technology", "110"),
        ("DSE", "117"), ("Data Science", "117"), ("Data Science and Engineering", "117"),
        ("VLSI", "118"), ("Electronics and VLSI", "118"),
        ("CY", "311"), ("Chemistry", "311"),
        ("MA", "312"), ("Mathematics", "312"),
        ("PH", "313"), ("Physics", "313"),
        ("MBA", "701"), ("Management", "701")
    ]
    for a, c in aliases:
        cur.execute("INSERT OR IGNORE INTO branch_aliases VALUES (?, ?)", (a.lower(), c))
        cur.execute("INSERT OR IGNORE INTO branch_aliases VALUES (?, ?)", (a, c))

    # Populate companies and aliases
    company_name_to_id = {}
    for canon_comp in sorted(list(set(COMPANY_NORMALIZER.values()))):
        cur.execute("INSERT OR IGNORE INTO companies (canonical_name) VALUES (?)", (canon_comp,))
        cur.execute("SELECT company_id FROM companies WHERE canonical_name = ?", (canon_comp,))
        cid = cur.fetchone()[0]
        company_name_to_id[canon_comp] = cid

    for raw_comp, canon_comp in COMPANY_NORMALIZER.items():
        cid = company_name_to_id[canon_comp]
        cur.execute("INSERT OR IGNORE INTO company_aliases VALUES (?, ?)", (raw_comp.lower().strip(), cid))
        cur.execute("INSERT OR IGNORE INTO company_aliases VALUES (?, ?)", (canon_comp.lower().strip(), cid))

    # Batches map
    # Year derivation:
    # 20 -> 2020-2024 (B.Tech), 2020-2022 (PG)
    # 21 -> 2021-2025 (B.Tech)
    # 22 -> 2022-2026 (B.Tech) / 2022-2024 (M.Tech/MSc/MBA)
    # 23 -> 2023-2027 (B.Tech) / 2023-2025 (M.Tech/MSc/MBA)
    # 24 -> 2024-2026 (PG)
    batch_defs = [
        ("2020-2024", 2020, 2024, "B.Tech"),
        ("2021-2025", 2021, 2025, "B.Tech"),
        ("2022-2026", 2022, 2026, "B.Tech"),
        ("2023-2027", 2023, 2027, "B.Tech"),
        ("2022-2024", 2022, 2024, "PG"),
        ("2023-2025", 2023, 2025, "PG"),
        ("2024-2026", 2024, 2026, "PG")
    ]
    for bid, a_yr, p_yr, deg in batch_defs:
        cur.execute("INSERT OR REPLACE INTO batches VALUES (?, ?, ?, ?)", (bid, a_yr, p_yr, deg))

    # Read and clean students and offers
    # We will prioritize File 2 M.Tech 2023-25 sheet over File 1 M.Tech 2023-25 sheet
    inserted_students = set()
    inserted_offers = 0
    skipped_dupe_offers = 0

    # Ordered files: process File 1 first, then File 2 (which updates/enriches M.Tech 2023-25), then File 3
    for f in files:
        fpath = os.path.join(DATA_DIR, f)
        wb = openpyxl.load_workbook(fpath, read_only=True, data_only=True)
        for sname in wb.sheetnames:
            s_low = sname.strip().lower()
            if s_low in SUMMARY_SHEETS:
                continue
            # If this is File 1 M.Tech 2023-25, skip it in favor of File 2 M.Tech 2023-25
            if "2020-24" in f and "m.tech 2023-25" in s_low:
                continue

            sheet = wb[sname]
            r_idx = 0
            h_row = None
            headers = {}
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

            is_textile_swapped = ("2020-24" in f and "textile" in s_low)

            for row in sheet.iter_rows(min_row=h_row + 1, values_only=True):
                r_idx += 1
                if not any(row):
                    continue
                first_few = [str(v or "").strip().lower() for v in row[:3]]
                if any("total" in v for v in first_few):
                    continue

                # Map columns
                row_map = {}
                for c_idx, h_name in headers.items():
                    val = row[c_idx] if c_idx < len(row) else None
                    row_map[h_name] = val

                # Find values
                roll_val = None
                branch_val = None
                gender_val = None
                cat_val = None
                comp_val = None
                pkg_val = None
                is_stipend_col = ("internship" in s_low or "2023-27" in s_low)
                date_val = None
                stat_val = None
                prof_val = None

                for k, v in row_map.items():
                    if "roll" in k and "no" in k:
                        roll_val = v
                    elif "branch" in k or "discipline" in k:
                        branch_val = v
                    elif "gender" in k or "sex" in k:
                        gender_val = v
                    elif "category" in k:
                        cat_val = v
                    elif "company" in k:
                        comp_val = v
                    elif "stipend" in k:
                        pkg_val = v
                        is_stipend_col = True
                    elif "package" in k or "ctc" in k:
                        pkg_val = v
                    elif "date" in k and date_val is None:
                        date_val = v
                    elif "status" in k or "fte" in k:
                        stat_val = v
                    elif "profile" in k:
                        prof_val = v

                # Handle swapped Textile columns (Col 6 was date header, col 7 was cat header, but values inverted)
                if is_textile_swapped:
                    # In row, date was in col 7 (idx 6) and cat was in col 6 (idx 5)
                    cat_val = row[5] if 5 < len(row) else cat_val
                    date_val = row[6] if 6 < len(row) else date_val

                # Clean roll
                clean_roll = str(roll_val).replace(".0", "").strip() if roll_val is not None else ""
                # Handle Santosh Kumar Palla
                if clean_roll == "2020 Batch" and "Santosh" in str(row_map.get("name", "")):
                    clean_roll = "20103104"

                if not clean_roll or len(clean_roll) < 5 or not clean_roll[:5].isdigit():
                    continue

                # Batch & Branch derivation from Roll No
                prefix_yr = clean_roll[:2]
                code = clean_roll[2:5]

                # Determine degree
                is_pg = (code in ["311", "312", "313", "701"] or code.startswith("2") or code.startswith("9"))
                if is_pg:
                    if prefix_yr == "22":
                        batch_id = "2022-2024"
                    elif prefix_yr == "23":
                        batch_id = "2023-2025"
                    elif prefix_yr == "24":
                        batch_id = "2024-2026"
                    else:
                        batch_id = f"20{prefix_yr}-20{int(prefix_yr)+2}"
                else:
                    if prefix_yr == "20":
                        batch_id = "2020-2024"
                    elif prefix_yr == "21":
                        batch_id = "2021-2025"
                    elif prefix_yr == "22":
                        batch_id = "2022-2026"
                    elif prefix_yr == "23":
                        batch_id = "2023-2027"
                    else:
                        batch_id = f"20{prefix_yr}-20{int(prefix_yr)+4}"

                # Derive canonical branch code
                canonical_bcode = code if code in BRANCH_MASTER else "103"
                is_conflict = 0
                if branch_val:
                    b_cell = str(branch_val).lower().replace("&", "and").replace(".", "").strip()
                    exp_b = BRANCH_MASTER[canonical_bcode]["name"].lower().replace("&", "and").replace(".", "").strip()
                    syns = {"cse": "computer science and engineering", "ice": "instrumentation and control engineering", "bio technology": "biotechnology"}
                    if syns.get(b_cell, b_cell) != syns.get(exp_b, exp_b):
                        is_conflict = 1

                # Normalize Gender
                clean_gender = str(gender_val).strip().upper() if gender_val else None
                if clean_gender in ["M", "MALE"]: clean_gender = "M"
                elif clean_gender in ["F", "FEMALE"]: clean_gender = "F"
                else: clean_gender = None

                # Normalize Category
                clean_cat = str(cat_val).strip() if cat_val else None
                if clean_cat:
                    if "gen-ews" in clean_cat.lower() or "ews" in clean_cat.lower(): clean_cat = "GEN-EWS"
                    elif "obc" in clean_cat.lower(): clean_cat = "OBC-NCL"
                    elif "sc" in clean_cat.lower(): clean_cat = "SC"
                    elif "st" in clean_cat.lower(): clean_cat = "ST"
                    elif "gen" in clean_cat.lower(): clean_cat = "General"

                # Insert Student
                if clean_roll not in inserted_students:
                    cur.execute("""
                    INSERT OR REPLACE INTO students 
                    (student_id, batch_id, branch_code, gender, category, source_branch_raw, is_branch_conflict)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (clean_roll, batch_id, canonical_bcode, clean_gender, clean_cat, str(branch_val or ""), is_conflict))
                    inserted_students.add(clean_roll)

                # Process Offer if company exists
                clean_comp = str(comp_val).strip() if comp_val else ""
                if clean_comp:
                    canon_comp = COMPANY_NORMALIZER.get(clean_comp, clean_comp)
                    cid = company_name_to_id.get(canon_comp)
                    if not cid:
                        cur.execute("INSERT OR IGNORE INTO companies (canonical_name) VALUES (?)", (canon_comp,))
                        cur.execute("SELECT company_id FROM companies WHERE canonical_name = ?", (canon_comp,))
                        cid = cur.fetchone()[0]
                        company_name_to_id[canon_comp] = cid

                    # Offer type & mode
                    off_type, off_mode = normalize_status(stat_val, str(date_val or ""))
                    
                    # Special check: if this sheet is an internship roster sheet (e.g. 3rd year or Summer internship),
                    # and status is Placed, tag as Intern / Summer Intern unless confirmed FTE
                    if any(term in s_low for term in ["internship", "summer intern"]) and off_type == "FTE":
                        off_type = "Intern"

                    # Package parsing
                    ctc_lpa, stipend_inr, raw_p, p_reason = parse_package(pkg_val, canon_comp, is_stipend_col=is_stipend_col)

                    # Date parsing
                    clean_date = normalize_date(date_val)

                    # Clean profile
                    clean_prof = str(prof_val).strip() if prof_val else None

                    try:
                        cur.execute("""
                        INSERT INTO offers 
                        (student_id, company_id, offer_type, ctc_lpa, stipend_monthly_inr, 
                         package_raw, package_reason, offer_date, offer_mode, profile, 
                         source_file, source_sheet, source_row)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (clean_roll, cid, off_type, ctc_lpa, stipend_inr, 
                              raw_p, p_reason, clean_date, off_mode, clean_prof,
                              f, sname, r_idx))
                        inserted_offers += 1
                    except sqlite3.IntegrityError:
                        # Duplicate offer row
                        skipped_dupe_offers += 1

        wb.close()

    # Create analytical views for SQL generation
    cur.executescript("""
    -- 1. Distinct placed students with at least 1 FTE or PPO offer
    CREATE VIEW v_placed_students AS
    SELECT DISTINCT
        s.student_id,
        s.batch_id,
        s.branch_code,
        b.canonical_name AS branch_name,
        b.short_name AS branch_short,
        b.degree,
        s.gender,
        s.category
    FROM students s
    JOIN branches b ON s.branch_code = b.branch_code
    JOIN offers o ON s.student_id = o.student_id
    WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');

    -- 2. Full-time and PPO job offers
    CREATE VIEW v_fte_ppo_offers AS
    SELECT 
        o.offer_id,
        s.student_id,
        s.batch_id,
        s.branch_code,
        b.canonical_name AS branch_name,
        b.short_name AS branch_short,
        b.degree,
        c.company_id,
        c.canonical_name AS company_name,
        c.sector,
        o.offer_type,
        o.ctc_lpa,
        o.offer_date,
        o.offer_mode,
        o.profile
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN branches b ON s.branch_code = b.branch_code
    JOIN companies c ON o.company_id = c.company_id
    WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');

    -- 3. Internship offers
    CREATE VIEW v_internship_offers AS
    SELECT 
        o.offer_id,
        s.student_id,
        s.batch_id,
        s.branch_code,
        b.canonical_name AS branch_name,
        b.short_name AS branch_short,
        b.degree,
        c.company_id,
        c.canonical_name AS company_name,
        o.offer_type,
        o.stipend_monthly_inr,
        o.offer_date,
        o.profile
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN branches b ON s.branch_code = b.branch_code
    JOIN companies c ON o.company_id = c.company_id
    WHERE o.offer_type IN ('Intern', 'Long Intern', 'Summer Intern');

    -- 4. Branch and Batch Placement Summary
    CREATE VIEW v_branch_year_stats AS
    SELECT
        b.canonical_name AS branch_name,
        b.short_name AS branch_short,
        s.batch_id,
        COUNT(DISTINCT s.student_id) AS total_students,
        COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) AS placed_students,
        COUNT(CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN o.offer_id END) AS total_offers,
        ROUND((COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) * 100.0) / COUNT(DISTINCT s.student_id), 2) AS placement_pct,
        ROUND(AVG(CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND o.ctc_lpa IS NOT NULL THEN o.ctc_lpa END), 2) AS avg_ctc_lpa,
        MAX(CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN o.ctc_lpa END) AS max_ctc_lpa
    FROM students s
    JOIN branches b ON s.branch_code = b.branch_code
    LEFT JOIN offers o ON s.student_id = o.student_id
    GROUP BY b.canonical_name, b.short_name, s.batch_id;
    """)

    conn.commit()

    # Query counts for validation
    cur.execute("SELECT COUNT(*) FROM students")
    total_db_students = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM offers")
    total_db_offers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM offers WHERE offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')")
    total_fte_offers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM offers WHERE ctc_lpa IS NOT NULL")
    offers_with_ctc = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM offers WHERE stipend_monthly_inr IS NOT NULL")
    offers_with_stipend = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM v_placed_students")
    total_placed_students = cur.fetchone()[0]

    conn.close()

    print("=== DATABASE BUILD COMPLETE ===")
    print(f"Total Unique Students Inserted: {total_db_students}")
    print(f"Total Deduplicated Offers: {total_db_offers}")
    print(f"FTE/PPO Offers: {total_fte_offers}")
    print(f"Offers with Verified CTC (LPA): {offers_with_ctc}")
    print(f"Offers with Stipend (INR/mo): {offers_with_stipend}")
    print(f"Distinct Placed Students (FTE/PPO): {total_placed_students}")
    print(f"Deduplicated Overlap Offers Skipped: {skipped_dupe_offers}")

if __name__ == "__main__":
    build_database()
