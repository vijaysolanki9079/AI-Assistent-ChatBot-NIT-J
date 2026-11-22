import openpyxl, os, re
from collections import Counter, defaultdict
import json

DATA_DIR = "NIT-J data"

files = [
    "2020-24 and 2022-24 Batch_Placement Database.xlsx",
    "2021-25 and 2023-25 Batch_Placement Database.xlsx",
    "2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx"
]

SUMMARY_SHEETS = {
    "full details", 
    "count wise details", 
    "count", 
    "copy of full details", 
    "m.tech 23-25 full details"
}

def scan_all_dates_and_columns():
    all_shifted = []
    typo_dates = []
    date_patterns = Counter()
    
    for f in files:
        wb = openpyxl.load_workbook(os.path.join(DATA_DIR, f), read_only=True, data_only=True)
        for sname in wb.sheetnames:
            if sname.strip().lower() in SUMMARY_SHEETS:
                continue
            sheet = wb[sname]
            
            # find header row and columns
            r_idx = 0
            h_row = None
            date_col = None
            roll_col = None
            cat_col = None
            status_col = None
            comp_col = None
            
            for row in sheet.iter_rows(values_only=True):
                r_idx += 1
                row_str = [str(v or "").strip().lower() for v in row]
                for c_idx, val in enumerate(row_str):
                    if "roll" in val and "no" in val:
                        roll_col = c_idx
                        h_row = r_idx
                    elif "date" in val:
                        # only take first date column or result date
                        if date_col is None or "result" in val:
                            date_col = c_idx
                    elif "category" in val:
                        cat_col = c_idx
                    elif "status" in val or "fte" in val:
                        status_col = c_idx
                    elif "company" in val:
                        comp_col = c_idx
                if h_row and r_idx >= h_row:
                    break
                    
            if h_row is None or date_col is None:
                continue
                
            # Iterate remaining rows
            for row in sheet.iter_rows(min_row=h_row + 1, values_only=True):
                r_idx += 1
                if not any(row):
                    continue
                roll_val = row[roll_col] if roll_col is not None and roll_col < len(row) else None
                if not roll_val:
                    continue
                roll_str = str(roll_val).replace(".0", "").strip()
                comp_val = str(row[comp_col]).strip() if comp_col is not None and comp_col < len(row) and row[comp_col] else ""
                date_val = str(row[date_col]).strip() if date_col < len(row) and row[date_col] is not None else ""
                cat_val = str(row[cat_col]).strip() if cat_col is not None and cat_col < len(row) and row[cat_col] is not None else ""
                stat_val = str(row[status_col]).strip() if status_col is not None and status_col < len(row) and row[status_col] is not None else ""
                
                if not comp_val:
                    # unplaced student
                    continue
                    
                if date_val:
                    # check if category value in date column
                    if date_val.upper() in ["GENERAL", "OBC-NCL", "SC", "ST", "GEN-EWS", "GEN", "EWS", "OBC"]:
                        all_shifted.append({
                            "type": "category_in_date_col",
                            "file": f, "sheet": sname, "row": r_idx, "roll": roll_str,
                            "date_cell": date_val, "cat_cell": cat_val, "status_cell": stat_val, "comp": comp_val
                        })
                    elif any(k in date_val.lower() for k in ["ppo", "offcampus", "intern", "placed"]):
                        all_shifted.append({
                            "type": "status_in_date_col",
                            "file": f, "sheet": sname, "row": r_idx, "roll": roll_str,
                            "date_cell": date_val, "cat_cell": cat_val, "status_cell": stat_val, "comp": comp_val
                        })
                    else:
                        # Check date format / typos
                        # e.g., "10.012.2024" or invalid dates
                        # match dd.mm.yyyy or dd-mm-yyyy or yyyy-mm-dd
                        match_dots = re.match(r"^(\d{1,2})\.(\d{1,4})\.(\d{2,4})", date_val)
                        if match_dots:
                            d, m, y = match_dots.groups()
                            if len(m) > 2 or int(m) > 12 or int(d) > 31:
                                typo_dates.append({
                                    "file": f, "sheet": sname, "row": r_idx, "roll": roll_str,
                                    "date_cell": date_val, "comp": comp_val
                                })
        wb.close()
        
    print(f"Total category-in-date rows: {sum(1 for s in all_shifted if s['type'] == 'category_in_date_col')}")
    print(f"Total status-in-date rows: {sum(1 for s in all_shifted if s['type'] == 'status_in_date_col')}")
    print(f"Total typo dates found: {len(typo_dates)}")
    
    with open("scripts/shifted_dates.json", "w") as out:
        json.dump({"shifted": all_shifted, "typos": typo_dates}, out, indent=2)
        
    print("\nSample typo dates:")
    for t in typo_dates[:10]:
        print(f"  {t['sheet']} r{t['row']} | Roll: {t['roll']} | Date: {repr(t['date_cell'])} | Comp: {t['comp']}")

    print("\nSample status-in-date rows:")
    for s in [x for x in all_shifted if x['type'] == 'status_in_date_col'][:10]:
        print(f"  {s['sheet']} r{s['row']} | Roll: {s['roll']} | Date cell: {repr(s['date_cell'])} | Status cell: {repr(s['status_cell'])}")

if __name__ == "__main__":
    scan_all_dates_and_columns()

