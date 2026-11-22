# Branch Conflicts Audit Report

- **Total Identified Branch Conflicts**: 291
- **Resolution Rule**: In NIT Jalandhar's roll numbering system (`YYDDPSSS`), digits 3-5 represent the official admitting department code. When an Excel cell or sheet name lists a different department than the matriculated code (e.g. due to dual-branch recruitment drives or cross-departmental electives), the database flags `is_branch_conflict = 1` and grounds canonical reporting on the student's authoritative enrolled degree program.

## Conflict Distribution by Source File

| Source Workbook | Conflict Count |
| :--- | :---: |
| `2020-24 and 2022-24 Batch_Placement Database.xlsx` | 118 |
| `2021-25 and 2023-25 Batch_Placement Database.xlsx` | 108 |
| `2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx` | 65 |

## Top Discrepancy Pairs (Roll Derivation vs Sheet Cell)

| Official Branch (from Roll Code) | Sheet / Cell Discipline | Instances |
| :--- | :--- | :---: |
| **MBA** | Humanities and Management | 30 |
| **MBA** | MBA (Self-Sponsored) | 23 |
| **Industrial and Production Engineering** | Mechanical Engineering | 15 |
| **Instrumentation and Control Engineering** | Electronics and Communication Engineering | 14 |
| **MBA** | MBA (Regular) | 12 |
| **Textile Technology** | Mechanical Engineering | 11 |
| **Chemical Engineering** | Electrical Engineering | 9 |
| **Mechanical Engineering** | Instrumentation and Control Engineering | 9 |
| **Industrial and Production Engineering** | Instrumentation and Control Engineering | 9 |
| **Chemical Engineering** | Instrumentation and Control Engineering | 8 |
| **Biotechnology** | Mechanical Engineering | 8 |
| **Textile Technology** | Electrical Engineering | 8 |
| **Instrumentation and Control Engineering** | Information Technology | 8 |
| **Civil Engineering** | Mechanical Engineering | 7 |
| **Textile Technology** | Industrial and Production Engineering | 7 |
| **Instrumentation and Control Engineering** | Computer Science and Engineering | 7 |
| **Instrumentation and Control Engineering** | Electrical Engineering | 6 |
| **Biotechnology** | Instrumentation and Control Engineering | 6 |
| **Chemical Engineering** | Electronics and Communication Engineering | 6 |
| **Textile Technology** | Instrumentation and Control Engineering | 6 |

## Sample Conflict Records

| Roll No | Student Name | Expected Branch | Sheet / Cell Branch | Company | File / Sheet |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `20110071` | SAUMYA CHATURVEDI | **Textile Technology** | Bio Technology | Amazon | `Biotechnology` (row 4) |
| `20111011` | ASHISH VERMA | **Biotechnology** | Civil Engineering | L&T Limited | `Civil Engg` (row 2) |
| `20124060` | MAURYA SHARMA | **Information Technology** | Computer Science and Engineering | Ensuredit | `Computer Engg` (row 2) |
| `20126003` | ADITI AGARWAL | **Electrical Engineering** | Computer Science and Engineering | Oracle India | `Computer Engg` (row 3) |
| `20109110` | VANSHIKA SHARMA | **Mechanical Engineering** | Electrical Engineering | Amazon | `Electrical Engg` (row 2) |
| `20109110` | VANSHIKA SHARMA | **Mechanical Engineering** | Electrical Engineering | Betalectic | `Electrical Engg` (row 3) |
| `20109110` | VANSHIKA SHARMA | **Mechanical Engineering** | Electrical Engineering | Surassa | `Electrical Engg` (row 4) |
| `20113026` | DIVYANSHU SINGH | **Industrial and Production Engineering** | Electrical Engineering | Betalectic | `Electrical Engg` (row 5) |
| `20113026` | DIVYANSHU SINGH | **Industrial and Production Engineering** | Electrical Engineering | Zomato | `Electrical Engg` (row 6) |
| `20106081` | RAVINDER CHADHA | **Instrumentation and Control Engineering** | Electrical Engineering | Rapidfort | `Electrical Engg` (row 7) |
| `20109015` | ANIRUDH SAINI | **Mechanical Engineering** | Electrical Engineering | Trident Group | `Electrical Engg` (row 8) |
| `20112003` | Abhay Kumar | **Chemical Engineering** | Electrical Engineering | Genpact next Gen | `Electrical Engg` (row 9) |
| `20112003` | Abhay Kumar | **Chemical Engineering** | Electrical Engineering | Balarpur Industries (BGPPL) | `Electrical Engg` (row 10) |
| `20106056` | MADALA CHANGALA NAGA LAKSHMI NEHA | **Instrumentation and Control Engineering** | Electronics and Communication Engineering | Nvida | `Electronics Engg` (row 2) |
| `20126043` | PRAGATI GUPTA | **Electrical Engineering** | Electronics and Communication Engineering | Nvida | `Electronics Engg` (row 3) |
| `20126043` | PRAGATI GUPTA | **Electrical Engineering** | Electronics and Communication Engineering | Daimler Truck Innovation Center India | `Electronics Engg` (row 4) |
| `20113025` | DEVANSH GAUR | **Industrial and Production Engineering** | Electronics and Communication Engineering | Incedo | `Electronics Engg` (row 5) |
| `20111004` | AMANPREET KAUR | **Biotechnology** | Industrial and Production Engineering | Ashok Leyland | `Industrial Engg` (row 8) |
| `20109103` | TANYA | **Mechanical Engineering** | Instrumentation and Control Engineering | AdvaRisk | `Instrumentation Engg` (row 2) |
| `20111021` | DIVANSHI | **Biotechnology** | Instrumentation and Control Engineering | Samsung Engineering | `Instrumentation Engg` (row 3) |
| `20109060` | NAMAN GUPTA | **Mechanical Engineering** | Instrumentation and Control Engineering | Moody's | `Instrumentation Engg` (row 4) |
| `20112038` | JIYA | **Chemical Engineering** | Instrumentation and Control Engineering | Technip Energy | `Instrumentation Engg` (row 5) |
| `20112040` | KAUSHAL AGRAWAL | **Chemical Engineering** | Instrumentation and Control Engineering | Trianz Digital | `Instrumentation Engg` (row 6) |
| `20113079` | TANISHQ JAIN | **Industrial and Production Engineering** | Instrumentation and Control Engineering | Accolite India | `Instrumentation Engg` (row 7) |
| `20110060` | RAHUL KUMAR | **Textile Technology** | Mechanical Engineering | Incture | `Mechanical Engg` (row 2) |
