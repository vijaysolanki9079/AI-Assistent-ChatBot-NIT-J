import json

with open("scripts/data_quality_items.json") as f:
    items = json.load(f)

for x in items:
    if x['type'] == 'INVALID_ROLL_FORMAT':
        print("Invalid roll row:", x)
    if x['type'] == 'DATE_IN_PACKAGE_COLUMN':
        print("Date in package row:", x)

