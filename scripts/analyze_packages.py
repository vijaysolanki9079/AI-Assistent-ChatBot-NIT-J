import os
import openpyxl
from collections import Counter
import re

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

def analyze_packages():
    raw_packages = Counter()
    package_details = []
    
    for f in files:
        wb = openpyxl.load_workbook(os.path.join(DATA_DIR, f), data_only=True)
        for sname in wb.sheetnames:
            if sname.strip().lower() in SUMMARY_SHEETS:
                continue
            sheet = wb[sname]
            
            # find header
            h_row = None
            pkg_col = None
            comp_col = None
            roll_col = None
            status_col = None
            
            for r in range(1, min(15, sheet.max_row + 1)):
                for c in range(1, sheet.max_column + 1):
                    val = str(sheet.cell(row=r, column=c).value or "").strip().lower()
                    if "roll" in val and "no" in val:
                        roll_col = c
                        h_row = r
                    elif "package" in val or "stipend" in val or "ctc" in val:
                        pkg_col = c
                    elif "company" in val:
                        comp_col = c
                    elif "status" in val or "fte" in val:
                        status_col = c
                if h_row and pkg_col and comp_col:
                    break
                    
            if not h_row or not pkg_col or not comp_col:
                continue
                
            for r in range(h_row + 1, sheet.max_row + 1):
                comp_val = sheet.cell(row=r, column=comp_col).value
                if not comp_val or not str(comp_val).strip():
                    continue
                
                pkg_val = sheet.cell(row=r, column=pkg_col).value
                roll_val = sheet.cell(row=r, column=roll_col).value if roll_col else None
                status_val = sheet.cell(row=r, column=status_col).value if status_col else None
                
                clean_p = str(pkg_val).strip() if pkg_val is not None else "NULL"
                raw_packages[clean_p] += 1
                
                # Check if it fails float parsing
                # try stripping LPA, lpa, Lpa
                test_str = re.sub(r'(?i)\s*lpa', '', clean_p).strip()
                try:
                    float(test_str)
                except ValueError:
                    package_details.append({
                        "file": f, "sheet": sname, "row": r,
                        "roll": str(roll_val).replace(".0", "") if roll_val else None,
                        "company": str(comp_val).strip(),
                        "status": str(status_val).strip() if status_val else None,
                        "pkg_raw": clean_p
                    })
                    
    print(f"Total distinct raw package strings: {len(raw_packages)}")
    print(f"Total non-float package entries: {len(package_details)}")
    
    non_float_counter = Counter([p["pkg_raw"] for p in package_details])
    print("\nAll Non-Float Package Patterns & Counts:")
    for p, count in sorted(non_float_counter.items(), key=lambda x: x[1], reverse=True):
        print(f"  {repr(p)}: {count}")
        
    return package_details

if __name__ == "__main__":
    analyze_packages()

