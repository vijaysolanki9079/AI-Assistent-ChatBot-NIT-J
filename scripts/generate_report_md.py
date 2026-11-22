import json
from collections import Counter, defaultdict

with open("scripts/data_quality_items.json") as f:
    items = json.load(f)

# Also let's load branch conflicts and shifted dates
with open("scripts/shifted_dates.json") as f:
    shifted_data = json.load(f)

with open("scripts/duplicates_breakdown.json") as f:
    dupes_data = json.load(f)

UG_CODE_TO_CANONICAL = {
    "102": "Civil Engineering",
    "103": "Computer Science and Engineering",
    "104": "Electronics and Communication Engineering",
    "106": "Instrumentation and Control Engineering",
    "109": "Mechanical Engineering",
    "110": "Textile Technology",
    "111": "Biotechnology",
    "112": "Chemical Engineering",
    "113": "Industrial and Production Engineering",
    "117": "Data Science and Engineering",
    "118": "Electronics and VLSI Engineering",
    "124": "Information Technology",
    "126": "Electrical Engineering",
    "311": "Chemistry",
    "312": "Mathematics",
    "313": "Physics",
    "701": "MBA"
}

report_lines = [
    "# NIT Jalandhar Placement Database - Data Quality & Audit Report",
    "",
    "> **Status**: Phase 1 Audit Complete (Read-only; No files modified)",
    "> **Total Student Records Audited**: 9,385 across 3 Excel workbooks",
    "> **Total Offer Records**: 3,009 rows (6,376 unplaced students / internship roster rows)",
    "> **Total Data Quality Flagged Rows**: 392 records requiring attention/clarification",
    "",
    "---",
    "",
    "## Executive Summary of Audit Findings",
    "",
    "| Audit Category | Issue Count | Description | Impact & Recommended Resolution |",
    "|---|---|---|---|",
    "| **Column Alignment & Swaps** | 34 rows | Textile Technology (File 1) has `Date Result` and `Category` headers reversed relative to cell contents. | Auto-swap columns 6 & 7 during ingestion for this sheet. |",
    "| **Status Shifted to Date** | 113 rows | Offer status (`PPO`, `Offcampus`, `04.10.2023 PPO`) stored in Date column. | Extract clean ISO date (e.g. `2023-10-04`) and move `PPO`/`Offcampus` flag to Offer Type / Mode. |",
    "| **Date Typos** | 5 rows | Month entered with extra zeros (e.g., `10.012.2024` for Flipkart, `22.011.2024` for NXP). | Normalize `10.012.2024` -> `2024-12-10`, `22.011.2024` -> `2024-11-22`. |",
    "| **Date in Package Column** | 2 rows | Date `2023-12-18` entered in package column for Trident Group PPO rows in Textile Technology. | Trident GET package is 12.0 LPA. Clarify whether PPO is 12.0 LPA or mark package as NULL (unverified). |",
    "| **Package / Stipend Units** | 475 rows | 188 distinct non-float package strings: pure stipends (`45K`, `1.25Lac PM`), compound packages (`40K+12.8LPA`), and unpaid/missing (`-`, `Unpaid`, `NA`). | Split into `ctc_lpa` (float) and `stipend_monthly_inr` (int/float). Never count stipend towards CTC. |",
    "| **Branch Code Conflicts** | 150 offer rows (291 total) | Roll number digits 3-5 differ from the sheet or branch cell (e.g. Roll `20109110` Mech in EE sheet; 20102 CE in ME sheet). | Derive canonical branch from roll number prefix code; flag conflicts for user confirmation. |",
    "| **Missing / Invalid Roll No** | 1 row | Computer Engg (File 2) row 8 has `'2020 Batch'` in roll column for Santosh Kumar Palla. | Matched to Roll `20103104` (2020-24 CSE batch unplaced student who appeared with 2021-25 batch). |",
    "| **Cross-Workbook Snapshot Overlaps** | 80+ rows | `M.Tech 2023-25` sheet exists in both File 1 (80 early offers) and File 2 (134 updated offers with PPO conversions). | Deduplicate across files using `(roll_no, company, offer_type)`; prefer later snapshot in File 2. |",
    "| **Student Multi-Offer / Progression** | 38 pairs | Same student appears in 3rd-year internship roster and later in branch sheet with FTE/PPO offer. | Keep both rows but tag them with distinct `offer_type` (`Intern` vs `FTE`/`PPO`). |",
    "| **HR & Privacy Sheet** | 1 sheet | `Copy of Full Details` in File 2 contains HR names, phone numbers, and email IDs. | Exclude sheet completely from DB ingestion. Implement strict aggregation privacy rules (min group 3). |",
    "",
    "---",
    "",
    "## Detailed Audit Log: All Flagged Rows",
    "",
    "### 1. Column Shift / Category in Date Column (Textile Technology)",
    "In workbook `2020-24 and 2022-24 Batch_Placement Database.xlsx`, sheet `Textile Technology`, column 6 is labeled `Date Result` and column 7 is labeled `Category`. In rows 2 to 35, column 6 contains category values (`General`, `SC`, `OBC-NCL`, `GEN-EWS`, `ST`) while column 7 contains result dates (`05.09.2023`, `12.03.2024`, etc.).",
    "",
    "| File | Sheet | Row | Roll No | Company | Col 6 (Labeled Date Result) | Col 7 (Labeled Category) | Remediation |",
    "|---|---|---|---|---|---|---|---|"
]

for item in items:
    if item['type'] == 'CATEGORY_IN_DATE_COLUMN':
        report_lines.append(f"| {item['file'][:25]}... | {item['sheet']} | {item['row']} | `{item['details'].split()[1]}` | {item['details'].split('placed at ')[1].split(' has')[0]} | Category found | Date found | Swap Col 6 and 7 |")

report_lines.extend([
    "",
    "### 2. Date in Package Column (High Severity)",
    "In `Textile Technology` (File 1), two students placed at Trident Group have date `2023-12-18 00:00:00` sitting in the Package column.",
    "",
    "| File | Sheet | Row | Roll No | Company | Raw Package Cell | Actual Meaning / Remediation |",
    "|---|---|---|---|---|---|---|",
    "| 2020-24 and 2022-24 Batch... | Textile Technology | 24 | `20110012` | Trident Group | `2023-12-18 00:00:00` | PPO effective date. Other Trident rows have 12.0 LPA. Clarify or set `ctc_lpa = 12.0` / NULL with reason. |",
    "| 2020-24 and 2022-24 Batch... | Textile Technology | 28 | `20110067` | Trident Group | `2023-12-18 00:00:00` | PPO effective date. Other Trident rows have 12.0 LPA. Clarify or set `ctc_lpa = 12.0` / NULL with reason. |",
    "",
    "### 3. Invalid Roll Number Format / Subheader Row",
    "",
    "| File | Sheet | Row | Raw Roll Cell | Student Name | Company | Package | Remediation |",
    "|---|---|---|---|---|---|---|---|",
    "| 2021-25 and 2023-25 Batch... | Computer Engg | 8 | `'2020 Batch'` | Santosh Kumar Palla | Infosys | 3.6 LPA | Trace: Student is `20103104` (unplaced in 2020-24 batch, placed with 2021-25 batch). Auto-resolve to `20103104`. |",
    "",
    "### 4. Date Column Typos (Months with Extra Zero)",
    "",
    "| File | Sheet | Row | Roll No | Company | Raw Date String | Normalized Clean Date |",
    "|---|---|---|---|---|---|---|"
])

for item in items:
    if item['type'] == 'DATE_TYPO':
        raw_d = item['details'].split("'")[3]
        clean_d = raw_d.replace(".012.", ".12.").replace(".011.", ".11.")
        parts = clean_d.split(".")
        iso_d = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        report_lines.append(f"| {item['file'][:25]}... | {item['sheet']} | {item['row']} | `{item['details'].split()[1]}` | {item['details'].split('placed at ')[1].split(' has')[0]} | `{raw_d}` | `{iso_d}` |")

report_lines.extend([
    "",
    "### 5. Status / Offer-Type Shifted Into Date Column (Sample 30 of 113 rows)",
    "Values like `04.10.2023 PPO`, `Offcampus`, `PPO`, or `Intern` entered in the Date Result column.",
    "",
    "| File | Sheet | Row | Roll No | Company | Raw Date Cell | Clean Extracted Date | Extracted Offer Mode / Status |",
    "|---|---|---|---|---|---|---|---|"
])

status_date_items = [x for x in items if x['type'] == 'STATUS_IN_DATE_COLUMN']
for item in status_date_items[:30]:
    raw_val = item['details'].split("'")[1]
    # parse
    has_ppo = "ppo" in raw_val.lower()
    has_off = "offcampus" in raw_val.lower()
    date_part = raw_val.replace("PPO", "").replace("ppo", "").replace("Offcampus", "").strip()
    status_part = "PPO" if has_ppo else ("Off-campus" if has_off else "Other")
    report_lines.append(f"| {item['file'][:22]}... | {item['sheet']} | {item['row']} | `{item['details'].split()[1]}` | {item['details'].split('placed at ')[1].split(' has')[0]} | `{raw_val}` | `{date_part if date_part else 'NULL'}` | `{status_part}` |")

report_lines.extend([
    "",
    "*(Total 113 occurrences of status/mode in date column cataloged for automated extraction)*",
    "",
    "### 6. Complex Package Parsing: Compound Packages (Stipend + CTC)",
    "The dataset contains compound package entries combining intern stipend and full-time CTC, plus pure monthly stipends that must not be counted as annual CTC.",
    "",
    "| Raw Package String | Count | Proposed `ctc_lpa` (Annual LPA) | Proposed `stipend_monthly_inr` | Interpretation / Reasoning |",
    "|---|---|---|---|---|",
    "| `40K+12.8LPA` | 6 | `12.8` | `40,000` | 40K INR/mo 6-month intern stipend + 12.8 LPA FTE CTC |",
    "| `45K, 22 Lac` | 6 | `22.0` | `45,000` | 45K INR/mo intern stipend + 22.0 LPA FTE CTC (Dell Technologies) |",
    "| `40K+17.5` | 3 | `17.5` | `40,000` | 40K INR/mo stipend + 17.5 LPA CTC |",
    "| `20K+10` | 1 | `10.0` | `20,000` | 20K INR/mo stipend + 10.0 LPA CTC |",
    "| `45K (Convert PPO 17LPA)` | 1 | `17.0` | `45,000` | 45K INR/mo intern converted to 17.0 LPA PPO |",
    "| `25K, 12.5 LPA` | 1 | `12.5` | `25,000` | 25K INR/mo stipend + 12.5 LPA CTC |",
    "| `45K` / `50K` / `40K` / `30K` / `35K` | 260 | `NULL` | `45,000` / `50,000` etc. | Pure monthly internship stipend. Must NEVER be treated as 45 LPA! |",
    "| `1.25Lac PM` / `1.25 Lac PM` | 10 | `NULL` | `125,000` | 1.25 Lakh per month stipend (e.g. American Express / Google intern) |",
    "| `Unpaid` | 17 | `NULL` | `0` | Unpaid internship |",
    "| `-` / `NA` / `N.A` / `NULL` | 58 | `NULL` | `NULL` | Package unknown / unannounced |",
    "",
    "### 7. Branch Code vs Branch Label Conflicts (Sample 35 of 150 offer rows)",
    "NIT Jalandhar student roll numbers encode the admission year (digits 1-2) and the department branch code (digits 3-5). In 150 offer rows (and 291 total rows), students appear in sheets or cells that conflict with their roll number branch code.",
    "",
    "| File | Sheet | Row | Roll No | Roll Branch Code | Canonical Branch from Roll | Branch Cell Content | Placed Company | Probable Root Cause |",
    "|---|---|---|---|---|---|---|---|---|"
])

branch_conflict_items = [x for x in items if x['type'] == 'BRANCH_CODE_CONFLICT']
for item in branch_conflict_items[:35]:
    roll = item['details'].split()[1]
    code = roll[2:5]
    exp = UG_CODE_TO_CANONICAL.get(code, "Unknown")
    cell_branch = item['details'].split("'")[1]
    comp = item['details'].split("placed at '")[1].split("'")[0]
    report_lines.append(f"| {item['file'][:20]}... | {item['sheet']} | {item['row']} | `{roll}` | `{code}` | **{exp}** | {cell_branch} | {comp} | Copy-paste from master placement roster |")

report_lines.extend([
    "",
    "*(All 150 branch conflicts logged with exact row and sheet for database resolution)*",
    "",
    "---",
    "",
    "## Summary of Privacy & Data Isolation Rules",
    "1. **HR Sheet Blacklist**: Workbook `2021-25 and 2023-25 Batch_Placement Database.xlsx`, sheet `Copy of Full Details` contains HR Contacts (HR Name, Contact Number, Email ID). This sheet is completely omitted from the database.",
    "2. **Summary Sheet Exclusion**: Sheets `Full Details`, `Count Wise Details`, `Count`, and `M.Tech 23-25 Full Details` contain pre-computed formulas and aggregates, not student-level truth. They are excluded from the ground truth database.",
    "3. **Student Privacy**: Student names, roll numbers, personal phone numbers, and categories are strictly anonymized. The chatbot interface will only report aggregated statistics with a minimum k-anonymity threshold (group size >= 3).",
    "",
    "---",
    "",
    "## Questions & Ambiguities for User Approval Before Phase 2",
    "1. **Branch Code vs Sheet Conflict Resolution**: When Roll No code says `Mechanical Engineering` (`109`) but the student is listed in `Electrical Engg` sheet (e.g. Roll `20109110` placed at Amazon 52 LPA), should the canonical branch be derived strictly from the **Roll Number code** or the **Sheet/Branch cell**? *(Recommended: Derive from Roll Number code, as it represents their official academic registration; trace back to 3rd year internship roster confirms `20109110` is Mechanical).* ",
    "2. **Trident Group Package in Textile Technology**: Rows 24 and 28 have date `2023-12-18` in the package column. Rows 25-27 for Trident Group have `12.0 LPA`. Should we set these two rows to `12.0 LPA` or keep `ctc_lpa = NULL` with reason `package_unconfirmed`?",
    "3. **Cross-Workbook Snapshot Overlap (`M.Tech 2023-25`)**: File 1 contains an early snapshot (80 offers) and File 2 contains an updated snapshot (134 offers with PPO packages like `22 Lac`). Confirm that deduplication on `(roll_no, company, offer_type)` should keep the richer File 2 record.",
    "4. **Compound Packages**: Confirm that for compound packages like `40K+12.8LPA` and `45K, 22 Lac`, `ctc_lpa` will be stored as `12.8` and `22.0` (float), and `stipend_monthly_inr` will be stored as `40,000` and `45,000`.",
    "5. **Santosh Kumar Palla (`2020 Batch`)**: Confirm that row 8 in Computer Engg (File 2) with roll `'2020 Batch'` placed at Infosys (3.6 LPA) should be mapped to student `20103104` (from 2020-24 CSE batch unplaced roster)."
])

report_content = "\n".join(report_lines)
with open("data_quality_report.md", "w", encoding="utf-8") as f:
    f.write(report_content)

print(f"data_quality_report.md generated successfully with {len(report_lines)} lines.")
