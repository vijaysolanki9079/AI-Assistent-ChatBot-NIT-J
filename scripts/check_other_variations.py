import json

with open("scripts/duplicates_breakdown.json") as f:
    d = json.load(f)

print(f"Total other variations: {len(d['other_variations'])}")
for item in d['other_variations'][:20]:
    print(f"\nRoll: {item['roll']} | Company: {item['comp']}")
    for x in item['items']:
        print(f"  {x['file'][:25]} | {x['sheet']} r{x['row']} | Pkg: {x['pkg']} | Stat: {x['status']} | Date: {x['date']}")

