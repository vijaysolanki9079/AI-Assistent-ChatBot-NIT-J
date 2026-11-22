import openpyxl, os
from collections import Counter

files = {
    "File 1": "NIT-J data/2020-24 and 2022-24 Batch_Placement Database.xlsx",
    "File 2": "NIT-J data/2021-25 and 2023-25 Batch_Placement Database.xlsx",
    "File 3": "NIT-J data/2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx"
}

for fname, fpath in files.items():
    wb = openpyxl.load_workbook(fpath, read_only=True, data_only=True)
    print(f"\n=== {fname}: {os.path.basename(fpath)} ===")
    for sname in wb.sheetnames:
        if any(term in sname.lower() for term in ["intern", "summer", "3rd year"]):
            sheet = wb[sname]
            batches = Counter()
            offers = 0
            total = 0
            r_idx = 0
            for row in sheet.iter_rows(values_only=True):
                r_idx += 1
                if r_idx < 2: continue
                # find roll
                row_str = [str(v or "").replace(".0", "").strip() for v in row]
                rolls = [v for v in row_str if len(v) == 8 and v.isdigit()]
                if rolls:
                    r = rolls[0]
                    total += 1
                    batches[r[:2]] += 1
                    # check if company
                    # in internship sheets, company is usually col 9 or 10
                    has_comp = any(c for c in row_str[7:11] if c and not any(k in c.lower() for k in ["intern", "placed", "male", "female", "general", "sc", "st", "obc"]))
                    if has_comp:
                        offers += 1
            print(f"  Sheet '{sname}': Total {total} students, Batches: {dict(batches)}")
    wb.close()

