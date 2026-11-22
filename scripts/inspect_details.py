import json
from collections import Counter

with open('scripts/audit_output.json') as f:
    d = json.load(f)

print("=== 10-DIGIT ROLL NO ===")
# Let's find any roll no with length != 8
import openpyxl, os
DATA_DIR = "NIT-J data"
for f in [
    "2020-24 and 2022-24 Batch_Placement Database.xlsx",
    "2021-25 and 2023-25 Batch_Placement Database.xlsx",
    "2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx"
]:
    wb = openpyxl.load_workbook(os.path.join(DATA_DIR, f), data_only=True)
    for sname in wb.sheetnames:
        sheet = wb[sname]
        for r in range(1, sheet.max_row + 1):
            for c in range(1, sheet.max_column + 1):
                val = sheet.cell(row=r, column=c).value
                if val is not None:
                    sval = str(val).replace(".0", "").strip()
                    if sval.isdigit() and len(sval) == 10:
                        print(f"Found 10-digit val: {sval} in {f} -> {sname} row {r} col {c}")

print("\n=== UNUSUAL PACKAGES (SAMPLE 40) ===")
pkg_types = Counter()
for item in d['unusual_packages_sample']:
    raw = str(item['pkg_raw']).strip()
    pkg_types[raw] += 1
    print(f"{item['sheet']} r{item['row']} | {item['roll']} | {item['company']} | pkg: {repr(item['pkg_raw'])}")

print("\n=== TOP UNUSUAL PACKAGE STRINGS ===")
for p, c in pkg_types.most_common(20):
    print(f"  {repr(p)}: {c}")

print("\n=== SHIFTED DATE EXAMPLES (SAMPLE 20) ===")
for item in d['shifted_date_examples_sample'][:20]:
    print(f"{item['sheet']} r{item['row']} | {item['roll']} | date: {repr(item['date_val'])} | status: {repr(item['status_val'])}")

