import openpyxl, os

wb = openpyxl.load_workbook("NIT-J data/2020-24 and 2022-24 Batch_Placement Database.xlsx", data_only=True)

# Check Mechanical Engg sheet
sheet = wb["Mechanical Engg"]
for r in range(2, sheet.max_row + 1):
    roll = str(sheet.cell(row=r, column=2).value or "").replace(".0", "").strip()
    branch = str(sheet.cell(row=r, column=4).value or "").strip()
    name = str(sheet.cell(row=r, column=3).value or "").strip()
    if roll.startswith("20102"):
        print(f"Mechanical Engg sheet row {r}: Roll {roll}, Name: {name}, Branch cell: '{branch}'")

# Check where 20102 students appear
print("\nWhere do 20102 students appear across sheets?")
for sname in wb.sheetnames:
    s = wb[sname]
    for r in range(2, min(50, s.max_row + 1)):
        roll = str(s.cell(row=r, column=2).value or "").replace(".0", "").strip()
        if roll.startswith("20102"):
            b = str(s.cell(row=r, column=4).value or "").strip()
            print(f"  {sname} r{r}: {roll} | {b}")
            break

