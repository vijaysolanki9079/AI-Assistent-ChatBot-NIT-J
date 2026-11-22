import openpyxl, os

wb = openpyxl.load_workbook("NIT-J data/2020-24 and 2022-24 Batch_Placement Database.xlsx", read_only=True)
print("Sheets in 2020-24:", wb.sheetnames[:5])
for sname in ["CSE", "IT"]:
    sheet = wb[sname]
    for row in sheet.iter_rows(values_only=True):
        if row and any(row):
            print(f"{sname} header:", [str(c) for c in row if c is not None])
            break
wb.close()

