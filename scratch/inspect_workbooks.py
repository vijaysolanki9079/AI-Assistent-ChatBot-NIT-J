import openpyxl

files = [
    'NIT-J data/2020-24 and 2022-24 Batch_Placement Database.xlsx',
    'NIT-J data/2021-25 and 2023-25 Batch_Placement Database.xlsx',
    'NIT-J data/2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx'
]

for f in files:
    print(f"\n=================== {f} ===================")
    wb = openpyxl.load_workbook(f, read_only=True)
    print("Sheets:", wb.sheetnames)
    for sname in wb.sheetnames:
        if any(k in sname.lower() for k in ["b.tech", "full", "count", "detail", "computer", "information"]):
            ws = wb[sname]
            for row in ws.iter_rows(values_only=True):
                if row and any(c is not None for c in row):
                    non_empty = [str(c) for c in row if c is not None]
                    if len(non_empty) >= 4:
                        print(f"[{sname} header/first row]: {non_empty[:8]}")
                        break

