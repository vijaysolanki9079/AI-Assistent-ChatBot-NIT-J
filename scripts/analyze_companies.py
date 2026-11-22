import openpyxl, os, re
from collections import Counter, defaultdict
import json

DATA_DIR = "NIT-J data"
files = [
    "2020-24 and 2022-24 Batch_Placement Database.xlsx",
    "2021-25 and 2023-25 Batch_Placement Database.xlsx",
    "2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx"
]
SUMMARY_SHEETS = {
    "full details", "count wise details", "count", "copy of full details", "m.tech 23-25 full details"
}

company_counter = Counter()

for f in files:
    wb = openpyxl.load_workbook(os.path.join(DATA_DIR, f), read_only=True, data_only=True)
    for sname in wb.sheetnames:
        if sname.strip().lower() in SUMMARY_SHEETS:
            continue
        sheet = wb[sname]
        h_row = None
        comp_col = None
        r_idx = 0
        for row in sheet.iter_rows(values_only=True):
            r_idx += 1
            row_str = [str(v or "").strip().lower() for v in row]
            for c_idx, val in enumerate(row_str):
                if "company" in val:
                    comp_col = c_idx
                    h_row = r_idx
            if h_row and r_idx >= h_row:
                break
        if h_row is None or comp_col is None:
            continue
        for row in sheet.iter_rows(min_row=h_row + 1, values_only=True):
            if comp_col < len(row) and row[comp_col] is not None:
                cval = str(row[comp_col]).strip()
                if cval:
                    company_counter[cval] += 1
    wb.close()

print(f"Total distinct company names: {len(company_counter)}")

# Normalize and cluster
norm_to_raw = defaultdict(list)
for c, count in company_counter.items():
    clean = re.sub(r'[^a-zA-Z0-9]', '', c).lower()
    clean = clean.replace('limited', '').replace('ltd', '').replace('pvt', '').replace('private', '').replace('india', '')
    norm_to_raw[clean].append((c, count))

clusters = {k: v for k, v in norm_to_raw.items() if len(v) > 1}
print(f"Total clustered variants found: {len(clusters)}")

with open("scripts/company_clusters.json", "w") as out:
    json.dump({
        "total_distinct": len(company_counter),
        "top_companies": company_counter.most_common(30),
        "clusters": clusters
    }, out, indent=2)

print("\nSample Company Clusters:")
for k, v in list(clusters.items())[:20]:
    print(f"  Root '{k}': {v}")

