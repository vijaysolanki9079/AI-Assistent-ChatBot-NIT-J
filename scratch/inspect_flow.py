import openpyxl

wb = openpyxl.load_workbook('NIT-J data/2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx', data_only=True)
for sname in wb.sheetnames:
    ws = wb[sname]
    for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        row_str = " ".join(str(c) for c in row if c is not None).lower()
        if "flow" in row_str or "116" in row_str:
            print(f"Found in sheet '{sname}' row {row_idx}:")
            print(row)

