import os
import glob
import sqlite3
import pandas as pd

conn = sqlite3.connect('data/nitj_placement.db')
c = conn.cursor()

# 1. DB companies & branches
c.execute("SELECT canonical_name FROM companies")
db_companies = set(r[0].strip() for r in c.fetchall())

c.execute("SELECT alias FROM company_aliases")
db_aliases = set(r[0].strip().lower() for r in c.fetchall())

c.execute("SELECT short_name, canonical_name FROM branches")
db_branches = set()
for s, can in c.fetchall():
    db_branches.add(s.strip().lower())
    db_branches.add(can.strip().lower())

c.execute("SELECT COUNT(*) FROM offers")
db_offers_count = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM students")
db_students_count = c.fetchone()[0]

print(f"DB Companies: {len(db_companies)}, DB Offers: {db_offers_count}, DB Students: {db_students_count}")

# 2. Raw Excel companies, branches, rows
excel_files = glob.glob("NIT-J data/*.xlsx")
excel_companies = set()
excel_branches = set()
total_excel_rows = 0
sheet_breakdown = []

for fpath in sorted(excel_files):
    fname = os.path.basename(fpath)
    xl = pd.ExcelFile(fpath)
    file_rows = 0
    for sname in xl.sheet_names:
        # Ignore summary/metadata sheets if they don't have individual student rows
        df = xl.parse(sname)
        rows_in_sheet = len(df)
        
        # Look for company column
        comp_col = None
        for col in df.columns:
            if any(k in str(col).lower() for k in ['company', 'recruiter', 'employer', 'organisation', 'organization']):
                comp_col = col
                break
        
        branch_col = None
        for col in df.columns:
            if any(k in str(col).lower() for k in ['branch', 'discipline', 'department']):
                branch_col = col
                break
        
        comps_found = 0
        if comp_col:
            for val in df[comp_col].dropna():
                sval = str(val).strip()
                if sval and sval.lower() not in ['company', 'nan', 'total', 'nil', '-', 'none', 'na', 'n/a', 'select', 'placed']:
                    excel_companies.add(sval)
                    comps_found += 1
                    
        if branch_col:
            for val in df[branch_col].dropna():
                sval = str(val).strip()
                if sval and sval.lower() not in ['branch', 'nan', 'total', 'nil', '-', 'none', 'na', 'n/a']:
                    excel_branches.add(sval)

        sheet_breakdown.append({
            'file': fname,
            'sheet': sname,
            'rows': rows_in_sheet,
            'comp_col': str(comp_col),
            'comps_found': comps_found
        })
        file_rows += rows_in_sheet
    total_excel_rows += file_rows

print(f"\nTotal raw Excel rows across all sheets: {total_excel_rows}")
print(f"Total distinct company strings in Excel: {len(excel_companies)}")
print(f"Total distinct branch strings in Excel: {len(excel_branches)}")

# Compare Excel companies vs DB
excel_comps_normalized = {}
missing_in_db = []
matched_in_db = []

for comp in sorted(excel_companies):
    comp_clean = comp.strip().lower()
    # Check if exact match in canonical or in aliases
    if comp in db_companies or comp_clean in db_aliases:
        matched_in_db.append(comp)
    else:
        missing_in_db.append(comp)

print(f"\nMatched in DB: {len(matched_in_db)}")
print(f"Missing in DB (unmapped raw names): {len(missing_in_db)}")
print("Sample missing in DB:", missing_in_db[:30])

with open("eval/data_completeness_report.json", "w", encoding="utf-8") as f:
    import json
    json.dump({
        "db_companies_count": len(db_companies),
        "db_offers_count": db_offers_count,
        "db_students_count": db_students_count,
        "total_excel_rows": total_excel_rows,
        "excel_companies_count": len(excel_companies),
        "matched_count": len(matched_in_db),
        "missing_count": len(missing_in_db),
        "missing_companies": missing_in_db,
        "sheet_breakdown": sheet_breakdown
    }, f, indent=2)

print("\nData completeness check written to eval/data_completeness_report.json")

