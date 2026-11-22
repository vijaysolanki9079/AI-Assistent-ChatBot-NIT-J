import openpyxl, os, re
from collections import defaultdict, Counter
import json

DATA_DIR = "NIT-J data"
files = [
    "2020-24 and 2022-24 Batch_Placement Database.xlsx",
    "2021-25 and 2023-25 Batch_Placement Database.xlsx",
    "2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx"
]
SUMMARY_SHEETS = {
    "full details", "count wise details", "count", "copy of full details", "m.tech 23-25 full details"
}

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

def build_data_quality_report_data():
    report_items = []
    
    for f in files:
        wb = openpyxl.load_workbook(os.path.join(DATA_DIR, f), read_only=True, data_only=True)
        for sname in wb.sheetnames:
            if sname.strip().lower() in SUMMARY_SHEETS:
                continue
            sheet = wb[sname]
            
            # Find header
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
                            headers[c_idx] = str(val).strip().replace("\n", " ")
                    break
                    
            if not h_row:
                continue
                
            # Iterate data rows
            for row in sheet.iter_rows(min_row=h_row + 1, values_only=True):
                r_idx += 1
                if not any(row):
                    continue
                
                # Check for footer/total row
                first_few = [str(v or "").strip().lower() for v in row[:3]]
                if any("total" in v for v in first_few):
                    continue
                
                # Map columns
                row_dict = {}
                for c_idx, h_name in headers.items():
                    val = row[c_idx] if c_idx < len(row) else None
                    row_dict[h_name.lower()] = val
                
                # Find key values
                roll_val = None
                name_val = None
                branch_val = None
                comp_val = None
                pkg_val = None
                date_val = None
                stat_val = None
                
                for k, v in row_dict.items():
                    if "roll" in k and "no" in k:
                        roll_val = v
                    elif "name" in k and "company" not in k and "hr" not in k:
                        name_val = v
                    elif "branch" in k or "discipline" in k:
                        branch_val = v
                    elif "company" in k:
                        comp_val = v
                    elif "package" in k or "stipend" in k or "ctc" in k:
                        pkg_val = v
                    elif "date" in k and date_val is None:
                        date_val = v
                    elif "status" in k or "fte" in k:
                        stat_val = v
                
                # Check 1: Missing Roll No on data row
                if not roll_val or str(roll_val).strip() == "":
                    if comp_val or name_val:
                        report_items.append({
                            "file": f, "sheet": sname, "row": r_idx,
                            "type": "MISSING_ROLL_NUMBER",
                            "severity": "HIGH",
                            "details": f"Row has name='{name_val}', company='{comp_val}' but Roll No is empty."
                        })
                    continue
                    
                clean_roll = str(roll_val).replace(".0", "").strip()
                clean_comp = str(comp_val).strip() if comp_val else None
                clean_pkg = str(pkg_val).strip() if pkg_val is not None else None
                clean_date = str(date_val).strip() if date_val is not None else None
                clean_stat = str(stat_val).strip() if stat_val is not None else None
                clean_branch = str(branch_val).strip() if branch_val else None
                
                # Check 2: Invalid roll format
                if len(clean_roll) != 8 or not clean_roll.isdigit():
                    report_items.append({
                        "file": f, "sheet": sname, "row": r_idx,
                        "type": "INVALID_ROLL_FORMAT",
                        "severity": "MEDIUM",
                        "details": f"Roll number '{clean_roll}' has length {len(clean_roll)} (expected 8 digits)."
                    })
                
                # Check 3: If company is present (offer row)
                if clean_comp:
                    # Missing or non-numeric package
                    if clean_pkg is None or clean_pkg in ["", "-", "NULL", "None", "NA", "N.A", "Unpaid"]:
                        report_items.append({
                            "file": f, "sheet": sname, "row": r_idx,
                            "type": "MISSING_OR_UNPAID_PACKAGE",
                            "severity": "MEDIUM",
                            "details": f"Roll {clean_roll} placed at '{clean_comp}' has package='{clean_pkg}'."
                        })
                    elif clean_pkg in ["2023-12-18 00:00:00"]:
                        report_items.append({
                            "file": f, "sheet": sname, "row": r_idx,
                            "type": "DATE_IN_PACKAGE_COLUMN",
                            "severity": "HIGH",
                            "details": f"Roll {clean_roll} placed at '{clean_comp}' has date string '{clean_pkg}' in package column."
                        })
                    
                    # Missing status
                    if clean_stat is None or clean_stat in ["", "None"]:
                        report_items.append({
                            "file": f, "sheet": sname, "row": r_idx,
                            "type": "MISSING_OFFER_STATUS",
                            "severity": "LOW",
                            "details": f"Roll {clean_roll} placed at '{clean_comp}' has no status/offer-type specified."
                        })
                        
                    # Shifted date / category in date
                    if clean_date and clean_date.upper() in ["GENERAL", "OBC-NCL", "SC", "ST", "GEN-EWS", "GEN", "EWS", "OBC"]:
                        report_items.append({
                            "file": f, "sheet": sname, "row": r_idx,
                            "type": "CATEGORY_IN_DATE_COLUMN",
                            "severity": "HIGH",
                            "details": f"Roll {clean_roll} placed at '{clean_comp}' has category value '{clean_date}' in date column."
                        })
                    elif clean_date and any(k in clean_date.lower() for k in ["ppo", "offcampus", "intern", "placed"]):
                        report_items.append({
                            "file": f, "sheet": sname, "row": r_idx,
                            "type": "STATUS_IN_DATE_COLUMN",
                            "severity": "MEDIUM",
                            "details": f"Roll {clean_roll} placed at '{clean_comp}' has status/mode '{clean_date}' in date column."
                        })
                        
                    # Date typos
                    if clean_date and ("10.012.2024" in clean_date or "22.011.2024" in clean_date):
                        report_items.append({
                            "file": f, "sheet": sname, "row": r_idx,
                            "type": "DATE_TYPO",
                            "severity": "LOW",
                            "details": f"Roll {clean_roll} placed at '{clean_comp}' has typo date '{clean_date}'."
                        })
                        
                    # Branch code conflict
                    if len(clean_roll) == 8 and clean_roll[:5].isdigit():
                        code = clean_roll[2:5]
                        if code in UG_CODE_TO_CANONICAL:
                            exp_b = UG_CODE_TO_CANONICAL[code]
                            # compare with clean_branch
                            if clean_branch:
                                b_norm = clean_branch.lower().replace("&", "and").replace(".", "").strip()
                                exp_norm = exp_b.lower().replace("&", "and").replace(".", "").strip()
                                syns = {"cse": "computer science and engineering", "ice": "instrumentation and control engineering", "bio technology": "biotechnology"}
                                if syns.get(b_norm, b_norm) != syns.get(exp_norm, exp_norm):
                                    report_items.append({
                                        "file": f, "sheet": sname, "row": r_idx,
                                        "type": "BRANCH_CODE_CONFLICT",
                                        "severity": "MEDIUM",
                                        "details": f"Roll {clean_roll} (code {code} -> {exp_b}) is in '{clean_branch}' sheet/row placed at '{clean_comp}'."
                                    })
        wb.close()
        
    print(f"Total data quality report items: {len(report_items)}")
    counts_by_type = Counter([x["type"] for x in report_items])
    for t, c in counts_by_type.items():
        print(f"  {t}: {c}")
        
    with open("scripts/data_quality_items.json", "w") as out:
        json.dump(report_items, out, indent=2)

if __name__ == "__main__":
    build_data_quality_report_data()

