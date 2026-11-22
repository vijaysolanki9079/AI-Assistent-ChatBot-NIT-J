import openpyxl

wb = openpyxl.load_workbook("NIT-J data/2020-24 and 2022-24 Batch_Placement Database.xlsx", data_only=True)
sheet = wb["Textile Technology"]
print("Textile Technology headers:")
for c in range(1, 12):
    print(c, sheet.cell(row=1, column=c).value)

print("\nTextile Technology rows 2-5:")
for r in range(2, 6):
    print([sheet.cell(row=r, column=c).value for c in range(1, 12)])

