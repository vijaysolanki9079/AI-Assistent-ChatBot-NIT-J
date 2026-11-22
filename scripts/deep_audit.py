import os
import re
import openpyxl
from collections import defaultdict, Counter
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

def clean_str(val):
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None

def normalize_header(h):
    h = h.lower().replace(".", "").replace("_", " ").replace("\n", " ").strip()
    if "roll" in h and "no" in h:
        return "roll_no"
    if h in ["srno", "sno", "s no", "sr no", "fnav"]:
        return "s_no"
    if "branch" in h or "discipline" in h:
        return "branch"
    if "name" in h and "company" not in h and "hr" not in h:
        return "name"
    if "gender" in h or "sex" in h:
        return "gender"
    if "category" in h:
        return "category"
    if "pwd" in h:
        return "pwd"
    if "date" in h:
        return "date"
    if "profile" in h:
        return "profile"
    if "company" in h:
        return "company"
    if "package" in h or "ctc" in h:
        return "package"
    if "stipend" in h:
        return "stipend"
    if "status" in h or "fte" in h or "intern" in h:
        return "status"
    return h

def run_deep_audit():
    audit_results = {
        "summary": {},
        "branch_names": Counter(),
        "status_values": Counter(),
        "package_raw_values": Counter(),
        "date_raw_values": Counter(),
        "company_raw_values": Counter(),
        "roll_no_formats": Counter(),
        "branch_code_map": defaultdict(Counter),
        "branch_conflict_examples": [],
        "shifted_date_examples": [],
        "unusual_packages": [],
        "duplicates": [],
        "unparsable_rows": []
    }
    
    total_rows = 0
    total_offer_rows = 0
    total_unplaced_rows = 0
    
    all_offers_for_dupe_check = defaultdict(list)
    
    for f in files:
        fpath = os.path.join(DATA_DIR, f)
        wb = openpyxl.load_workbook(fpath, data_only=True)
        file_stats = {}
        
        for sname in wb.sheetnames:
            sname_clean = sname.strip().lower()
            if sname_clean in SUMMARY_SHEETS:
                continue
                
            sheet = wb[sname]
            
            # Find header row
            header_row_idx = None
            header_map = {} # col_idx -> canonical_name
            
            for r in range(1, min(20, sheet.max_row + 1)):
                r_vals = [sheet.cell(row=r, column=c).value for c in range(1, min(30, sheet.max_column + 1))]
                for c_idx, val in enumerate(r_vals, 1):
                    val_str = str(val or "").strip().lower()
                    if ("roll" in val_str and "no" in val_str) or val_str in ["roll no", "roll no.", "roll_no"]:
                        header_row_idx = r
                        break
                if header_row_idx:
                    # map headers
                    for c in range(1, sheet.max_column + 1):
                        cell_val = sheet.cell(row=r, column=c).value
                        if cell_val is not None and str(cell_val).strip():
                            norm_h = normalize_header(str(cell_val))
                            header_map[c] = norm_h
                    break
            
            if not header_row_idx:
                audit_results["unparsable_rows"].append({
                    "file": f,
                    "sheet": sname,
                    "row": 0,
                    "reason": "No header row with Roll No found"
                })
                continue
                
            sheet_rows = 0
            sheet_offers = 0
            sheet_unplaced = 0
            
            for r in range(header_row_idx + 1, sheet.max_row + 1):
                row_data = {}
                for c, h in header_map.items():
                    row_data[h] = sheet.cell(row=r, column=c).value
                
                # Check if entire row is empty
                if not any(v is not None and str(v).strip() != "" for v in row_data.values()):
                    continue
                
                raw_roll = row_data.get("roll_no")
                clean_roll = clean_str(raw_roll)
                
                # Check if this is a footer or total row
                first_few_vals = [str(v or "").strip().lower() for v in list(row_data.values())[:3]]
                if any("total" in v for v in first_few_vals):
                    continue
                
                if not clean_roll:
                    # Is there a company or name?
                    if row_data.get("company") or row_data.get("name"):
                        audit_results["unparsable_rows"].append({
                            "file": f,
                            "sheet": sname,
                            "row": r,
                            "reason": f"Missing Roll No but row has data: name={row_data.get('name')}, company={row_data.get('company')}"
                        })
                    continue
                
                # Clean roll number (handle float from Excel, e.g., 20111006.0 -> "20111006")
                if isinstance(raw_roll, float):
                    roll_str = str(int(raw_roll))
                else:
                    # strip trailing .0 if present
                    roll_str = str(clean_roll).replace(".0", "").strip()
                
                audit_results["roll_no_formats"][len(roll_str)] += 1
                
                sheet_rows += 1
                total_rows += 1
                
                # Extract branch
                raw_branch = clean_str(row_data.get("branch"))
                if raw_branch:
                    audit_results["branch_names"][raw_branch] += 1
                
                # Branch code vs roll number
                # Roll no convention: e.g. 20111006 -> batch=20, code=111
                if len(roll_str) >= 5 and roll_str[:2].isdigit() and roll_str[2:5].isdigit():
                    b_code = roll_str[2:5]
                    audit_results["branch_code_map"][b_code][raw_branch or "MISSING"] += 1
                
                # Company & offer check
                raw_company = clean_str(row_data.get("company"))
                raw_pkg = clean_str(row_data.get("package")) if "package" in row_data else clean_str(row_data.get("stipend"))
                raw_status = clean_str(row_data.get("status"))
                raw_date = row_data.get("date")
                
                # Date checks & shifted columns
                date_str = clean_str(raw_date)
                if date_str:
                    audit_results["date_raw_values"][str(date_str)[:30]] += 1
                    # check if status / category shifted into date
                    lower_d = date_str.lower()
                    if any(term in lower_d for term in ["ppo", "offcampus", "intern", "placed", "obc", "sc", "st", "gen"]):
                        audit_results["shifted_date_examples"].append({
                            "file": f, "sheet": sname, "row": r, "roll": roll_str,
                            "date_val": date_str, "status_val": raw_status, "company": raw_company
                        })
                
                if raw_company:
                    sheet_offers += 1
                    total_offer_rows += 1
                    audit_results["company_raw_values"][raw_company] += 1
                    
                    if raw_status:
                        audit_results["status_values"][raw_status] += 1
                    else:
                        audit_results["status_values"]["MISSING_STATUS"] += 1
                    
                    if raw_pkg is not None:
                        audit_results["package_raw_values"][raw_pkg] += 1
                        # Check for non-numeric packages
                        pkg_clean_num = str(raw_pkg).replace("LPA", "").replace("lpa", "").replace("Lpa", "").strip()
                        try:
                            float(pkg_clean_num)
                        except ValueError:
                            audit_results["unusual_packages"].append({
                                "file": f, "sheet": sname, "row": r, "roll": roll_str,
                                "company": raw_company, "pkg_raw": raw_pkg
                            })
                    else:
                        audit_results["package_raw_values"]["MISSING_PACKAGE"] += 1
                    
                    # Track for duplicates
                    offer_key = (roll_str, raw_company.lower().strip())
                    all_offers_for_dupe_check[offer_key].append({
                        "file": f, "sheet": sname, "row": r,
                        "roll": roll_str, "company": raw_company,
                        "pkg": raw_pkg, "status": raw_status, "date": date_str
                    })
                else:
                    sheet_unplaced += 1
                    total_unplaced_rows += 1
            
            file_stats[sname] = {
                "rows": sheet_rows,
                "offers": sheet_offers,
                "unplaced": sheet_unplaced
            }
        
        audit_results["summary"][f] = file_stats

    # Check duplicates
    dupe_count = 0
    for key, items in all_offers_for_dupe_check.items():
        if len(items) > 1:
            dupe_count += 1
            audit_results["duplicates"].append({
                "key": key,
                "count": len(items),
                "occurrences": items
            })
            
    audit_results["total_rows"] = total_rows
    audit_results["total_offer_rows"] = total_offer_rows
    audit_results["total_unplaced_rows"] = total_unplaced_rows
    audit_results["total_duplicate_keys"] = dupe_count
    
    # Write audit summary to JSON for inspection
    with open("scripts/audit_output.json", "w") as out:
        # Convert counter/defaultdict to regular dict
        serializable = {
            "total_rows": total_rows,
            "total_offer_rows": total_offer_rows,
            "total_unplaced_rows": total_unplaced_rows,
            "total_duplicate_keys": dupe_count,
            "summary": audit_results["summary"],
            "roll_no_formats": dict(audit_results["roll_no_formats"]),
            "branch_names_count": len(audit_results["branch_names"]),
            "branch_names": dict(audit_results["branch_names"]),
            "status_values_count": len(audit_results["status_values"]),
            "status_values": dict(audit_results["status_values"]),
            "company_raw_values_count": len(audit_results["company_raw_values"]),
            "branch_code_map": {k: dict(v) for k, v in audit_results["branch_code_map"].items()},
            "unusual_packages_count": len(audit_results["unusual_packages"]),
            "unusual_packages_sample": audit_results["unusual_packages"][:50],
            "shifted_date_examples_count": len(audit_results["shifted_date_examples"]),
            "shifted_date_examples_sample": audit_results["shifted_date_examples"][:50],
            "unparsable_rows_count": len(audit_results["unparsable_rows"]),
            "unparsable_rows": audit_results["unparsable_rows"],
            "duplicate_examples_sample": audit_results["duplicates"][:25]
        }
        json.dump(serializable, out, indent=2)
        
    print(f"Deep Audit complete!")
    print(f"Total student rows: {total_rows}")
    print(f"Total offer rows: {total_offer_rows}")
    print(f"Total unplaced/internship roster rows: {total_unplaced_rows}")
    print(f"Duplicate offer keys (roll, company): {dupe_count}")
    print(f"Unique branch strings: {len(audit_results['branch_names'])}")
    print(f"Unique status strings: {len(audit_results['status_values'])}")
    print(f"Unique company strings: {len(audit_results['company_raw_values'])}")
    print(f"Unusual package values: {len(audit_results['unusual_packages'])}")
    print(f"Shifted date examples: {len(audit_results['shifted_date_examples'])}")
    print(f"Unparsable rows: {len(audit_results['unparsable_rows'])}")

if __name__ == "__main__":
    run_deep_audit()

