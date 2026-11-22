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

def analyze_all_columns():
    """
    Check column header vs column actual content per sheet.
    """
    column_audits = {}
    
    for f in files:
        fpath = os.path.join(DATA_DIR, f)
        wb = openpyxl.load_workbook(fpath, data_only=True)
        for sname in wb.sheetnames:
            if sname.strip().lower() in SUMMARY_SHEETS:
                continue
            sheet = wb[sname]
            
            # find header row
            h_row = None
            headers = {}
            for r in range(1, min(15, sheet.max_row + 1)):
                for c in range(1, sheet.max_column + 1):
                    val = str(sheet.cell(row=r, column=c).value or "").strip().lower()
                    if "roll" in val and "no" in val:
                        h_row = r
                        break
                if h_row:
                    for c in range(1, sheet.max_column + 1):
                        v = sheet.cell(row=h_row, column=c).value
                        if v is not None and str(v).strip():
                            headers[c] = str(v).strip().replace("\n", " ")
                    break
            
            # Sample first 20 rows of data to detect column contents
            col_samples = defaultdict(list)
            for r in range(h_row + 1, min(h_row + 30, sheet.max_row + 1)):
                for c, h in headers.items():
                    val = sheet.cell(row=r, column=c).value
                    if val is not None:
                        col_samples[c].append(str(val).strip())
            
            column_audits[f"{f} :: {sname}"] = {
                "header_row": h_row,
                "headers": headers,
                "sample_vals": {c: col_samples[c][:3] for c in headers}
            }
    
    with open("scripts/column_audits.json", "w") as out:
        json.dump(column_audits, out, indent=2)
    print("Column audits saved.")

if __name__ == "__main__":
    analyze_all_columns()

