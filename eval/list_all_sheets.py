import openpyxl, os, json

DATA_DIR = "NIT-J data"
files = [
    "2020-24 and 2022-24 Batch_Placement Database.xlsx",
    "2021-25 and 2023-25 Batch_Placement Database.xlsx",
    "2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx"
]

for f in files:
    fpath = os.path.join(DATA_DIR, f)
    wb = openpyxl.load_workbook(fpath, read_only=True)
    print(f"=== {f} ===")
    for s in wb.sheetnames:
        print(f"  - {s}")

