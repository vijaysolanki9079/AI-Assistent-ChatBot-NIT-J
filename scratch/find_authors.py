import openpyxl

wb_21_25 = openpyxl.load_workbook(r"NIT-J data\2021-25 and 2023-25 Batch_Placement Database.xlsx", data_only=True)
wb_22_26 = openpyxl.load_workbook(r"NIT-J data\2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx", data_only=True)

def find_student(wb, name_sub):
    results = []
    for sheetname in wb.sheetnames:
        sheet = wb[sheetname]
        for r in range(1, sheet.max_row + 1):
            for c in range(1, 10):
                val = str(sheet.cell(r, c).value or '')
                if name_sub.lower() in val.lower():
                    row_vals = [sheet.cell(r, col).value for col in range(1, 12)]
                    results.append((sheetname, r, row_vals))
    return results

print("Searching for LOVKESH in 2021-25:")
for res in find_student(wb_21_25, "Lovkesh"):
    print(res)

print("\nSearching for SAMARTH in 2022-26:")
for res in find_student(wb_22_26, "Samarth"):
    print(res)

wb_21_25.close()
wb_22_26.close()

