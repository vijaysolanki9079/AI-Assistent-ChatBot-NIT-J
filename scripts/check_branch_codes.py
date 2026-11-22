import json

with open('scripts/audit_output.json') as f:
    d = json.load(f)

branch_map = d['branch_code_map']
print("=== BRANCH CODES AND ASSOCIATED BRANCH LABELS ===")
for code, branches in sorted(branch_map.items()):
    total = sum(branches.values())
    primary = max(branches.items(), key=lambda x: x[1])
    pct = (primary[1] / total) * 100
    print(f"Code {code} (Total {total} students): Primary '{primary[0]}' ({primary[1]} rows, {pct:.1f}%)")
    others = {k: v for k, v in branches.items() if k != primary[0]}
    if others:
        print(f"   Other labels: {others}")

