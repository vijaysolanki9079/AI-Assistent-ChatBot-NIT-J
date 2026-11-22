import os
import openpyxl
from collections import defaultdict, Counter

DATA_DIR = "NIT-J data"

files = [
    "2020-24 and 2022-24 Batch_Placement Database.xlsx",
    "2021-25 and 2023-25 Batch_Placement Database.xlsx",
    "2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx"
]

def find_header_row(sheet):
    """Find the row index (1-based) containing 'roll no' (case-insensitive)."""
    for r in range(1, min(25, sheet.max_row + 1)):
        row_vals = [str(sheet.cell(row=r, column=c).value or "").strip().lower() for c in range(1, min(30, sheet.max_column + 1))]
        for c_idx, val in enumerate(row_vals):
            if "roll" in val and "no" in val:
                return r, row_vals
            # also check if "roll" alone is in val or "rollno"
            if val in ["roll no", "roll no.", "roll_no", "rollno", "roll #"]:
                return r, row_vals
    return None, None

def inspect_all():
    summary_sheet_names = {"full details", "count wise details", "count", "copy of full details", "m.tech 23-25 full details"}
    
    for f in files:
        path = os.path.join(DATA_DIR, f)
        print(f"\n{'='*60}\nFILE: {f}\n{'='*60}")
        wb = openpyxl.load_workbook(path, data_only=True)
        
        for sname in wb.sheetnames:
            is_summary = sname.strip().lower() in summary_sheet_names
            sheet = wb[sname]
            header_r, header_vals = find_header_row(sheet)
            print(f"\nSheet: '{sname}' | max_row: {sheet.max_row} | max_col: {sheet.max_column} | Summary: {is_summary}")
            if header_r:
                # get non-empty headers
                headers = []
                for c in range(1, sheet.max_column + 1):
                    val = sheet.cell(row=header_r, column=c).value
                    if val is not None and str(val).strip() != "":
                        headers.append((c, str(val).strip().replace("\n", " ")))
                print(f"  Header found at row {header_r}: {headers}")
                
                # Check sample 3 rows
                data_rows_count = 0
                sample_rows = []
                for r in range(header_r + 1, min(header_r + 20, sheet.max_row + 1)):
                    row_vals = [sheet.cell(row=r, column=c[0]).value for c in headers]
                    if any(v is not None and str(v).strip() != "" for v in row_vals):
                        data_rows_count += 1
                        if len(sample_rows) < 3:
                            sample_rows.append(row_vals)
                print(f"  Sample row 1: {sample_rows[0] if sample_rows else 'None'}")
            else:
                print(f"  NO 'Roll No' header found! First 3 rows:")
                for r in range(1, min(4, sheet.max_row + 1)):
                    row_vals = [sheet.cell(row=r, column=c).value for c in range(1, min(10, sheet.max_column + 1))]
                    print(f"    Row {r}: {row_vals}")

if __name__ == "__main__":
    inspect_all()

