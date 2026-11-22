import openpyxl

for fname, bname in [
    ('NIT-J data/2020-24 and 2022-24 Batch_Placement Database.xlsx', '2020-2024'),
    ('NIT-J data/2021-25 and 2023-25 Batch_Placement Database.xlsx', '2021-2025'),
    ('NIT-J data/2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx', '2022-2026')
]:
    print(f"\n=================== {bname} Count Wise Details ===================")
    wb = openpyxl.load_workbook(fname, data_only=True)
    if 'Count Wise Details' in wb.sheetnames:
        ws = wb['Count Wise Details']
        for row in ws.iter_rows(values_only=True):
            if any(c is not None for c in row):
                print([c for c in row if c is not None][:8])

