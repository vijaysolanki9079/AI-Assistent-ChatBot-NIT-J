import openpyxl

wb = openpyxl.load_workbook(r"NIT-J data\2021-25 and 2023-25 Batch_Placement Database.xlsx", data_only=True)
sheet = wb["Computer Engg"]

print("Headers (Row 1 to 3):")
for r in range(1, 4):
    row_vals = [sheet.cell(r, c).value for c in range(1, 15)]
    print(f"Row {r}: {row_vals}")

print("\nRows 36 to 41 (IndiaMART rows):")
for r in range(35, 42):
    row_vals = [sheet.cell(r, c).value for c in range(1, 15)]
    print(f"Row {r}: {row_vals}")

wb.close()

