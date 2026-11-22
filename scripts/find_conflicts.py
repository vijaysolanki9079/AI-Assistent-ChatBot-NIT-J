import os
import openpyxl
from collections import defaultdict
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

# Canonical mapping for UG branch codes
UG_CODE_TO_CANONICAL = {
    "102": "Civil Engineering",
    "103": "Computer Science and Engineering",
    "104": "Electronics and Communication Engineering",
    "106": "Instrumentation and Control Engineering",
    "109": "Mechanical Engineering",
    "110": "Textile Technology",
    "111": "Biotechnology",
    "112": "Chemical Engineering",
    "113": "Industrial and Production Engineering",
    "117": "Data Science and Engineering",
    "118": "Electronics and VLSI Engineering",
    "124": "Information Technology",
    "126": "Electrical Engineering",
    "311": "Chemistry",
    "312": "Mathematics",
    "313": "Physics",
    "701": "MBA"
}

def check_all_conflicts():
    conflicts = []
    
    for f in files:
        wb = openpyxl.load_workbook(os.path.join(DATA_DIR, f), data_only=True)
        for sname in wb.sheetnames:
            if sname.strip().lower() in SUMMARY_SHEETS:
                continue
            sheet = wb[sname]
            
            # find header row
            h_row = None
            roll_col = None
            branch_col = None
            name_col = None
            comp_col = None
            
            for r in range(1, min(15, sheet.max_row + 1)):
                for c in range(1, sheet.max_column + 1):
                    val = str(sheet.cell(row=r, column=c).value or "").strip().lower()
                    if "roll" in val and "no" in val:
                        roll_col = c
                        h_row = r
                    elif "branch" in val or "discipline" in val:
                        branch_col = c
                    elif "name" in val and "company" not in val and "hr" not in val:
                        name_col = c
                    elif "company" in val:
                        comp_col = c
                if h_row and roll_col:
                    break
                    
            if not h_row or not roll_col:
                continue
                
            for r in range(h_row + 1, sheet.max_row + 1):
                roll_val = sheet.cell(row=r, column=roll_col).value
                if not roll_val:
                    continue
                roll_str = str(roll_val).replace(".0", "").strip()
                if len(roll_str) >= 5 and roll_str[:5].isdigit():
                    code = roll_str[2:5]
                    if code in UG_CODE_TO_CANONICAL:
                        expected = UG_CODE_TO_CANONICAL[code]
                        actual = str(sheet.cell(row=r, column=branch_col).value or "").strip() if branch_col else ""
                        name = str(sheet.cell(row=r, column=name_col).value or "").strip() if name_col else ""
                        comp = str(sheet.cell(row=r, column=comp_col).value or "").strip() if comp_col else ""
                        
                        # normalize actual
                        norm_act = actual.lower().replace("&", "and").replace(".", "").strip()
                        norm_exp = expected.lower().replace("&", "and").replace(".", "").strip()
                        
                        # Handle known synonyms
                        synonyms = {
                            "cse": "computer science and engineering",
                            "ice": "instrumentation and control engineering",
                            "bio technology": "biotechnology",
                            "biotechnology": "biotechnology"
                        }
                        mapped_act = synonyms.get(norm_act, norm_act)
                        mapped_exp = synonyms.get(norm_exp, norm_exp)
                        
                        if mapped_act and mapped_act != mapped_exp:
                            conflicts.append({
                                "file": f, "sheet": sname, "row": r,
                                "roll": roll_str, "name": name,
                                "code": code, "expected_from_roll": expected,
                                "actual_in_cell": actual, "company": comp
                            })
                            
    print(f"Total branch conflicts found: {len(conflicts)}")
    with open("scripts/branch_conflicts.json", "w") as out:
        json.dump(conflicts, out, indent=2)
        
    print("\nSample conflicts (first 15):")
    for c in conflicts[:15]:
        print(f"  {c['sheet']} r{c['row']} | Roll: {c['roll']} | Code {c['code']} -> Exp: {c['expected_from_roll']} | Cell: {c['actual_in_cell']} | Comp: {c['company']}")

if __name__ == "__main__":
    check_all_conflicts()
