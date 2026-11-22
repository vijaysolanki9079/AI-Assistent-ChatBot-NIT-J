import openpyxl, os

files = [
    "2020-24 and 2022-24 Batch_Placement Database.xlsx",
    "2021-25 and 2023-25 Batch_Placement Database.xlsx",
    "2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx"
]

target_roll = "20109110"

for f in files:
    wb = openpyxl.load_workbook(os.path.join("NIT-J data", f), data_only=True)
    for sname in wb.sheetnames:
        sheet = wb[sname]
        for r in range(1, sheet.max_row + 1):
            row_vals = [str(sheet.cell(row=r, column=c).value or "") for c in range(1, sheet.max_column + 1)]
            for val in row_vals:
                if target_roll in val:
                    print(f"File {f[:25]} | Sheet {sname} row {r}:")
                    print("  ", [v for v in row_vals if v][:8])
                    break

