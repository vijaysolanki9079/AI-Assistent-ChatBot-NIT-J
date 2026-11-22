import json
from collections import Counter

# Let's write a script that processes audit_output.json or directly checks all 194 shifted date rows
with open('scripts/audit_output.json') as f:
    d = json.load(f)

# Let's load the full audit results if we can inspect all shifted dates
print("Sample shifted date records:")
for item in d['shifted_date_examples_sample'][:30]:
    print(f"{item['file'][:20]} | {item['sheet']} r{item['row']} | Roll: {item['roll']} | Date: {repr(item['date_val'])} | Status: {repr(item['status_val'])} | Comp: {item['company']}")

