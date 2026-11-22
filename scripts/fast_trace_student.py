import openpyxl, os

files = [
    "2020-24 and 2022-24 Batch_Placement Database.xlsx",
    "2021-25 and 2023-25 Batch_Placement Database.xlsx",
    "2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx"
]

target_roll = "20109110"

for f in files:
    wb = openpyxl.load_workbook(os.path.join("NIT-J data", f), read_only=True, data_only=True)
    for sname in wb.sheetnames:
        sheet = wb[sname]
        r_idx = 0
        for row in sheet.iter_rows(values_only=True):
            r_idx += 1
            row_str = [str(v) if v is not None else "" for v in row]
            if any(target_roll in v for v in row_str):
                print(f"File: {f[:25]} | Sheet: {sname} row {r_idx}:")
                non_empty = [v for v in row_str if v]
                print("  ", non_empty[:10])
    wb.close()

