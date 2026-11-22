import openpyxl

wb1 = openpyxl.load_workbook("NIT-J data/2021-25 and 2023-25 Batch_Placement Database.xlsx", read_only=True, data_only=True)
sheet1 = wb1["Computer Engg"]
r_idx = 0
print("=== File 2 Computer Engg Rows 5-12 ===")
for row in sheet1.iter_rows(min_row=5, max_row=12, values_only=True):
    r_idx += 1
    print(r_idx + 4, [str(v) if v is not None else "" for v in row][:10])
wb1.close()

wb2 = openpyxl.load_workbook("NIT-J data/2020-24 and 2022-24 Batch_Placement Database.xlsx", read_only=True, data_only=True)
sheet2 = wb2["Textile Technology"]
print("\n=== File 1 Textile Technology Rows 20-30 ===")
idx = 0
for row in sheet2.iter_rows(min_row=20, max_row=30, values_only=True):
    idx += 1
    print(idx + 19, [str(v) if v is not None else "" for v in row][:12])
wb2.close()
