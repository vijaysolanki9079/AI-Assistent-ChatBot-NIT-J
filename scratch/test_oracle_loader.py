import openpyxl
import pandas as pd
import re

BRANCH_MAP = {
    'computer': 'CSE', 'cse': 'CSE', 'information': 'IT', 'it': 'IT',
    'electronics': 'ECE', 'ece': 'ECE', 'electrical': 'EE', 'ee': 'EE',
    'mechanical': 'ME', 'me': 'ME', 'civil': 'CE', 'ce': 'CE',
    'chemical': 'CHE', 'che': 'CHE', 'industrial': 'IPE', 'ipe': 'IPE',
    'instrumentation': 'ICE', 'ice': 'ICE', 'biotechnology': 'BT', 'bt': 'BT',
    'textile': 'TT', 'tt': 'TT'
}

def clean_branch(val):
    if not val:
        return None
    s = str(val).lower().strip()
    for k, v in BRANCH_MAP.items():
        if k in s:
            return v
    return s.upper()

def clean_ctc(val):
    if val is None or val == '' or pd.isna(val):
        return None
    s = str(val).strip().replace(',', '')
    # Check crore e.g. 1.16 Crore
    if 'crore' in s.lower() or 'cr' in s.lower():
        m = re.search(r'(\d+(?:\.\d+)?)', s)
        if m:
            return round(float(m.group(1)) * 100.0, 2)
    # Check LPA e.g. 52 LPA, 52
    m = re.search(r'(\d+(?:\.\d+)?)', s)
    if m:
        v = float(m.group(1))
        # If unreasonably high (e.g. stipend in rupees like 50000 or annual 360000)
        if v > 10000:
            return round(v / 100000.0, 2)
        return v
    return None

records = []

# Workbook 1: 2020-2024
wb1 = openpyxl.load_workbook('NIT-J data/2020-24 and 2022-24 Batch_Placement Database.xlsx', data_only=True)
for sname in wb1.sheetnames:
    if sname in ['Biotechnology', 'Chemical Engg', 'Civil Engg', 'Computer Engg', 'Electrical Engg', 'Electronics Engg', 'Industrial Engg', 'Instrumentation Engg', 'Mechanical Engg', 'Information Technology', 'Textile Technology']:
        ws = wb1[sname]
        headers = []
        for r_idx, row in enumerate(ws.iter_rows(values_only=True)):
            row_vals = [str(c).strip() if c is not None else '' for c in row]
            if any('roll' in c.lower() for c in row_vals):
                headers = [c.lower() for c in row_vals]
                header_idx = r_idx
                break
        if not headers:
            continue
        
        roll_col = next((i for i, h in enumerate(headers) if 'roll' in h), None)
        name_col = next((i for i, h in enumerate(headers) if 'name' in h), None)
        comp_col = next((i for i, h in enumerate(headers) if 'company' in h), None)
        pkg_col = next((i for i, h in enumerate(headers) if 'package' in h or 'ctc' in h), None)
        
        for row in list(ws.iter_rows(values_only=True))[header_idx+1:]:
            if not row or not any(row):
                continue
            roll = str(row[roll_col]).strip() if roll_col is not None and row[roll_col] is not None else None
            comp = str(row[comp_col]).strip() if comp_col is not None and row[comp_col] is not None else None
            pkg = clean_ctc(row[pkg_col]) if pkg_col is not None else None
            
            if comp and comp.lower() not in ['not placed', 'unplaced', 'opted out', 'higher studies', 'none', '-', '']:
                records.append({
                    'batch': '2020-2024',
                    'branch': clean_branch(sname),
                    'roll_number': roll,
                    'company': comp,
                    'ctc_lpa': pkg
                })

print(f"Loaded 2020-2024 records: {len(records)}")

