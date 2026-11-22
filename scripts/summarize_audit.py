import json
from collections import Counter

with open('scripts/audit_output.json') as f:
    d = json.load(f)

print("=== TOTAL SUMMARY ===")
print(f"Total Rows: {d['total_rows']}")
print(f"Total Offer Rows: {d['total_offer_rows']}")
print(f"Total Unplaced / Roster Rows: {d['total_unplaced_rows']}")
print(f"Duplicate Offer Keys: {d['total_duplicate_keys']}")
print(f"Unusual Packages: {d['unusual_packages_count']}")
print(f"Shifted Date Rows: {d['shifted_date_examples_count']}")

print("\n=== PER FILE AND SHEET BREAKDOWN ===")
for fname, sheets in d['summary'].items():
    print(f"\n--- {fname} ---")
    for sname, s in sheets.items():
        print(f"  {sname:<35}: Total {s['rows']:<5} | Offers {s['offers']:<5} | Unplaced {s['unplaced']:<5}")

print("\n=== ALL BRANCH CODES (DIGITS 3-5 of Roll) ===")
for b_code, branches in sorted(d['branch_code_map'].items()):
    print(f"Code {b_code}: {dict(branches)}")

print("\n=== SAMPLE UNUSUAL PACKAGES ===")
for p in d['unusual_packages_sample'][:25]:
    print(f"  {p['sheet']} (row {p['row']}): {p['roll']} | {p['company']} -> {repr(p['pkg_raw'])}")

print("\n=== SAMPLE SHIFTED DATES ===")
for s in d['shifted_date_examples_sample'][:25]:
    print(f"  {s['sheet']} (row {s['row']}): {s['roll']} | Date: {repr(s['date_val'])} | Status: {repr(s['status_val'])} | Company: {s['company']}")

print("\n=== SAMPLE DUPLICATES ===")
for dupe in d['duplicate_examples_sample'][:10]:
    print(f"Key: {dupe['key']}")
    for occ in dupe['occurrences']:
        print(f"    File: {occ['file'][:25]} | Sheet: {occ['sheet']} (row {occ['row']}) | Pkg: {occ['pkg']} | Status: {occ['status']} | Date: {occ['date']}")

