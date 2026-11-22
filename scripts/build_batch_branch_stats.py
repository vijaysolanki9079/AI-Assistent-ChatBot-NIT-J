import os
import re
import sqlite3
import openpyxl

DB_PATH = "data/nitj_placement.db"
DATA_DIR = "NIT-J data"

def clean_key(s):
    if not s:
        return ""
    return re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9&]', ' ', str(s)).strip().lower())

# Canonical branch mapping for disciplines in Count Wise Details sheets
RAW_UG = {
    "ece": "104",
    "electronics & communication": "104",
    "electronics & communication engg": "104",
    "electronics & communicationg": "104",
    "ee": "126",
    "electrical": "126",
    "electrical engg": "126",
    "cse": "103",
    "computer science": "103",
    "computer sceince & engg": "103",
    "computer science & engineering": "103",
    "it": "124",
    "information technology": "124",
    "che": "112",
    "chemical": "112",
    "chemical engg": "112",
    "chemical engineering": "112",
    "ice": "106",
    "instrumentation & control": "106",
    "instrumentation & control engineering": "106",
    "instrumention & control engineering": "106",
    "civil": "102",
    "civil engg": "102",
    "civil engineering": "102",
    "ipe": "113",
    "industrial & production engg": "113",
    "industrial engg": "113",
    "industrial engineering": "113",
    "me": "109",
    "mechanical": "109",
    "mechanical engg": "109",
    "mechanical engineering": "109",
    "bt": "111",
    "biotechnology": "111",
    "tt": "110",
    "textile technology": "110",
    "total": "TOTAL",
}
DISCIPLINE_MAP_UG = {clean_key(k): v for k, v in RAW_UG.items()}

RAW_PG = {
    "ece": "204",
    "vlsi": "204",
    "vlsi design": "204",
    "ai": "201",
    "artifical intelligence": "201",
    "artificial intelligence": "201",
    "cse": "203",
    "computer science & engineering": "203",
    "is": "203",
    "information security": "203",
    "che": "112",
    "chemical": "112",
    "chemical engineering": "112",
    "ice": "206",
    "instrumention & control engineering": "206",
    "instrumentation & control engineering": "206",
    "civil": "202",
    "sce": "202",
    "structural and construction engg": "202",
    "structural and construction engineering": "202",
    "geo tech": "202",
    "geo tech and environmental engg": "202",
    "geotechnical and geo environmental engineering": "202",
    "me": "209",
    "thermal": "209",
    "thermal and energy engineering": "209",
    "design engineering": "209",
    "desing engineering": "209",
    "ev&d": "126",
    "electrical vehicle design": "126",
    "renewable": "126",
    "renewable energy": "126",
    "bt": "111",
    "biotechnology": "111",
    "tt": "210",
    "tt&m": "210",
    "textile engineering and management": "210",
    "textile engineering and managment engg": "210",
    "textile engineering and management engg": "210",
    "da": "205",
    "data analytics": "205",
    "ds&e": "117",
    "data science & engineering": "117",
    "data science and engineering": "117",
    "ie&da": "205",
    "industrial engineering & data anaytics": "205",
    "industrial engineering and data analytics": "205",
    "spml": "204",
    "signal processing and machine learning": "204",
    "mathematics computing": "312",
    "mathematics and computing": "312",
    "mia": "201",
    "machine intelligence and automation": "201",
    "mba": "701",
    "msc": "311",
    "total": "TOTAL",
}
DISCIPLINE_MAP_PG = {clean_key(k): v for k, v in RAW_PG.items()}

def clean_val(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in ["-", "null", "none", "na", "n.a."]:
        return None
    return s

def parse_num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(',', '')
    if "crore" in s.lower() or "cr" in s.lower():
        m = re.search(r'[-+]?\d*\.?\d+', s)
        if m:
            return float(m.group(0)) * 100.0
    m = re.search(r'[-+]?\d*\.?\d+', s)
    if m:
        try:
            return float(m.group(0))
        except ValueError:
            return None
    return None

def normalize_disc(name, is_pg=False):
    if not name:
        return None
    ck = clean_key(name)
    if is_pg:
        return DISCIPLINE_MAP_PG.get(ck, DISCIPLINE_MAP_UG.get(ck))
    return DISCIPLINE_MAP_UG.get(ck)

def build_stats():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS batch_branch_stats (
        batch_id TEXT,
        branch_code TEXT,
        discipline_raw TEXT,
        degree TEXT,
        total_students INTEGER,
        eligible_students INTEGER,
        placed_students INTEGER,
        job_offers INTEGER,
        double_job_offers INTEGER,
        max_ctc REAL,
        top_recruiter TEXT,
        avg_ctc REAL,
        placement_pct REAL,
        male_placed INTEGER,
        female_placed INTEGER,
        source_sheet TEXT,
        PRIMARY KEY (batch_id, branch_code)
    )
    """)
    cur.execute("DELETE FROM batch_branch_stats")
    
    records = []

    # 1. 2020-2024
    path_2020 = os.path.join(DATA_DIR, "2020-24 and 2022-24 Batch_Placement Database.xlsx")
    wb_2020 = openpyxl.load_workbook(path_2020, data_only=True)
    ws_2020 = wb_2020["Count Wise Details"]
    
    # UG: Rows 3 to 14
    for r in range(3, 15):
        disc = ws_2020.cell(r, 1).value
        if not disc:
            continue
        b_code = normalize_disc(disc, is_pg=False)
        if not b_code:
            continue
        tot = parse_num(ws_2020.cell(r, 2).value)
        elig = parse_num(ws_2020.cell(r, 3).value)
        offers = parse_num(ws_2020.cell(r, 5).value)
        double_offers = parse_num(ws_2020.cell(r, 6).value)
        placed = parse_num(ws_2020.cell(r, 7).value)
        max_c = parse_num(ws_2020.cell(r, 8).value)
        recruiter = clean_val(ws_2020.cell(r, 9).value)
        avg_c = parse_num(ws_2020.cell(r, 10).value)
        pct = parse_num(ws_2020.cell(r, 11).value)
        m_placed = parse_num(ws_2020.cell(r, 12).value)
        f_placed = parse_num(ws_2020.cell(r, 13).value)
        
        records.append((
            "2020-2024", b_code, str(disc).strip(), "B.Tech",
            int(tot) if tot is not None else None,
            int(elig) if elig is not None else None,
            int(placed) if placed is not None else None,
            int(offers) if offers is not None else None,
            int(double_offers) if double_offers is not None else None,
            max_c, recruiter, avg_c, round(pct, 2) if pct is not None else None,
            int(m_placed) if m_placed is not None else None,
            int(f_placed) if f_placed is not None else None,
            "2020-24 Count Wise Details"
        ))

    # PG 2022-24 M.Tech: Rows 20 to 32
    for r in range(20, 33):
        disc = ws_2020.cell(r, 1).value
        if not disc:
            continue
        b_code = normalize_disc(disc, is_pg=True)
        if not b_code:
            continue
        elig = parse_num(ws_2020.cell(r, 3).value)
        offers = parse_num(ws_2020.cell(r, 5).value)
        double_offers = parse_num(ws_2020.cell(r, 6).value)
        placed = parse_num(ws_2020.cell(r, 7).value)
        max_c = parse_num(ws_2020.cell(r, 8).value)
        recruiter = clean_val(ws_2020.cell(r, 9).value)
        avg_c = parse_num(ws_2020.cell(r, 10).value)
        pct = parse_num(ws_2020.cell(r, 11).value)
        m_placed = parse_num(ws_2020.cell(r, 12).value)
        f_placed = parse_num(ws_2020.cell(r, 13).value)
        
        records.append((
            "2022-2024", b_code, str(disc).strip(), "M.Tech",
            int(elig) if elig is not None else None,
            int(elig) if elig is not None else None,
            int(placed) if placed is not None else None,
            int(offers) if offers is not None else None,
            int(double_offers) if double_offers is not None else None,
            max_c, recruiter, avg_c, round(pct, 2) if pct is not None else None,
            int(m_placed) if m_placed is not None else None,
            int(f_placed) if f_placed is not None else None,
            "2022-24 M.Tech Count Wise Details"
        ))

    # 2. 2021-2025
    path_2021 = os.path.join(DATA_DIR, "2021-25 and 2023-25 Batch_Placement Database.xlsx")
    wb_2021 = openpyxl.load_workbook(path_2021, data_only=True)
    ws_2021 = wb_2021["Count Wise Details"]
    
    # UG: Rows 3 to 14
    for r in range(3, 15):
        disc = ws_2021.cell(r, 1).value
        if not disc:
            continue
        b_code = normalize_disc(disc, is_pg=False)
        if not b_code:
            continue
        tot = parse_num(ws_2021.cell(r, 2).value)
        elig = parse_num(ws_2021.cell(r, 3).value)
        offers = parse_num(ws_2021.cell(r, 5).value)
        double_offers = parse_num(ws_2021.cell(r, 6).value)
        placed = parse_num(ws_2021.cell(r, 7).value)
        max_c = parse_num(ws_2021.cell(r, 9).value)
        recruiter = clean_val(ws_2021.cell(r, 10).value)
        avg_c = parse_num(ws_2021.cell(r, 11).value)
        pct = parse_num(ws_2021.cell(r, 12).value)
        
        records.append((
            "2021-2025", b_code, str(disc).strip(), "B.Tech",
            int(tot) if tot is not None else None,
            int(elig) if elig is not None else None,
            int(placed) if placed is not None else None,
            int(offers) if offers is not None else None,
            int(double_offers) if double_offers is not None else None,
            max_c, recruiter, avg_c, round(pct, 2) if pct is not None else None,
            None, None,
            "2021-25 Count Wise Details"
        ))

    # PG 2023-25: Rows 19 to 36
    for r in range(19, 37):
        disc = ws_2021.cell(r, 1).value
        if not disc:
            continue
        b_code = normalize_disc(disc, is_pg=True)
        if not b_code:
            continue
        tot = parse_num(ws_2021.cell(r, 2).value)
        elig = parse_num(ws_2021.cell(r, 3).value)
        offers = parse_num(ws_2021.cell(r, 5).value)
        double_offers = parse_num(ws_2021.cell(r, 6).value)
        placed = parse_num(ws_2021.cell(r, 7).value)
        max_c = parse_num(ws_2021.cell(r, 9).value)
        recruiter = clean_val(ws_2021.cell(r, 10).value)
        avg_c = parse_num(ws_2021.cell(r, 11).value)
        pct = parse_num(ws_2021.cell(r, 12).value)
        
        records.append((
            "2023-2025", b_code, str(disc).strip(), "PG",
            int(tot) if tot is not None else None,
            int(elig) if elig is not None else None,
            int(placed) if placed is not None else None,
            int(offers) if offers is not None else None,
            int(double_offers) if double_offers is not None else None,
            max_c, recruiter, avg_c, round(pct, 2) if pct is not None else None,
            None, None,
            "2023-25 PG Count Wise Details"
        ))

    # 3. 2022-2026
    path_2022 = os.path.join(DATA_DIR, "2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx")
    wb_2022 = openpyxl.load_workbook(path_2022, data_only=True)
    ws_2022 = wb_2022["Count Wise Details"]
    
    # UG: Rows 3 to 14
    for r in range(3, 15):
        disc = ws_2022.cell(r, 1).value
        if not disc:
            continue
        b_code = normalize_disc(disc, is_pg=False)
        if not b_code:
            continue
        tot = parse_num(ws_2022.cell(r, 2).value)
        elig = parse_num(ws_2022.cell(r, 3).value)
        offers = parse_num(ws_2022.cell(r, 4).value)
        double_offers = parse_num(ws_2022.cell(r, 5).value)
        placed = parse_num(ws_2022.cell(r, 6).value)
        max_c = parse_num(ws_2022.cell(r, 7).value)
        recruiter = clean_val(ws_2022.cell(r, 8).value)
        avg_c = parse_num(ws_2022.cell(r, 9).value)
        pct = parse_num(ws_2022.cell(r, 10).value)
        m_placed = parse_num(ws_2022.cell(r, 11).value)
        f_placed = parse_num(ws_2022.cell(r, 12).value)
        
        records.append((
            "2022-2026", b_code, str(disc).strip(), "B.Tech",
            int(tot) if tot is not None else None,
            int(elig) if elig is not None else None,
            int(placed) if placed is not None else None,
            int(offers) if offers is not None else None,
            int(double_offers) if double_offers is not None else None,
            max_c, recruiter, avg_c, round(pct, 2) if pct is not None else None,
            int(m_placed) if m_placed is not None else None,
            int(f_placed) if f_placed is not None else None,
            "2022-26 Count Wise Details"
        ))

    # PG 2024-26: Rows 19 to 40
    for r in range(19, 41):
        disc = ws_2022.cell(r, 1).value
        if not disc:
            continue
        b_code = normalize_disc(disc, is_pg=True)
        if not b_code:
            continue
        tot = parse_num(ws_2022.cell(r, 2).value)
        elig = parse_num(ws_2022.cell(r, 3).value)
        offers = parse_num(ws_2022.cell(r, 4).value)
        double_offers = parse_num(ws_2022.cell(r, 5).value)
        placed = parse_num(ws_2022.cell(r, 6).value)
        max_c = parse_num(ws_2022.cell(r, 7).value)
        recruiter = clean_val(ws_2022.cell(r, 8).value)
        avg_c = parse_num(ws_2022.cell(r, 9).value)
        pct = parse_num(ws_2022.cell(r, 10).value)
        
        records.append((
            "2024-2026", b_code, str(disc).strip(), "PG",
            int(tot) if tot is not None else None,
            int(elig) if elig is not None else None,
            int(placed) if placed is not None else None,
            int(offers) if offers is not None else None,
            int(double_offers) if double_offers is not None else None,
            max_c, recruiter, avg_c, round(pct, 2) if pct is not None else None,
            None, None,
            "2024-26 PG Count Wise Details"
        ))

    cur.executemany("""
    INSERT OR REPLACE INTO batch_branch_stats (
        batch_id, branch_code, discipline_raw, degree, total_students, eligible_students,
        placed_students, job_offers, double_job_offers, max_ctc, top_recruiter,
        avg_ctc, placement_pct, male_placed, female_placed, source_sheet
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, records)
    
    conn.commit()
    print(f"Successfully loaded {len(records)} records into batch_branch_stats.")
    
    # Check counts per batch
    cur.execute("SELECT batch_id, degree, COUNT(*) FROM batch_branch_stats GROUP BY batch_id, degree")
    for row in cur.fetchall():
        print("Batch count:", row)
        
    conn.close()

if __name__ == "__main__":
    build_stats()
