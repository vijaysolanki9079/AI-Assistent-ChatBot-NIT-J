import openpyxl, os
from collections import defaultdict
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

all_offers = defaultdict(list)

for f in files:
    wb = openpyxl.load_workbook(os.path.join(DATA_DIR, f), read_only=True, data_only=True)
    for sname in wb.sheetnames:
        if sname.strip().lower() in SUMMARY_SHEETS:
            continue
        sheet = wb[sname]
        h_row = None
        roll_col = comp_col = pkg_col = date_col = stat_col = None
        r_idx = 0
        for row in sheet.iter_rows(values_only=True):
            r_idx += 1
            row_str = [str(v or "").strip().lower() for v in row]
            for c_idx, val in enumerate(row_str):
                if "roll" in val and "no" in val:
                    roll_col = c_idx
                    h_row = r_idx
                elif "company" in val:
                    comp_col = c_idx
                elif "package" in val or "stipend" in val or "ctc" in val:
                    pkg_col = c_idx
                elif "date" in val and date_col is None:
                    date_col = c_idx
                elif "status" in val or "fte" in val:
                    stat_col = c_idx
            if h_row and r_idx >= h_row:
                break
        if not h_row or roll_col is None or comp_col is None:
            continue
            
        for row in sheet.iter_rows(min_row=h_row + 1, values_only=True):
            r_idx += 1
            roll_val = row[roll_col] if roll_col < len(row) else None
            comp_val = row[comp_col] if comp_col < len(row) else None
            if not roll_val or not comp_val or not str(comp_val).strip():
                continue
            roll_str = str(roll_val).replace(".0", "").strip()
            comp_str = str(comp_val).strip()
            pkg_str = str(row[pkg_col]).strip() if pkg_col is not None and pkg_col < len(row) and row[pkg_col] is not None else None
            date_str = str(row[date_col]).strip() if date_col is not None and date_col < len(row) and row[date_col] is not None else None
            stat_str = str(row[stat_col]).strip() if stat_col is not None and stat_col < len(row) and row[stat_col] is not None else None
            
            all_offers[(roll_str, comp_str.lower())].append({
                "file": f, "sheet": sname, "row": r_idx,
                "roll": roll_str, "company": comp_str,
                "pkg": pkg_str, "date": date_str, "status": stat_str
            })
    wb.close()

exact_dupes = [] # same roll, same company, same date, same status
intern_plus_fte = [] # one is intern/summer intern, one is FTE/Placed
different_date_same_sheet = [] # multiple offers or updates

for (roll, comp), items in all_offers.items():
    if len(items) > 1:
        # check if they have same date and package and status
        sigs = [(x['file'], x['sheet'], x['pkg'], x['date'], x['status']) for x in items]
        if len(set(sigs)) == 1:
            exact_dupes.append({"roll": roll, "comp": comp, "items": items})
        else:
            # check if one is intern and other is placed/fte
            statuses = [str(x['status']).lower() for x in items]
            has_intern = any("intern" in s for s in statuses)
            has_fte = any("placed" in s or "fte" in s or "ppo" in s for s in statuses)
            if has_intern and has_fte:
                intern_plus_fte.append({"roll": roll, "comp": comp, "items": items})
            else:
                different_date_same_sheet.append({"roll": roll, "comp": comp, "items": items})

print(f"Total groups with >1 offer for same (roll, company): {len(all_offers) - sum(1 for v in all_offers.values() if len(v) == 1)}")
print(f"Exact duplicates (identical row copy): {len(exact_dupes)}")
print(f"Internship + FTE / PPO conversion pairs: {len(intern_plus_fte)}")
print(f"Other variations (different date/pkg/sheet): {len(different_date_same_sheet)}")

with open("scripts/duplicates_breakdown.json", "w") as out:
    json.dump({
        "exact_dupes": exact_dupes,
        "intern_plus_fte": intern_plus_fte,
        "other_variations": different_date_same_sheet
    }, out, indent=2)

print("\nSample Exact Duplicates:")
for d in exact_dupes[:5]:
    print(f"  Roll {d['roll']} | Company: {d['comp']} (Count {len(d['items'])})")
    for item in d['items']:
        print(f"    {item['file'][:20]} | {item['sheet']} r{item['row']} | Pkg: {item['pkg']} | Stat: {item['status']}")

print("\nSample Intern + FTE conversions:")
for d in intern_plus_fte[:5]:
    print(f"  Roll {d['roll']} | Company: {d['comp']}")
    for item in d['items']:
        print(f"    {item['sheet']} r{item['row']} | Pkg: {item['pkg']} | Stat: {item['status']} | Date: {item['date']}")

