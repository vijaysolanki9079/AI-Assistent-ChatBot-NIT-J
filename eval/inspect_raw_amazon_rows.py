import openpyxl

wb = openpyxl.load_workbook("NIT-J data/2021-25 and 2023-25 Batch_Placement Database.xlsx", data_only=True)
ws = wb["Computer Engg"]

for r in [107, 111, 128, 170]:
    row = [cell.value for cell in ws[r]]
    print(f"Row {r}: {row}")

