import openpyxl

wb1 = openpyxl.load_workbook('NIT-J data/2020-24 and 2022-24 Batch_Placement Database.xlsx', data_only=True)
ws1 = wb1['Computer Engg']
for i, r in enumerate(ws1.iter_rows(values_only=True)):
    if any(str(c).strip().lower() == 'roll no.' for c in r if c is not None):
        print("2020-24 Computer Engg Header:", [str(c).strip() for c in r if c is not None])
        for row in list(ws1.iter_rows(values_only=True))[i+1:i+4]:
            print("  sample row:", row[:12])
        break

wb2 = openpyxl.load_workbook('NIT-J data/2021-25 and 2023-25 Batch_Placement Database.xlsx', data_only=True)
ws2 = wb2['Computer Engg']
for i, r in enumerate(ws2.iter_rows(values_only=True)):
    if any(str(c).strip().lower() == 'roll no.' for c in r if c is not None):
        print("\n2021-25 Computer Engg Header:", [str(c).strip() for c in r if c is not None])
        for row in list(ws2.iter_rows(values_only=True))[i+1:i+4]:
            print("  sample row:", row[:12])
        break

wb3 = openpyxl.load_workbook('NIT-J data/2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx', data_only=True)
ws3 = wb3['B.Tech 2022-26']
for i, r in enumerate(ws3.iter_rows(values_only=True)):
    if any(str(c).strip().lower() == 'roll no.' for c in r if c is not None):
        print("\n2022-26 B.Tech Header:", [str(c).strip() for c in r if c is not None])
        for row in list(ws3.iter_rows(values_only=True))[i+1:i+4]:
            print("  sample row:", row[:12])
        break

