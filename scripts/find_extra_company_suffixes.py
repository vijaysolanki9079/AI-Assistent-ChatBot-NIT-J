import json, re

with open("scripts/all_raw_companies.json") as f:
    comps = json.load(f)

print("=== Companies with University / Team / Campus / India ===")
for c in sorted(comps.keys()):
    low = c.lower()
    if any(k in low for k in ["university", "team", "campus", "hiring", "talent", "grad", "technolog"]):
        print(f"  {repr(c)}")

