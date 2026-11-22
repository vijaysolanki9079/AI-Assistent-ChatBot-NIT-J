import sqlite3
import json
from collections import defaultdict

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()

# Get aliases per company
cur.execute("""
    SELECT c.canonical_name, ca.alias
    FROM company_aliases ca
    JOIN companies c ON ca.company_id = c.company_id
    ORDER BY c.canonical_name, ca.alias
""")
company_to_aliases = defaultdict(list)
alias_to_companies = defaultdict(list)
for cname, alias in cur.fetchall():
    company_to_aliases[cname].append(alias)
    alias_to_companies[alias.lower().strip()].append(cname)

# Find companies with >1 alias
multi_alias_companies = {c: a for c, a in company_to_aliases.items() if len(a) > 1}
# Find ambiguous aliases (mapped to >1 company)
ambiguous_aliases = {a: cs for a, cs in alias_to_companies.items() if len(set(cs)) > 1}

print(f"Total companies: {len(company_to_aliases)}")
print(f"Companies with >1 alias: {len(multi_alias_companies)}")
print(f"Ambiguous aliases: {len(ambiguous_aliases)}")

with open("reports/alias_merge_review.md", "w", encoding="utf-8") as f:
    f.write("# Company Alias Merge Review\n\n")
    f.write(f"- **Total Canonical Companies**: {len(company_to_aliases)}\n")
    f.write(f"- **Companies with Multiple Raw Names / Aliases**: {len(multi_alias_companies)}\n")
    f.write(f"- **Potentially Ambiguous Aliases**: {len(ambiguous_aliases)}\n\n")
    
    if ambiguous_aliases:
        f.write("## Ambiguous Aliases (Critical Review)\n\n")
        f.write("| Alias | Mapped Companies |\n")
        f.write("| :--- | :--- |\n")
        for a, cs in ambiguous_aliases.items():
            f.write(f"| `{a}` | {', '.join(set(cs))} |\n")
        f.write("\n")
    else:
        f.write("## Ambiguous Aliases\n\nNone. All aliases map deterministically to a single canonical company.\n\n")
        
    f.write("## Companies with Multiple Aliases / Raw Variants\n\n")
    f.write("| Canonical Company | Alias Count | Raw Variants / Aliases |\n")
    f.write("| :--- | :---: | :--- |\n")
    for c, aliases in sorted(multi_alias_companies.items(), key=lambda x: -len(x[1])):
        f.write(f"| **{c}** | {len(aliases)} | {', '.join(f'`{a}`' for a in aliases)} |\n")

print("Wrote reports/alias_merge_review.md")

