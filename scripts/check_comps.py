import json
from collections import Counter
import re

with open('scripts/audit_output.json') as f:
    d = json.load(f)

raw_comps = list(d['summary'].keys()) # wait, let's get companies from audit_output
# in deep_audit.py, company_raw_values was a counter, but let's check what was saved
with open('scripts/audit_output.json') as f:
    d = json.load(f)

# Let's inspect companies
print("Checking companies...")

