import json
from collections import Counter

with open('scripts/audit_output.json') as f:
    d = json.load(f)

date_vals = Counter()
for item in d['shifted_date_examples_sample']:
    val = str(item['date_val']).strip()
    date_vals[val] += 1

print(f"Total shifted date rows sampled: {len(d['shifted_date_examples_sample'])}")
print("\nShifted Date Patterns:")
for val, count in date_vals.most_common(30):
    print(f"  {repr(val)}: {count}")

