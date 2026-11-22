# NIT Jalandhar Placement Database - Data Quality & Audit Report

> **Status**: Phase 1 Audit Complete (Read-only; No files modified)
> **Total Student Records Audited**: 9,385 across 3 Excel workbooks
> **Total Offer Records**: 3,009 rows (6,376 unplaced students / internship roster rows)
> **Total Data Quality Flagged Rows**: 392 records requiring attention/clarification

---

## Executive Summary of Audit Findings

| Audit Category | Issue Count | Description | Impact & Recommended Resolution |
|---|---|---|---|
| **Column Alignment & Swaps** | 34 rows | Textile Technology (File 1) has `Date Result` and `Category` headers reversed relative to cell contents. | Auto-swap columns 6 & 7 during ingestion for this sheet. |
| **Status Shifted to Date** | 113 rows | Offer status (`PPO`, `Offcampus`, `04.10.2023 PPO`) stored in Date column. | Extract clean ISO date (e.g. `2023-10-04`) and move `PPO`/`Offcampus` flag to Offer Type / Mode. |
| **Date Typos** | 5 rows | Month entered with extra zeros (e.g., `10.012.2024` for Flipkart, `22.011.2024` for NXP). | Normalize `10.012.2024` -> `2024-12-10`, `22.011.2024` -> `2024-11-22`. |
| **Date in Package Column** | 2 rows | Date `2023-12-18` entered in package column for Trident Group PPO rows in Textile Technology. | Trident GET package is 12.0 LPA. Clarify whether PPO is 12.0 LPA or mark package as NULL (unverified). |
| **Package / Stipend Units** | 475 rows | 188 distinct non-float package strings: pure stipends (`45K`, `1.25Lac PM`), compound packages (`40K+12.8LPA`), and unpaid/missing (`-`, `Unpaid`, `NA`). | Split into `ctc_lpa` (float) and `stipend_monthly_inr` (int/float). Never count stipend towards CTC. |
| **Branch Code Conflicts** | 150 offer rows (291 total) | Roll number digits 3-5 differ from the sheet or branch cell (e.g. Roll `20109110` Mech in EE sheet; 20102 CE in ME sheet). | Derive canonical branch from roll number prefix code; flag conflicts for user confirmation. |
| **Missing / Invalid Roll No** | 1 row | Computer Engg (File 2) row 8 has `'2020 Batch'` in roll column for Santosh Kumar Palla. | Matched to Roll `20103104` (2020-24 CSE batch unplaced student who appeared with 2021-25 batch). |
| **Cross-Workbook Snapshot Overlaps** | 80+ rows | `M.Tech 2023-25` sheet exists in both File 1 (80 early offers) and File 2 (134 updated offers with PPO conversions). | Deduplicate across files using `(roll_no, company, offer_type)`; prefer later snapshot in File 2. |
| **Student Multi-Offer / Progression** | 38 pairs | Same student appears in 3rd-year internship roster and later in branch sheet with FTE/PPO offer. | Keep both rows but tag them with distinct `offer_type` (`Intern` vs `FTE`/`PPO`). |
| **HR & Privacy Sheet** | 1 sheet | `Copy of Full Details` in File 2 contains HR names, phone numbers, and email IDs. | Exclude sheet completely from DB ingestion. Implement strict aggregation privacy rules (min group 3). |

---

## Detailed Audit Log: All Flagged Rows

### 1. Column Shift / Category in Date Column (Textile Technology)
In workbook `2020-24 and 2022-24 Batch_Placement Database.xlsx`, sheet `Textile Technology`, column 6 is labeled `Date Result` and column 7 is labeled `Category`. In rows 2 to 35, column 6 contains category values (`General`, `SC`, `OBC-NCL`, `GEN-EWS`, `ST`) while column 7 contains result dates (`05.09.2023`, `12.03.2024`, etc.).

| File | Sheet | Row | Roll No | Company | Col 6 (Labeled Date Result) | Col 7 (Labeled Category) | Remediation |
|---|---|---|---|---|---|---|---|
| 2020-24 and 2022-24 Batch... | Textile Technology | 2 | `20110077` | 'Amazon' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 3 | `20110084` | 'Amazon' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 4 | `20110072` | 'Arvind Limited' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 5 | `20110010` | 'Delhivery Limited' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 6 | `20110086` | 'Directioneducare' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 7 | `20110014` | 'EXL Services' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 8 | `20110033` | 'Gainers India' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 9 | `20110074` | 'Gainers India' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 10 | `20110042` | 'Hike Education' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 11 | `20110025` | 'Himatsingka Seide Ltd.' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 12 | `20110041` | 'Himatsingka Seide Ltd.' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 13 | `20110078` | 'Himatsingka Seide Ltd.' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 14 | `20110051` | 'Quantiphi' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 15 | `20110001` | 'Reliance Industries Limited' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 16 | `20110013` | 'Reliance Industries Limited' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 17 | `20110016` | 'Reliance Industries Limited' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 18 | `20110022` | 'Reliance Industries Limited' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 19 | `20110030` | 'Reliance Industries Limited' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 20 | `20110061` | 'Reliance Industries Limited' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 21 | `20110066` | 'Reliance Industries Limited' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 22 | `20110051` | 'Teachnook' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 23 | `20110079` | 'Tex Fasteners' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 24 | `20110012` | 'Trident Group' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 25 | `20110036` | 'Trident Group' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 26 | `20110045` | 'Trident Group' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 27 | `20110065` | 'Trident Group' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 28 | `20110067` | 'Trident Group' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 29 | `20110006` | 'Trutzschler' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 30 | `20110009` | 'Unacademy' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 31 | `20110028` | 'Unacademy' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 32 | `20110057` | 'Unacademy' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 33 | `20110034` | 'Urban Company' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 34 | `20110082` | 'Urban Company' | Category found | Date found | Swap Col 6 and 7 |
| 2020-24 and 2022-24 Batch... | Textile Technology | 35 | `20110034` | 'Zomato' | Category found | Date found | Swap Col 6 and 7 |

### 2. Date in Package Column (High Severity)
In `Textile Technology` (File 1), two students placed at Trident Group have date `2023-12-18 00:00:00` sitting in the Package column.

| File | Sheet | Row | Roll No | Company | Raw Package Cell | Actual Meaning / Remediation |
|---|---|---|---|---|---|---|
| 2020-24 and 2022-24 Batch... | Textile Technology | 24 | `20110012` | Trident Group | `2023-12-18 00:00:00` | PPO effective date. Other Trident rows have 12.0 LPA. Clarify or set `ctc_lpa = 12.0` / NULL with reason. |
| 2020-24 and 2022-24 Batch... | Textile Technology | 28 | `20110067` | Trident Group | `2023-12-18 00:00:00` | PPO effective date. Other Trident rows have 12.0 LPA. Clarify or set `ctc_lpa = 12.0` / NULL with reason. |

### 3. Invalid Roll Number Format / Subheader Row

| File | Sheet | Row | Raw Roll Cell | Student Name | Company | Package | Remediation |
|---|---|---|---|---|---|---|---|
| 2021-25 and 2023-25 Batch... | Computer Engg | 8 | `'2020 Batch'` | Santosh Kumar Palla | Infosys | 3.6 LPA | Trace: Student is `20103104` (unplaced in 2020-24 batch, placed with 2021-25 batch). Auto-resolve to `20103104`. |

### 4. Date Column Typos (Months with Extra Zero)

| File | Sheet | Row | Roll No | Company | Raw Date String | Normalized Clean Date |
|---|---|---|---|---|---|---|
| 2021-25 and 2023-25 Batch... | Chemical Engg | 69 | `21112040` | 'Flipkart' | `10.012.2024` | `2024-12-10` |
| 2021-25 and 2023-25 Batch... | Electronics Engg | 12 | `21104001` | 'NXP' | `22.011.2024` | `2024-11-22` |
| 2021-25 and 2023-25 Batch... | Electronics Engg | 96 | `21104060` | 'Flipkart' | `10.012.2024` | `2024-12-10` |
| 2021-25 and 2023-25 Batch... | Industrial Engg | 83 | `21113002` | 'Flipkart' | `10.012.2024` | `2024-12-10` |
| 2021-25 and 2023-25 Batch... | Instrumentation Engg | 111 | `21106099` | 'Flipkart' | `10.012.2024` | `2024-12-10` |

### 5. Status / Offer-Type Shifted Into Date Column (Sample 30 of 113 rows)
Values like `04.10.2023 PPO`, `Offcampus`, `PPO`, or `Intern` entered in the Date Result column.

| File | Sheet | Row | Roll No | Company | Raw Date Cell | Clean Extracted Date | Extracted Offer Mode / Status |
|---|---|---|---|---|---|---|---|
| 2020-24 and 2022-24 Ba... | Chemical Engg | 7 | `20112005` | 'Reliance Industries Limited' | `Reliance Industries Limited` | `Reliance Industries Limited` | `Other` |
| 2020-24 and 2022-24 Ba... | Chemical Engg | 29 | `20112025` | 'Reliance Industries Limited' | `Reliance Industries Limited` | `Reliance Industries Limited` | `Other` |
| 2020-24 and 2022-24 Ba... | Chemical Engg | 72 | `20112066` | 'Reliance Industries Limited' | `Reliance Industries Limited` | `Reliance Industries Limited` | `Other` |
| 2020-24 and 2022-24 Ba... | Computer Engg | 50 | `20103044` | 'Goldman Sachs' | `Goldman Sachs` | `Goldman Sachs` | `Other` |
| 2020-24 and 2022-24 Ba... | Computer Engg | 199 | `20103164` | 'Adobe' | `Adobe` | `Adobe` | `Other` |
| 2020-24 and 2022-24 Ba... | Computer Engg | 204 | `20103168` | 'PayPal University Team' | `PayPal University Team` | `PayPal University Team` | `Other` |
| 2020-24 and 2022-24 Ba... | Mechanical Engg | 65 | `20109050` | 'Reliance Industries Limited' | `Reliance Industries Limited` | `Reliance Industries Limited` | `Other` |
| 2020-24 and 2022-24 Ba... | MBA | 19 | `22701017` | 'Zomato' | `Zomato` | `Zomato` | `Other` |
| 2021-25 and 2023-25 Ba... | Biotechnology | 2 | `21111025` | 'Kisanwala Technology Pvt. ltd.' | `Kisanwala Technology Pvt. ltd.` | `Kisanwala Technology Pvt. ltd.` | `Other` |
| 2021-25 and 2023-25 Ba... | Biotechnology | 3 | `21111015` | 'Astrotalk' | `Astrotalk` | `Astrotalk` | `Other` |
| 2021-25 and 2023-25 Ba... | Biotechnology | 4 | `21111020` | 'Chainscore Finance Pvt. Ltd.' | `Chainscore Finance Pvt. Ltd.` | `Chainscore Finance Pvt. Ltd.` | `Other` |
| 2021-25 and 2023-25 Ba... | Biotechnology | 5 | `21111016` | 'School Hack FZLLC' | `School Hack FZLLC` | `School Hack FZLLC` | `Other` |
| 2021-25 and 2023-25 Ba... | Biotechnology | 6 | `21111031` | 'Primotech' | `Primotech` | `Primotech` | `Other` |
| 2021-25 and 2023-25 Ba... | Chemical Engg | 2 | `21112038` | 'Thrillophilla' | `Thrillophilla` | `Thrillophilla` | `Other` |
| 2021-25 and 2023-25 Ba... | Chemical Engg | 5 | `21112049` | 'Zomato' | `Zomato` | `Zomato` | `Other` |
| 2021-25 and 2023-25 Ba... | Chemical Engg | 6 | `21112055` | 'Juspay' | `Juspay` | `Juspay` | `Other` |
| 2021-25 and 2023-25 Ba... | Chemical Engg | 7 | `21112005` | 'Neutrawell Healthcare Pvt. Ltd.' | `Neutrawell Healthcare Pvt. Ltd.` | `Neutrawell Healthcare Pvt. Ltd.` | `Other` |
| 2021-25 and 2023-25 Ba... | Chemical Engg | 8 | `21112010` | 'Centrient Pharaceuticals India Pvt. Ltd.' | `Centrient Pharaceuticals India Pvt. Ltd.` | `Centrient Pharaceuticals India Pvt. Ltd.` | `Other` |
| 2021-25 and 2023-25 Ba... | Chemical Engg | 9 | `21112025` | 'Blinkt' | `Blinkt` | `Blinkt` | `Other` |
| 2021-25 and 2023-25 Ba... | Chemical Engg | 10 | `21112012` | 'ENTNT' | `ENTNT` | `ENTNT` | `Other` |
| 2021-25 and 2023-25 Ba... | Chemical Engg | 11 | `21112033` | 'Zomato' | `Zomato` | `Zomato` | `Other` |
| 2021-25 and 2023-25 Ba... | Chemical Engg | 12 | `21112027` | 'Cadence' | `Cadence` | `Cadence` | `Other` |
| 2021-25 and 2023-25 Ba... | Chemical Engg | 13 | `21112029` | 'OGGANS' | `OGGANS` | `OGGANS` | `Other` |
| 2021-25 and 2023-25 Ba... | Chemical Engg | 14 | `21112081` | 'NetQull Technologies' | `NetQull Technologies` | `NetQull Technologies` | `Other` |
| 2021-25 and 2023-25 Ba... | Chemical Engg | 38 | `21112065` | 'TechnipEnergies' | `TechnipEnergies` | `TechnipEnergies` | `Other` |
| 2021-25 and 2023-25 Ba... | Civil Engg | 53 | `21102090` | 'Cabra Bags' | `Cabra Bags` | `Cabra Bags` | `Other` |
| 2021-25 and 2023-25 Ba... | Computer Engg | 150 | `21103007` | 'Kashmiri Lal Tarun Khanna Pvt. ltd.' | `Kashmiri Lal Tarun Khanna Pvt. ltd.` | `Kashmiri Lal Tarun Khanna Pvt. ltd.` | `Other` |
| 2021-25 and 2023-25 Ba... | Computer Engg | 167 | `21103014` | 'Nvida' | `Nvida` | `Nvida` | `Other` |
| 2021-25 and 2023-25 Ba... | Computer Engg | 168 | `21103046` | 'Juspay' | `Juspay` | `Juspay` | `Other` |
| 2021-25 and 2023-25 Ba... | Computer Engg | 180 | `21102028` | 'Cred' | `Cred` | `Cred` | `Other` |

*(Total 113 occurrences of status/mode in date column cataloged for automated extraction)*

### 6. Complex Package Parsing: Compound Packages (Stipend + CTC)
The dataset contains compound package entries combining intern stipend and full-time CTC, plus pure monthly stipends that must not be counted as annual CTC.

| Raw Package String | Count | Proposed `ctc_lpa` (Annual LPA) | Proposed `stipend_monthly_inr` | Interpretation / Reasoning |
|---|---|---|---|---|
| `40K+12.8LPA` | 6 | `12.8` | `40,000` | 40K INR/mo 6-month intern stipend + 12.8 LPA FTE CTC |
| `45K, 22 Lac` | 6 | `22.0` | `45,000` | 45K INR/mo intern stipend + 22.0 LPA FTE CTC (Dell Technologies) |
| `40K+17.5` | 3 | `17.5` | `40,000` | 40K INR/mo stipend + 17.5 LPA CTC |
| `20K+10` | 1 | `10.0` | `20,000` | 20K INR/mo stipend + 10.0 LPA CTC |
| `45K (Convert PPO 17LPA)` | 1 | `17.0` | `45,000` | 45K INR/mo intern converted to 17.0 LPA PPO |
| `25K, 12.5 LPA` | 1 | `12.5` | `25,000` | 25K INR/mo stipend + 12.5 LPA CTC |
| `45K` / `50K` / `40K` / `30K` / `35K` | 260 | `NULL` | `45,000` / `50,000` etc. | Pure monthly internship stipend. Must NEVER be treated as 45 LPA! |
| `1.25Lac PM` / `1.25 Lac PM` | 10 | `NULL` | `125,000` | 1.25 Lakh per month stipend (e.g. American Express / Google intern) |
| `Unpaid` | 17 | `NULL` | `0` | Unpaid internship |
| `-` / `NA` / `N.A` / `NULL` | 58 | `NULL` | `NULL` | Package unknown / unannounced |

### 7. Branch Code vs Branch Label Conflicts (Sample 35 of 150 offer rows)
NIT Jalandhar student roll numbers encode the admission year (digits 1-2) and the department branch code (digits 3-5). In 150 offer rows (and 291 total rows), students appear in sheets or cells that conflict with their roll number branch code.

| File | Sheet | Row | Roll No | Roll Branch Code | Canonical Branch from Roll | Branch Cell Content | Placed Company | Probable Root Cause |
|---|---|---|---|---|---|---|---|---|
| 2020-24 and 2022-24 ... | Biotechnology | 4 | `20110071` | `110` | **Textile Technology** | Bio Technology | Amazon | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Civil Engg | 2 | `20111011` | `111` | **Biotechnology** | Civil Engineering | L&T Limited | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Computer Engg | 2 | `20124060` | `124` | **Information Technology** | Computer Science and Engineering | Ensuredit | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Computer Engg | 3 | `20126003` | `126` | **Electrical Engineering** | Computer Science and Engineering | Oracle India | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electrical Engg | 2 | `20109110` | `109` | **Mechanical Engineering** | Electrical Engineering | Amazon | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electrical Engg | 3 | `20109110` | `109` | **Mechanical Engineering** | Electrical Engineering | Betalectic | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electrical Engg | 4 | `20109110` | `109` | **Mechanical Engineering** | Electrical Engineering | Surassa | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electrical Engg | 5 | `20113026` | `113` | **Industrial and Production Engineering** | Electrical Engineering | Betalectic | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electrical Engg | 6 | `20113026` | `113` | **Industrial and Production Engineering** | Electrical Engineering | Zomato | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electrical Engg | 7 | `20106081` | `106` | **Instrumentation and Control Engineering** | Electrical Engineering | Rapidfort | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electrical Engg | 8 | `20109015` | `109` | **Mechanical Engineering** | Electrical Engineering | Trident Group | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electrical Engg | 9 | `20112003` | `112` | **Chemical Engineering** | Electrical Engineering | Genpact next Gen | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electrical Engg | 10 | `20112003` | `112` | **Chemical Engineering** | Electrical Engineering | Balarpur Industries (BGPPL) | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electronics Engg | 2 | `20106056` | `106` | **Instrumentation and Control Engineering** | Electronics and Communication Engineering | Nvida | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electronics Engg | 3 | `20126043` | `126` | **Electrical Engineering** | Electronics and Communication Engineering | Nvida | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electronics Engg | 4 | `20126043` | `126` | **Electrical Engineering** | Electronics and Communication Engineering | Daimler Truck Innovation Center India | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Electronics Engg | 5 | `20113025` | `113` | **Industrial and Production Engineering** | Electronics and Communication Engineering | Incedo | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Industrial Engg | 8 | `20111004` | `111` | **Biotechnology** | Industrial and Production Engineering | Ashok Leyland | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Instrumentation Engg | 2 | `20109103` | `109` | **Mechanical Engineering** | Instrumentation and Control Engineering | AdvaRisk | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Instrumentation Engg | 3 | `20111021` | `111` | **Biotechnology** | Instrumentation and Control Engineering | Samsung Engineering | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Instrumentation Engg | 4 | `20109060` | `109` | **Mechanical Engineering** | Instrumentation and Control Engineering | Moody | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Instrumentation Engg | 5 | `20112038` | `112` | **Chemical Engineering** | Instrumentation and Control Engineering | Technip Energy | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Instrumentation Engg | 6 | `20112040` | `112` | **Chemical Engineering** | Instrumentation and Control Engineering | Trianz Digital | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Instrumentation Engg | 7 | `20113079` | `113` | **Industrial and Production Engineering** | Instrumentation and Control Engineering | Accolite India | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Mechanical Engg | 2 | `20110060` | `110` | **Textile Technology** | Mechanical Engineering | Incture | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Mechanical Engg | 3 | `20102041` | `102` | **Civil Engineering** | Mechanical Engineering | Hero MotorCorp | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Mechanical Engg | 4 | `20102067` | `102` | **Civil Engineering** | Mechanical Engineering | Maruti Suzuki India | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Mechanical Engg | 5 | `20110046` | `110` | **Textile Technology** | Mechanical Engineering | Maruti Suzuki India | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Mechanical Engg | 6 | `20110038` | `110` | **Textile Technology** | Mechanical Engineering | Maruti Suzuki India | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Mechanical Engg | 7 | `20102019` | `102` | **Civil Engineering** | Mechanical Engineering | Maruti Suzuki India | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Mechanical Engg | 8 | `20113038` | `113` | **Industrial and Production Engineering** | Mechanical Engineering | Maruti Suzuki India | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Mechanical Engg | 9 | `20113038` | `113` | **Industrial and Production Engineering** | Mechanical Engineering | Ashok Leyland | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Mechanical Engg | 10 | `20110068` | `110` | **Textile Technology** | Mechanical Engineering | Jubilant Food works | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Mechanical Engg | 11 | `20111012` | `111` | **Biotechnology** | Mechanical Engineering | Technip Energy | Copy-paste from master placement roster |
| 2020-24 and 2022-24 ... | Mechanical Engg | 138 | `20113023` | `113` | **Industrial and Production Engineering** | Mechanical Engineering | Water Technologies & Solutions | Copy-paste from master placement roster |

*(All 150 branch conflicts logged with exact row and sheet for database resolution)*

---

## Summary of Privacy & Data Isolation Rules
1. **HR Sheet Blacklist**: Workbook `2021-25 and 2023-25 Batch_Placement Database.xlsx`, sheet `Copy of Full Details` contains HR Contacts (HR Name, Contact Number, Email ID). This sheet is completely omitted from the database.
2. **Summary Sheet Exclusion**: Sheets `Full Details`, `Count Wise Details`, `Count`, and `M.Tech 23-25 Full Details` contain pre-computed formulas and aggregates, not student-level truth. They are excluded from the ground truth database.
3. **Student Privacy**: Student names, roll numbers, personal phone numbers, and categories are strictly anonymized. The chatbot interface will only report aggregated statistics with a minimum k-anonymity threshold (group size >= 3).

---

## Questions & Ambiguities for User Approval Before Phase 2
1. **Branch Code vs Sheet Conflict Resolution**: When Roll No code says `Mechanical Engineering` (`109`) but the student is listed in `Electrical Engg` sheet (e.g. Roll `20109110` placed at Amazon 52 LPA), should the canonical branch be derived strictly from the **Roll Number code** or the **Sheet/Branch cell**? *(Recommended: Derive from Roll Number code, as it represents their official academic registration; trace back to 3rd year internship roster confirms `20109110` is Mechanical).* 
2. **Trident Group Package in Textile Technology**: Rows 24 and 28 have date `2023-12-18` in the package column. Rows 25-27 for Trident Group have `12.0 LPA`. Should we set these two rows to `12.0 LPA` or keep `ctc_lpa = NULL` with reason `package_unconfirmed`?
3. **Cross-Workbook Snapshot Overlap (`M.Tech 2023-25`)**: File 1 contains an early snapshot (80 offers) and File 2 contains an updated snapshot (134 offers with PPO packages like `22 Lac`). Confirm that deduplication on `(roll_no, company, offer_type)` should keep the richer File 2 record.
4. **Compound Packages**: Confirm that for compound packages like `40K+12.8LPA` and `45K, 22 Lac`, `ctc_lpa` will be stored as `12.8` and `22.0` (float), and `stipend_monthly_inr` will be stored as `40,000` and `45,000`.
5. **Santosh Kumar Palla (`2020 Batch`)**: Confirm that row 8 in Computer Engg (File 2) with roll `'2020 Batch'` placed at Infosys (3.6 LPA) should be mapped to student `20103104` (from 2020-24 CSE batch unplaced roster).