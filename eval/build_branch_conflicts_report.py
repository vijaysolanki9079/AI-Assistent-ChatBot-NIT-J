import json
from collections import Counter

with open("scripts/branch_conflicts.json", encoding="utf-8") as f:
    conflicts = json.load(f)

print(f"Total branch conflicts: {len(conflicts)}")

# Group by expected vs actual
pairs = Counter((c["expected_from_roll"], c["actual_in_cell"]) for c in conflicts)
files = Counter(c["file"] for c in conflicts)

with open("reports/branch_conflicts.md", "w", encoding="utf-8") as f:
    f.write("# Branch Conflicts Audit Report\n\n")
    f.write(f"- **Total Identified Branch Conflicts**: {len(conflicts)}\n")
    f.write("- **Resolution Rule**: In NIT Jalandhar's roll numbering system (`YYDDPSSS`), digits 3-5 represent the official admitting department code. When an Excel cell or sheet name lists a different department than the matriculated code (e.g. due to dual-branch recruitment drives or cross-departmental electives), the database flags `is_branch_conflict = 1` and grounds canonical reporting on the student's authoritative enrolled degree program.\n\n")
    
    f.write("## Conflict Distribution by Source File\n\n")
    f.write("| Source Workbook | Conflict Count |\n")
    f.write("| :--- | :---: |\n")
    for fname, cnt in files.most_common():
        f.write(f"| `{fname}` | {cnt} |\n")
    f.write("\n")
    
    f.write("## Top Discrepancy Pairs (Roll Derivation vs Sheet Cell)\n\n")
    f.write("| Official Branch (from Roll Code) | Sheet / Cell Discipline | Instances |\n")
    f.write("| :--- | :--- | :---: |\n")
    for (exp, act), cnt in pairs.most_common(20):
        f.write(f"| **{exp}** | {act} | {cnt} |\n")
    f.write("\n")
    
    f.write("## Sample Conflict Records\n\n")
    f.write("| Roll No | Student Name | Expected Branch | Sheet / Cell Branch | Company | File / Sheet |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
    for c in conflicts[:25]:
        f.write(f"| `{c['roll']}` | {c.get('name', 'N/A')} | **{c['expected_from_roll']}** | {c['actual_in_cell']} | {c.get('company', 'N/A')} | `{c['sheet']}` (row {c['row']}) |\n")

print("Wrote reports/branch_conflicts.md")

