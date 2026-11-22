import sqlite3
import json
import os
from collections import Counter

DB_PATH = "data/nitj_placement.db"
os.makedirs("eval", exist_ok=True)

def create_eval_dataset():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    raw_questions = [
        # ==========================================
        # 1. LOOKUP (10 questions)
        # ==========================================
        {
            "id": "LOOKUP_01",
            "type_id": 1,
            "type_name": "Lookup",
            "question": "What is the CTC of Microsoft for CSE?",
            "entities": {"companies": ["Microsoft"], "branches": ["CSE"], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Microsoft' AND b.short_name = 'CSE' AND o.ctc_lpa IS NOT NULL ORDER BY o.ctc_lpa DESC;",
            "answer_type": "number_list",
            "notes": "Verified FTE CTC is 52.0 LPA. Excludes summer intern stipend."
        },
        {
            "id": "LOOKUP_02",
            "type_id": 1,
            "type_name": "Lookup",
            "question": "What package did Google offer?",
            "entities": {"companies": ["Google"], "branches": [], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Google' AND o.ctc_lpa IS NOT NULL ORDER BY o.ctc_lpa DESC;",
            "answer_type": "number_list",
            "notes": "Google offers in dataset: 62.0 LPA and 30.5 LPA."
        },
        {
            "id": "LOOKUP_03",
            "type_id": 1,
            "type_name": "Lookup",
            "question": "What was the package offered by PayPal?",
            "entities": {"companies": ["PayPal"], "branches": [], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'PayPal' AND o.ctc_lpa IS NOT NULL;",
            "answer_type": "number_list",
            "notes": "PayPal offered 34.4 LPA."
        },
        {
            "id": "LOOKUP_04",
            "type_id": 1,
            "type_name": "Lookup",
            "question": "CTC of Micorsoft for CSE",
            "entities": {"companies": ["Microsoft"], "branches": ["CSE"], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Microsoft' AND b.short_name = 'CSE' AND o.ctc_lpa IS NOT NULL;",
            "answer_type": "number_list",
            "notes": "Spelling variant 'Micorsoft' resolved to Microsoft."
        },
        {
            "id": "LOOKUP_05",
            "type_id": 1,
            "type_name": "Lookup",
            "question": "What package did Nvida offer to Electronics engineering?",
            "entities": {"companies": ["Nvidia"], "branches": ["ECE"], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Nvidia' AND b.short_name = 'ECE' AND o.ctc_lpa IS NOT NULL;",
            "answer_type": "number_list",
            "notes": "Typo Nvida resolved to Nvidia. Offer at 25.0 LPA."
        },
        {
            "id": "LOOKUP_06",
            "type_id": 1,
            "type_name": "Lookup",
            "question": "What is the CTC offered by Uber?",
            "entities": {"companies": ["Uber"], "branches": [], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Uber' AND o.ctc_lpa IS NOT NULL;",
            "answer_type": "number_list",
            "notes": "Uber offer CTC is 59.0 LPA."
        },
        {
            "id": "LOOKUP_07",
            "type_id": 1,
            "type_name": "Lookup",
            "question": "What package was given by Cred?",
            "entities": {"companies": ["Cred"], "branches": [], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Cred' AND o.ctc_lpa IS NOT NULL;",
            "answer_type": "number_list",
            "notes": "Cred package is 52.0 LPA."
        },
        {
            "id": "LOOKUP_08",
            "type_id": 1,
            "type_name": "Lookup",
            "question": "What package does Zomato offer for Chemical Engineering?",
            "entities": {"companies": ["Zomato"], "branches": ["CHE"], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Zomato' AND b.short_name = 'CHE' AND o.ctc_lpa IS NOT NULL;",
            "answer_type": "number_list",
            "notes": "Zomato offered 6.0 LPA to Chemical Engg."
        },
        {
            "id": "LOOKUP_09",
            "type_id": 1,
            "type_name": "Lookup",
            "question": "Package of Oracle India for Information Technology",
            "entities": {"companies": ["Oracle"], "branches": ["IT"], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Oracle' AND b.short_name = 'IT' AND o.ctc_lpa IS NOT NULL ORDER BY o.ctc_lpa DESC;",
            "answer_type": "number_list",
            "notes": "Oracle offers in IT."
        },
        {
            "id": "LOOKUP_10",
            "type_id": 1,
            "type_name": "Lookup",
            "question": "What is the CTC of Goldman Sachs?",
            "entities": {"companies": ["Goldman Sachs"], "branches": [], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Goldman Sachs' AND o.ctc_lpa IS NOT NULL;",
            "answer_type": "number_list",
            "notes": "Goldman Sachs package: 24.0 LPA."
        },

        # ==========================================
        # 2. COUNT BY CONDITION (10 questions)
        # ==========================================
        {
            "id": "COUNT_01",
            "type_id": 2,
            "type_name": "Count by condition",
            "question": "How many students from IT got placed in Amazon?",
            "entities": {"companies": ["Amazon"], "branches": ["IT"], "years": []},
            "sql": "SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Amazon' AND b.short_name = 'IT' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Distinct IT students placed at Amazon."
        },
        {
            "id": "COUNT_02",
            "type_id": 2,
            "type_name": "Count by condition",
            "question": "How many students were placed in Microsoft from CSE?",
            "entities": {"companies": ["Microsoft"], "branches": ["CSE"], "years": []},
            "sql": "SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Microsoft' AND b.short_name = 'CSE' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Distinct CSE students placed in Microsoft with FTE/PPO."
        },
        {
            "id": "COUNT_03",
            "type_id": 2,
            "type_name": "Count by condition",
            "question": "How many students received offers above 20 LPA in 2020-2024 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2020-2024' AND o.ctc_lpa > 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Distinct students with package > 20 LPA in batch 2020-2024."
        },
        {
            "id": "COUNT_04",
            "type_id": 2,
            "type_name": "Count by condition",
            "question": "How many total offers were made by Infosys?",
            "entities": {"companies": ["Infosys"], "branches": [], "years": []},
            "sql": "SELECT COUNT(o.offer_id) FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Infosys';",
            "answer_type": "scalar",
            "notes": "Total offers made by Infosys."
        },
        {
            "id": "COUNT_05",
            "type_id": 2,
            "type_name": "Count by condition",
            "question": "How many female students got placed in 2020-2024 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2020-2024' AND s.gender = 'F' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Female placed students in 2020-2024 batch."
        },
        {
            "id": "COUNT_06",
            "type_id": 2,
            "type_name": "Count by condition",
            "question": "How many total offers were given to Mechanical Engineering students?",
            "entities": {"companies": [], "branches": ["ME"], "years": []},
            "sql": "SELECT COUNT(o.offer_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = 'ME' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Total FTE/PPO job offers in Mechanical."
        },
        {
            "id": "COUNT_07",
            "type_id": 2,
            "type_name": "Count by condition",
            "question": "How many students got placed off-campus?",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id WHERE o.offer_mode = 'Off-campus';",
            "answer_type": "scalar",
            "notes": "Distinct students with off-campus offers."
        },
        {
            "id": "COUNT_08",
            "type_id": 2,
            "type_name": "Count by condition",
            "question": "How many offers were made with CTC greater than or equal to 50 LPA?",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT COUNT(o.offer_id) FROM offers o WHERE o.ctc_lpa >= 50.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Total super-dream offers >= 50 LPA."
        },
        {
            "id": "COUNT_09",
            "type_id": 2,
            "type_name": "Count by condition",
            "question": "How many students from Chemical Engineering were placed in Reliance Industries?",
            "entities": {"companies": ["Reliance Industries"], "branches": ["CHE"], "years": []},
            "sql": "SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Reliance Industries' AND b.short_name = 'CHE' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Distinct Chemical students at Reliance."
        },
        {
            "id": "COUNT_10",
            "type_id": 2,
            "type_name": "Count by condition",
            "question": "How many students have double job offers in 2020-2024 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT COUNT(*) FROM (SELECT s.student_id FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2020-2024' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.student_id HAVING COUNT(o.offer_id) >= 2);",
            "answer_type": "scalar",
            "notes": "Students holding >= 2 FTE/PPO offers in 2020-2024 batch."
        },

        # ==========================================
        # 3. BRANCH-WISE / YEAR-WISE BREAKDOWNS (10 questions)
        # ==========================================
        {
            "id": "BREAKDOWN_01",
            "type_id": 3,
            "type_name": "Branch-wise / year-wise breakdowns",
            "question": "Company-wise offers for ECE in 2020-2024 batch",
            "entities": {"companies": [], "branches": ["ECE"], "years": ["2020-2024"]},
            "sql": "SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = 'ECE' AND s.batch_id = '2020-2024' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY offers_count DESC, c.canonical_name ASC;",
            "answer_type": "table",
            "notes": "Breakdown of ECE offers per company in 2020-2024."
        },
        {
            "id": "BREAKDOWN_02",
            "type_id": 3,
            "type_name": "Branch-wise / year-wise breakdowns",
            "question": "Branch-wise placed students count in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT b.short_name, COUNT(DISTINCT s.student_id) AS placed_count FROM branches b JOIN students s ON b.branch_code = s.branch_code JOIN offers o ON s.student_id = o.student_id WHERE s.batch_id = '2020-2024' AND b.degree = 'B.Tech' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name ORDER BY placed_count DESC;",
            "answer_type": "table",
            "notes": "Placed students count across B.Tech branches."
        },
        {
            "id": "BREAKDOWN_03",
            "type_id": 3,
            "type_name": "Branch-wise / year-wise breakdowns",
            "question": "Batch-wise offers count for Amazon",
            "entities": {"companies": ["Amazon"], "branches": [], "years": []},
            "sql": "SELECT s.batch_id, COUNT(o.offer_id) AS amazon_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Amazon' GROUP BY s.batch_id ORDER BY s.batch_id ASC;",
            "answer_type": "table",
            "notes": "Amazon offers per batch."
        },
        {
            "id": "BREAKDOWN_04",
            "type_id": 3,
            "type_name": "Branch-wise / year-wise breakdowns",
            "question": "Category-wise placement count in CSE for 2020-2024 batch",
            "entities": {"companies": [], "branches": ["CSE"], "years": ["2020-2024"]},
            "sql": "SELECT s.category, COUNT(DISTINCT s.student_id) AS placed_students FROM students s JOIN branches b ON s.branch_code = b.branch_code JOIN offers o ON s.student_id = o.student_id WHERE b.short_name = 'CSE' AND s.batch_id = '2020-2024' AND s.category IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.category ORDER BY placed_students DESC;",
            "answer_type": "table",
            "notes": "Category distribution of placed students in CSE."
        },
        {
            "id": "BREAKDOWN_05",
            "type_id": 3,
            "type_name": "Branch-wise / year-wise breakdowns",
            "question": "Company-wise hiring breakdown for Biotechnology in 2020-2024",
            "entities": {"companies": [], "branches": ["BT"], "years": ["2020-2024"]},
            "sql": "SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = 'BT' AND s.batch_id = '2020-2024' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY offers_count DESC;",
            "answer_type": "table",
            "notes": "BT hiring company breakdown."
        },
        {
            "id": "BREAKDOWN_06",
            "type_id": 3,
            "type_name": "Branch-wise / year-wise breakdowns",
            "question": "Year-wise average package for Computer Science and Engineering",
            "entities": {"companies": [], "branches": ["CSE"], "years": []},
            "sql": "SELECT s.batch_id, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = 'CSE' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;",
            "answer_type": "table",
            "notes": "CSE average CTC by batch."
        },
        {
            "id": "BREAKDOWN_07",
            "type_id": 3,
            "type_name": "Branch-wise / year-wise breakdowns",
            "question": "Branch-wise offers for Oracle across all years",
            "entities": {"companies": ["Oracle"], "branches": [], "years": []},
            "sql": "SELECT b.short_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Oracle' GROUP BY b.short_name ORDER BY offers_count DESC;",
            "answer_type": "table",
            "notes": "Oracle offers distributed by branch."
        },
        {
            "id": "BREAKDOWN_08",
            "type_id": 3,
            "type_name": "Branch-wise / year-wise breakdowns",
            "question": "Gender-wise placement count in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT s.gender, COUNT(DISTINCT s.student_id) AS placed_students FROM students s JOIN offers o ON s.student_id = o.student_id WHERE s.batch_id = '2020-2024' AND s.gender IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.gender ORDER BY placed_students DESC;",
            "answer_type": "table",
            "notes": "Gender distribution of placed students."
        },
        {
            "id": "BREAKDOWN_09",
            "type_id": 3,
            "type_name": "Branch-wise / year-wise breakdowns",
            "question": "Branch-wise count of double job offers in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT b.short_name, COUNT(*) AS double_offer_students FROM (SELECT s.student_id, s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2020-2024' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.student_id, s.branch_code HAVING COUNT(o.offer_id) >= 2) t JOIN branches b ON t.branch_code = b.branch_code GROUP BY b.short_name ORDER BY double_offer_students DESC;",
            "answer_type": "table",
            "notes": "Double offer holders per branch in 2020-2024."
        },
        {
            "id": "BREAKDOWN_10",
            "type_id": 3,
            "type_name": "Branch-wise / year-wise breakdowns",
            "question": "Sector-wise offers breakdown for 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT c.sector, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE s.batch_id = '2020-2024' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.sector ORDER BY offers_count DESC;",
            "answer_type": "table",
            "notes": "Offers by company sector."
        },

        # ==========================================
        # 4. RANKING / TOP-N (10 questions)
        # ==========================================
        {
            "id": "RANKING_01",
            "type_id": 4,
            "type_name": "Ranking / top-N",
            "question": "Top 5 companies by highest package",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT c.canonical_name, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY max_ctc DESC LIMIT 5;",
            "answer_type": "table",
            "notes": "Top 5 highest CTC recruiters."
        },
        {
            "id": "RANKING_02",
            "type_id": 4,
            "type_name": "Ranking / top-N",
            "question": "Which branch had the most offers above 20 LPA in 2020-2024 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT b.short_name, COUNT(o.offer_id) AS high_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE s.batch_id = '2020-2024' AND o.ctc_lpa > 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name ORDER BY high_offers DESC LIMIT 1;",
            "answer_type": "table",
            "notes": "Branch with most > 20 LPA offers."
        },
        {
            "id": "RANKING_03",
            "type_id": 4,
            "type_name": "Ranking / top-N",
            "question": "Top 3 recruiting companies by number of offers in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE s.batch_id = '2020-2024' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY offers_count DESC LIMIT 3;",
            "answer_type": "table",
            "notes": "Top 3 recruiters by volume."
        },
        {
            "id": "RANKING_04",
            "type_id": 4,
            "type_name": "Ranking / top-N",
            "question": "Top 5 branches by average CTC in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT b.short_name, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE s.batch_id = '2020-2024' AND b.degree = 'B.Tech' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name ORDER BY avg_ctc DESC LIMIT 5;",
            "answer_type": "table",
            "notes": "Top 5 B.Tech branches by average CTC."
        },
        {
            "id": "RANKING_05",
            "type_id": 4,
            "type_name": "Ranking / top-N",
            "question": "Top 3 companies that hired the most students from CSE",
            "entities": {"companies": [], "branches": ["CSE"], "years": []},
            "sql": "SELECT c.canonical_name, COUNT(DISTINCT s.student_id) AS hired_students FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = 'CSE' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY hired_students DESC LIMIT 3;",
            "answer_type": "table",
            "notes": "Top CSE recruiters."
        },
        {
            "id": "RANKING_06",
            "type_id": 4,
            "type_name": "Ranking / top-N",
            "question": "Which company made the highest package offer in ECE?",
            "entities": {"companies": [], "branches": ["ECE"], "years": []},
            "sql": "SELECT c.canonical_name, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = 'ECE' AND o.ctc_lpa IS NOT NULL GROUP BY c.canonical_name ORDER BY max_ctc DESC LIMIT 1;",
            "answer_type": "table",
            "notes": "Highest paying recruiter in ECE."
        },
        {
            "id": "RANKING_07",
            "type_id": 4,
            "type_name": "Ranking / top-N",
            "question": "Top 5 companies by number of PPO offers",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT c.canonical_name, COUNT(o.offer_id) AS ppo_count FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.offer_type IN ('PPO', 'Intern+PPO') GROUP BY c.canonical_name ORDER BY ppo_count DESC LIMIT 5;",
            "answer_type": "table",
            "notes": "Top PPO providers."
        },
        {
            "id": "RANKING_08",
            "type_id": 4,
            "type_name": "Ranking / top-N",
            "question": "Bottom 3 branches by placement percentage in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT branch_short, placement_pct FROM v_branch_year_stats WHERE batch_id = '2020-2024' ORDER BY placement_pct ASC LIMIT 3;",
            "answer_type": "table",
            "notes": "Lowest placement % branches in 2020-2024."
        },
        {
            "id": "RANKING_09",
            "type_id": 4,
            "type_name": "Ranking / top-N",
            "question": "Top 5 companies hiring from Mechanical Engineering",
            "entities": {"companies": [], "branches": ["ME"], "years": []},
            "sql": "SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = 'ME' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY offers_count DESC LIMIT 5;",
            "answer_type": "table",
            "notes": "Top ME recruiters."
        },
        {
            "id": "RANKING_10",
            "type_id": 4,
            "type_name": "Ranking / top-N",
            "question": "Top 3 highest paying companies in core branches",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT c.canonical_name, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.division = 'Core' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY max_ctc DESC LIMIT 3;",
            "answer_type": "table",
            "notes": "Top payers in Core engineering."
        },

        # ==========================================
        # 5. AGGREGATES WITH FILTERS (10 questions)
        # ==========================================
        {
            "id": "AGG_01",
            "type_id": 5,
            "type_name": "Aggregates with filters",
            "question": "Average CTC of CSE vs IT in 2020-2024 batch",
            "entities": {"companies": [], "branches": ["CSE", "IT"], "years": ["2020-2024"]},
            "sql": "SELECT b.short_name, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name IN ('CSE', 'IT') AND s.batch_id = '2020-2024' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name;",
            "answer_type": "table",
            "notes": "Comparison of average CTC between CSE and IT."
        },
        {
            "id": "AGG_02",
            "type_id": 5,
            "type_name": "Aggregates with filters",
            "question": "Median package of core companies in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "WITH ordered AS (SELECT o.ctc_lpa, ROW_NUMBER() OVER (ORDER BY o.ctc_lpa) AS r, COUNT(*) OVER () AS c FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.division = 'Core' AND s.batch_id = '2020-2024' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) SELECT ROUND(AVG(ctc_lpa), 2) AS median_ctc FROM ordered WHERE r IN ((c + 1) / 2, (c + 2) / 2);",
            "answer_type": "scalar",
            "notes": "Median CTC of Core branch offers."
        },
        {
            "id": "AGG_03",
            "type_id": 5,
            "type_name": "Aggregates with filters",
            "question": "Average package of female students in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT ROUND(AVG(o.ctc_lpa), 2) AS avg_female_ctc FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.gender = 'F' AND s.batch_id = '2020-2024' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Female average CTC."
        },
        {
            "id": "AGG_04",
            "type_id": 5,
            "type_name": "Aggregates with filters",
            "question": "Average CTC of circuit branches in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT ROUND(AVG(o.ctc_lpa), 2) AS avg_circuit_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.division = 'Circuit' AND s.batch_id = '2020-2024' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Circuit division average CTC."
        },
        {
            "id": "AGG_05",
            "type_id": 5,
            "type_name": "Aggregates with filters",
            "question": "Overall average package of NIT Jalandhar in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT ROUND(AVG(o.ctc_lpa), 2) AS overall_avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE s.batch_id = '2020-2024' AND b.degree = 'B.Tech' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "College-wide B.Tech average CTC."
        },
        {
            "id": "AGG_06",
            "type_id": 5,
            "type_name": "Aggregates with filters",
            "question": "Average package offered by Amazon across all students",
            "entities": {"companies": ["Amazon"], "branches": [], "years": []},
            "sql": "SELECT ROUND(AVG(o.ctc_lpa), 2) AS avg_amazon_ctc FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Amazon' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Amazon average CTC."
        },
        {
            "id": "AGG_07",
            "type_id": 5,
            "type_name": "Aggregates with filters",
            "question": "Average monthly stipend for summer internships in 2023-2027 batch",
            "entities": {"companies": [], "branches": [], "years": ["2023-2027"]},
            "sql": "SELECT ROUND(AVG(o.stipend_monthly_inr), 0) AS avg_stipend FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2023-2027' AND o.stipend_monthly_inr IS NOT NULL AND o.stipend_monthly_inr > 0;",
            "answer_type": "scalar",
            "notes": "Average summer intern stipend in INR."
        },
        {
            "id": "AGG_08",
            "type_id": 5,
            "type_name": "Aggregates with filters",
            "question": "Lowest package offered in Computer Science in 2020-2024 batch",
            "entities": {"companies": [], "branches": ["CSE"], "years": ["2020-2024"]},
            "sql": "SELECT MIN(o.ctc_lpa) AS min_cse_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = 'CSE' AND s.batch_id = '2020-2024' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Minimum package in CSE."
        },
        {
            "id": "AGG_09",
            "type_id": 5,
            "type_name": "Aggregates with filters",
            "question": "Average CTC of off-campus placements in 2021-2025 batch",
            "entities": {"companies": [], "branches": [], "years": ["2021-2025"]},
            "sql": "SELECT ROUND(AVG(o.ctc_lpa), 2) AS avg_offcampus_ctc FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2021-2025' AND o.offer_mode = 'Off-campus' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Off-campus average CTC."
        },
        {
            "id": "AGG_10",
            "type_id": 5,
            "type_name": "Aggregates with filters",
            "question": "Median package of Electronics and Communication in 2020-2024 batch",
            "entities": {"companies": [], "branches": ["ECE"], "years": ["2020-2024"]},
            "sql": "WITH ordered AS (SELECT o.ctc_lpa, ROW_NUMBER() OVER (ORDER BY o.ctc_lpa) AS r, COUNT(*) OVER () AS c FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = 'ECE' AND s.batch_id = '2020-2024' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) SELECT ROUND(AVG(ctc_lpa), 2) AS median_ece_ctc FROM ordered WHERE r IN ((c + 1) / 2, (c + 2) / 2);",
            "answer_type": "scalar",
            "notes": "Median CTC in ECE."
        },

        # ==========================================
        # 6. PERCENTAGES / RATIOS (10 questions)
        # ==========================================
        {
            "id": "PERCENT_01",
            "type_id": 6,
            "type_name": "Percentages / ratios",
            "question": "What percentage of CSE students got placed in 2020-2024 batch?",
            "entities": {"companies": [], "branches": ["CSE"], "years": ["2020-2024"]},
            "sql": "SELECT ROUND((COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) * 100.0) / COUNT(DISTINCT s.student_id), 2) AS cse_placement_pct FROM students s JOIN branches b ON s.branch_code = b.branch_code LEFT JOIN offers o ON s.student_id = o.student_id WHERE b.short_name = 'CSE' AND s.batch_id = '2020-2024';",
            "answer_type": "scalar",
            "notes": "CSE placement percentage in 2020-2024 (74.7%)."
        },
        {
            "id": "PERCENT_02",
            "type_id": 6,
            "type_name": "Percentages / ratios",
            "question": "What percentage of IT students got placed in 2020-2024 batch?",
            "entities": {"companies": [], "branches": ["IT"], "years": ["2020-2024"]},
            "sql": "SELECT ROUND((COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) * 100.0) / COUNT(DISTINCT s.student_id), 2) AS it_placement_pct FROM students s JOIN branches b ON s.branch_code = b.branch_code LEFT JOIN offers o ON s.student_id = o.student_id WHERE b.short_name = 'IT' AND s.batch_id = '2020-2024';",
            "answer_type": "scalar",
            "notes": "IT placement percentage in 2020-2024 (81.2%)."
        },
        {
            "id": "PERCENT_03",
            "type_id": 6,
            "type_name": "Percentages / ratios",
            "question": "Share of offers above 18 LPA per branch in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT b.short_name, ROUND((COUNT(CASE WHEN o.ctc_lpa >= 18.0 THEN 1 END) * 100.0) / COUNT(CASE WHEN o.ctc_lpa IS NOT NULL THEN 1 END), 2) AS share_above_18 FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE s.batch_id = '2020-2024' AND b.degree = 'B.Tech' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name HAVING COUNT(CASE WHEN o.ctc_lpa IS NOT NULL THEN 1 END) > 0 ORDER BY share_above_18 DESC;",
            "answer_type": "table",
            "notes": "Share of offers >= 18 LPA."
        },
        {
            "id": "PERCENT_04",
            "type_id": 6,
            "type_name": "Percentages / ratios",
            "question": "What percentage of offers in 2020-2024 batch were PPOs?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT ROUND((COUNT(CASE WHEN o.offer_type IN ('PPO', 'Intern+PPO') THEN 1 END) * 100.0) / COUNT(o.offer_id), 2) AS ppo_percentage FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2020-2024' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "PPO conversion percentage."
        },
        {
            "id": "PERCENT_05",
            "type_id": 6,
            "type_name": "Percentages / ratios",
            "question": "Placement percentage of Mechanical Engineering in 2020-2024 batch",
            "entities": {"companies": [], "branches": ["ME"], "years": ["2020-2024"]},
            "sql": "SELECT ROUND((COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) * 100.0) / COUNT(DISTINCT s.student_id), 2) AS me_placement_pct FROM students s JOIN branches b ON s.branch_code = b.branch_code LEFT JOIN offers o ON s.student_id = o.student_id WHERE b.short_name = 'ME' AND s.batch_id = '2020-2024';",
            "answer_type": "scalar",
            "notes": "Mechanical placement percentage."
        },
        {
            "id": "PERCENT_06",
            "type_id": 6,
            "type_name": "Percentages / ratios",
            "question": "What percentage of female students got placed in CSE in 2020-2024?",
            "entities": {"companies": [], "branches": ["CSE"], "years": ["2020-2024"]},
            "sql": "SELECT ROUND((COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) * 100.0) / COUNT(DISTINCT s.student_id), 2) AS female_cse_pct FROM students s JOIN branches b ON s.branch_code = b.branch_code LEFT JOIN offers o ON s.student_id = o.student_id WHERE b.short_name = 'CSE' AND s.batch_id = '2020-2024' AND s.gender = 'F';",
            "answer_type": "scalar",
            "notes": "Female CSE placement percentage."
        },
        {
            "id": "PERCENT_07",
            "type_id": 6,
            "type_name": "Percentages / ratios",
            "question": "What fraction of total B.Tech offers came from IT companies in 2020-2024 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT ROUND((COUNT(CASE WHEN c.sector = 'IT' THEN 1 END) * 100.0) / COUNT(o.offer_id), 2) AS it_sector_share FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE s.batch_id = '2020-2024' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "IT sector offer percentage."
        },
        {
            "id": "PERCENT_08",
            "type_id": 6,
            "type_name": "Percentages / ratios",
            "question": "Placement percentage of Civil Engineering in 2020-2024",
            "entities": {"companies": [], "branches": ["CE"], "years": ["2020-2024"]},
            "sql": "SELECT ROUND((COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) * 100.0) / COUNT(DISTINCT s.student_id), 2) AS ce_placement_pct FROM students s JOIN branches b ON s.branch_code = b.branch_code LEFT JOIN offers o ON s.student_id = o.student_id WHERE b.short_name = 'CE' AND s.batch_id = '2020-2024';",
            "answer_type": "scalar",
            "notes": "Civil placement percentage."
        },
        {
            "id": "PERCENT_09",
            "type_id": 6,
            "type_name": "Percentages / ratios",
            "question": "What percentage of placed students hold double offers in 2020-2024 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT ROUND((COUNT(CASE WHEN offer_count >= 2 THEN 1 END) * 100.0) / COUNT(*), 2) AS double_offer_ratio FROM (SELECT s.student_id, COUNT(o.offer_id) AS offer_count FROM students s JOIN offers o ON s.student_id = o.student_id WHERE s.batch_id = '2020-2024' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.student_id);",
            "answer_type": "scalar",
            "notes": "Ratio of double offers among placed students."
        },
        {
            "id": "PERCENT_10",
            "type_id": 6,
            "type_name": "Percentages / ratios",
            "question": "Share of offers with CTC >= 10 LPA in Mechanical Engineering in 2020-2024",
            "entities": {"companies": [], "branches": ["ME"], "years": ["2020-2024"]},
            "sql": "SELECT ROUND((COUNT(CASE WHEN o.ctc_lpa >= 10.0 THEN 1 END) * 100.0) / COUNT(CASE WHEN o.ctc_lpa IS NOT NULL THEN 1 END), 2) AS me_above_10_share FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = 'ME' AND s.batch_id = '2020-2024' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Share of offers >= 10 LPA in Mechanical."
        },

        # ==========================================
        # 7. TRENDS / COMPARISONS (10 questions)
        # ==========================================
        {
            "id": "TREND_01",
            "type_id": 7,
            "type_name": "Trends / comparisons",
            "question": "How did Microsoft package change over the batches?",
            "entities": {"companies": ["Microsoft"], "branches": [], "years": []},
            "sql": "SELECT s.batch_id, MAX(o.ctc_lpa) AS max_ctc, COUNT(o.offer_id) AS fte_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Microsoft' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;",
            "answer_type": "table",
            "notes": "Microsoft packages across batches."
        },
        {
            "id": "TREND_02",
            "type_id": 7,
            "type_name": "Trends / comparisons",
            "question": "Compare Amazon and Google hiring",
            "entities": {"companies": ["Amazon", "Google"], "branches": [], "years": []},
            "sql": "SELECT c.canonical_name, COUNT(DISTINCT s.student_id) AS placed_students, COUNT(o.offer_id) AS total_offers, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name IN ('Amazon', 'Google') AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name;",
            "answer_type": "table",
            "notes": "Amazon vs Google comparison."
        },
        {
            "id": "TREND_03",
            "type_id": 7,
            "type_name": "Trends / comparisons",
            "question": "Compare average package of CSE vs ECE in 2020-2024 batch",
            "entities": {"companies": [], "branches": ["CSE", "ECE"], "years": ["2020-2024"]},
            "sql": "SELECT b.short_name, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name IN ('CSE', 'ECE') AND s.batch_id = '2020-2024' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name;",
            "answer_type": "table",
            "notes": "CSE vs ECE comparison."
        },
        {
            "id": "TREND_04",
            "type_id": 7,
            "type_name": "Trends / comparisons",
            "question": "Compare placement percentage between 2020-2024 and 2021-2025 batches",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024", "2021-2025"]},
            "sql": "SELECT s.batch_id, COUNT(DISTINCT s.student_id) AS total_students, COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) AS placed_students, ROUND((COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) * 100.0) / COUNT(DISTINCT s.student_id), 2) AS placement_pct FROM students s LEFT JOIN offers o ON s.student_id = o.student_id WHERE s.batch_id IN ('2020-2024', '2021-2025') GROUP BY s.batch_id ORDER BY s.batch_id ASC;",
            "answer_type": "table",
            "notes": "Batch-to-batch placement percentage comparison."
        },
        {
            "id": "TREND_05",
            "type_id": 7,
            "type_name": "Trends / comparisons",
            "question": "How did average CTC in Mechanical Engineering trend over the years?",
            "entities": {"companies": [], "branches": ["ME"], "years": []},
            "sql": "SELECT s.batch_id, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = 'ME' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;",
            "answer_type": "table",
            "notes": "ME average package trend."
        },
        {
            "id": "TREND_06",
            "type_id": 7,
            "type_name": "Trends / comparisons",
            "question": "Compare Circuit vs Core branches average CTC in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT b.division, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE s.batch_id = '2020-2024' AND b.degree = 'B.Tech' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.division ORDER BY avg_ctc DESC;",
            "answer_type": "table",
            "notes": "Circuit vs Core division comparison."
        },
        {
            "id": "TREND_07",
            "type_id": 7,
            "type_name": "Trends / comparisons",
            "question": "Compare male vs female average package in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT s.gender, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc, COUNT(DISTINCT s.student_id) AS placed_count FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2020-2024' AND s.gender IN ('M', 'F') AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.gender;",
            "answer_type": "table",
            "notes": "Gender CTC comparison."
        },
        {
            "id": "TREND_08",
            "type_id": 7,
            "type_name": "Trends / comparisons",
            "question": "Compare Infosys and TCS hiring across all batches",
            "entities": {"companies": ["Infosys", "TCS"], "branches": [], "years": []},
            "sql": "SELECT c.canonical_name, COUNT(DISTINCT s.student_id) AS students_placed, COUNT(o.offer_id) AS total_offers, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name IN ('Infosys', 'TCS') AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name;",
            "answer_type": "table",
            "notes": "Infosys vs TCS hiring numbers."
        },
        {
            "id": "TREND_09",
            "type_id": 7,
            "type_name": "Trends / comparisons",
            "question": "How did highest package change between 2020-2024 and 2021-2025 batches?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024", "2021-2025"]},
            "sql": "SELECT s.batch_id, MAX(o.ctc_lpa) AS highest_package FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id IN ('2020-2024', '2021-2025') AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;",
            "answer_type": "table",
            "notes": "Highest package trend."
        },
        {
            "id": "TREND_10",
            "type_id": 7,
            "type_name": "Trends / comparisons",
            "question": "Compare number of offers in Chemical vs Civil in 2020-2024 batch",
            "entities": {"companies": [], "branches": ["CHE", "CE"], "years": ["2020-2024"]},
            "sql": "SELECT b.short_name, COUNT(o.offer_id) AS total_offers, COUNT(DISTINCT s.student_id) AS placed_students FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name IN ('CHE', 'CE') AND s.batch_id = '2020-2024' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name;",
            "answer_type": "table",
            "notes": "CHE vs CE comparison."
        },

        # ==========================================
        # 8. MULTI-CONDITION (10 questions)
        # ==========================================
        {
            "id": "MULTI_01",
            "type_id": 8,
            "type_name": "Multi-condition",
            "question": "Companies that hired both CSE and ECE with CTC > 15 LPA",
            "entities": {"companies": [], "branches": ["CSE", "ECE"], "years": []},
            "sql": "SELECT c.canonical_name FROM companies c JOIN offers o ON c.company_id = o.company_id JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE o.ctc_lpa > 15.0 AND b.short_name IN ('CSE', 'ECE') AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name HAVING COUNT(DISTINCT b.short_name) = 2 ORDER BY c.canonical_name ASC;",
            "answer_type": "list",
            "notes": "Companies hiring from both CSE and ECE at > 15 LPA."
        },
        {
            "id": "MULTI_02",
            "type_id": 8,
            "type_name": "Multi-condition",
            "question": "Companies that gave offers above 20 LPA in 2020-2024 batch to female students",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT DISTINCT c.canonical_name FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE s.batch_id = '2020-2024' AND s.gender = 'F' AND o.ctc_lpa > 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') ORDER BY c.canonical_name ASC;",
            "answer_type": "list",
            "notes": "Companies with >20 LPA female offers in 2020-2024."
        },
        {
            "id": "MULTI_03",
            "type_id": 8,
            "type_name": "Multi-condition",
            "question": "Students from Core branches who received packages >= 15 LPA in 2020-2024 batch",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT COUNT(DISTINCT s.student_id) AS core_super_students FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.division = 'Core' AND s.batch_id = '2020-2024' AND o.ctc_lpa >= 15.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Core students achieving >= 15 LPA."
        },
        {
            "id": "MULTI_04",
            "type_id": 8,
            "type_name": "Multi-condition",
            "question": "Companies that hired from both IT and Mechanical Engineering",
            "entities": {"companies": [], "branches": ["IT", "ME"], "years": []},
            "sql": "SELECT c.canonical_name FROM companies c JOIN offers o ON c.company_id = o.company_id JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name IN ('IT', 'ME') AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name HAVING COUNT(DISTINCT b.short_name) = 2 ORDER BY c.canonical_name ASC;",
            "answer_type": "list",
            "notes": "Companies hiring from both IT and ME."
        },
        {
            "id": "MULTI_05",
            "type_id": 8,
            "type_name": "Multi-condition",
            "question": "How many offers were made to SC/ST students with package >= 10 LPA in 2020-2024 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT COUNT(o.offer_id) AS sc_st_offers_above_10 FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2020-2024' AND s.category IN ('SC', 'ST') AND o.ctc_lpa >= 10.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "SC/ST offers >= 10 LPA."
        },
        {
            "id": "MULTI_06",
            "type_id": 8,
            "type_name": "Multi-condition",
            "question": "Companies that hired more than 5 students in CSE with package >= 10 LPA",
            "entities": {"companies": [], "branches": ["CSE"], "years": []},
            "sql": "SELECT c.canonical_name, COUNT(DISTINCT s.student_id) AS cse_hires FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = 'CSE' AND o.ctc_lpa >= 10.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name HAVING cse_hires > 5 ORDER BY cse_hires DESC;",
            "answer_type": "table",
            "notes": "Companies hiring >5 CSE students at >= 10 LPA."
        },
        {
            "id": "MULTI_07",
            "type_id": 8,
            "type_name": "Multi-condition",
            "question": "Which companies hired through PPO with package > 30 LPA?",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT DISTINCT c.canonical_name, MAX(o.ctc_lpa) AS max_ppo_ctc FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.offer_type IN ('PPO', 'Intern+PPO') AND o.ctc_lpa > 30.0 GROUP BY c.canonical_name ORDER BY max_ppo_ctc DESC;",
            "answer_type": "table",
            "notes": "Companies offering >30 LPA via PPO."
        },
        {
            "id": "MULTI_08",
            "type_id": 8,
            "type_name": "Multi-condition",
            "question": "Count of offers above 12 LPA in Textile Technology across all batches",
            "entities": {"companies": [], "branches": ["TT"], "years": []},
            "sql": "SELECT COUNT(o.offer_id) AS tt_above_12 FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = 'TT' AND o.ctc_lpa >= 12.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');",
            "answer_type": "scalar",
            "notes": "Offers >= 12 LPA in Textile Tech."
        },
        {
            "id": "MULTI_09",
            "type_id": 8,
            "type_name": "Multi-condition",
            "question": "Companies that hired in 2021-2025 batch with package >= 15 LPA and made at least 3 offers",
            "entities": {"companies": [], "branches": [], "years": ["2021-2025"]},
            "sql": "SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE s.batch_id = '2021-2025' AND o.ctc_lpa >= 15.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name HAVING offers_count >= 3 ORDER BY offers_count DESC;",
            "answer_type": "table",
            "notes": "Companies with >= 3 offers at >= 15 LPA in 2021-2025."
        },
        {
            "id": "MULTI_10",
            "type_id": 8,
            "type_name": "Multi-condition",
            "question": "Which companies hired both B.Tech and M.Tech students?",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT c.canonical_name FROM companies c JOIN offers o ON c.company_id = o.company_id JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name HAVING COUNT(DISTINCT CASE WHEN b.degree = 'B.Tech' THEN 1 END) > 0 AND COUNT(DISTINCT CASE WHEN b.degree = 'M.Tech' THEN 1 END) > 0 ORDER BY c.canonical_name ASC;",
            "answer_type": "list",
            "notes": "Companies hiring both UG and PG."
        },

        # ==========================================
        # 9. NEGATIVE / EXISTENCE (10 questions)
        # ==========================================
        {
            "id": "NEGATIVE_01",
            "type_id": 9,
            "type_name": "Negative / existence",
            "question": "Which branches were never hired by PayPal?",
            "entities": {"companies": ["PayPal"], "branches": [], "years": []},
            "sql": "SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'PayPal' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;",
            "answer_type": "list",
            "notes": "Branches never hired by PayPal (all except CSE)."
        },
        {
            "id": "NEGATIVE_02",
            "type_id": 9,
            "type_name": "Negative / existence",
            "question": "Which branches had zero offers above 20 LPA in 2020-2024 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2020-2024' AND o.ctc_lpa > 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;",
            "answer_type": "list",
            "notes": "Branches with zero offers > 20 LPA in 2020-2024."
        },
        {
            "id": "NEGATIVE_03",
            "type_id": 9,
            "type_name": "Negative / existence",
            "question": "Which B.Tech branches had zero female placements in 2020-2024 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2020-2024' AND s.gender = 'F' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;",
            "answer_type": "list",
            "notes": "Branches with zero female placements."
        },
        {
            "id": "NEGATIVE_04",
            "type_id": 9,
            "type_name": "Negative / existence",
            "question": "Which companies gave offers to CSE but never to IT?",
            "entities": {"companies": [], "branches": ["CSE", "IT"], "years": []},
            "sql": "SELECT DISTINCT c.canonical_name FROM companies c JOIN offers o ON c.company_id = o.company_id JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = 'CSE' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND c.company_id NOT IN (SELECT DISTINCT o2.company_id FROM offers o2 JOIN students s2 ON o2.student_id = s2.student_id JOIN branches b2 ON s2.branch_code = b2.branch_code WHERE b2.short_name = 'IT' AND o2.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY c.canonical_name ASC;",
            "answer_type": "list",
            "notes": "Companies hiring CSE but not IT."
        },
        {
            "id": "NEGATIVE_05",
            "type_id": 9,
            "type_name": "Negative / existence",
            "question": "Which branches were never hired by Uber?",
            "entities": {"companies": ["Uber"], "branches": [], "years": []},
            "sql": "SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Uber') ORDER BY b.short_name ASC;",
            "answer_type": "list",
            "notes": "Branches never hired by Uber."
        },
        {
            "id": "NEGATIVE_06",
            "type_id": 9,
            "type_name": "Negative / existence",
            "question": "Which core branches had no offers above 15 LPA in 2020-2024 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT b.short_name FROM branches b WHERE b.division = 'Core' AND b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2020-2024' AND o.ctc_lpa >= 15.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;",
            "answer_type": "list",
            "notes": "Core branches lacking >= 15 LPA offers."
        },
        {
            "id": "NEGATIVE_07",
            "type_id": 9,
            "type_name": "Negative / existence",
            "question": "How many students in 2020-2024 batch remained unplaced?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT COUNT(DISTINCT s.student_id) AS unplaced_count FROM students s JOIN branches b ON s.branch_code = b.branch_code WHERE s.batch_id = '2020-2024' AND b.degree = 'B.Tech' AND s.student_id NOT IN (SELECT DISTINCT o.student_id FROM offers o WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE'));",
            "answer_type": "scalar",
            "notes": "Unplaced B.Tech students in 2020-2024."
        },
        {
            "id": "NEGATIVE_08",
            "type_id": 9,
            "type_name": "Negative / existence",
            "question": "Which companies hired zero students from Information Technology?",
            "entities": {"companies": [], "branches": ["IT"], "years": []},
            "sql": "SELECT c.canonical_name FROM companies c WHERE c.company_id NOT IN (SELECT DISTINCT o.company_id FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = 'IT' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY c.canonical_name ASC LIMIT 10;",
            "answer_type": "list",
            "notes": "Companies that did not hire from IT."
        },
        {
            "id": "NEGATIVE_09",
            "type_id": 9,
            "type_name": "Negative / existence",
            "question": "Which branches had zero off-campus offers in 2020-2024 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2020-2024' AND o.offer_mode = 'Off-campus') ORDER BY b.short_name ASC;",
            "answer_type": "list",
            "notes": "Branches with zero off-campus offers."
        },
        {
            "id": "NEGATIVE_10",
            "type_id": 9,
            "type_name": "Negative / existence",
            "question": "Which companies never hired in 2020-2024 batch but hired in 2021-2025 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024", "2021-2025"]},
            "sql": "SELECT DISTINCT c.canonical_name FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE s.batch_id = '2021-2025' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND c.company_id NOT IN (SELECT DISTINCT o2.company_id FROM offers o2 JOIN students s2 ON o2.student_id = s2.student_id WHERE s2.batch_id = '2020-2024' AND o2.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY c.canonical_name ASC LIMIT 10;",
            "answer_type": "list",
            "notes": "New companies in 2021-2025 batch."
        },

        # ==========================================
        # 10. OFFER-TYPE AWARE (10 questions)
        # ==========================================
        {
            "id": "OFFERTYPE_01",
            "type_id": 10,
            "type_name": "Offer-type aware",
            "question": "How many PPOs were given by Amazon?",
            "entities": {"companies": ["Amazon"], "branches": [], "years": []},
            "sql": "SELECT COUNT(o.offer_id) AS amazon_ppos FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Amazon' AND o.offer_type IN ('PPO', 'Intern+PPO');",
            "answer_type": "scalar",
            "notes": "Amazon PPOs."
        },
        {
            "id": "OFFERTYPE_02",
            "type_id": 10,
            "type_name": "Offer-type aware",
            "question": "What is the internship stipend of Microsoft?",
            "entities": {"companies": ["Microsoft"], "branches": [], "years": []},
            "sql": "SELECT DISTINCT o.stipend_monthly_inr FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Microsoft' AND o.stipend_monthly_inr IS NOT NULL;",
            "answer_type": "number_list",
            "notes": "Microsoft internship stipend (125,000 INR/month)."
        },
        {
            "id": "OFFERTYPE_03",
            "type_id": 10,
            "type_name": "Offer-type aware",
            "question": "How many internship offers were made in 2023-2027 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2023-2027"]},
            "sql": "SELECT COUNT(o.offer_id) AS intern_offers FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2023-2027' AND o.offer_type IN ('Intern', 'Summer Intern');",
            "answer_type": "scalar",
            "notes": "2023-2027 summer internship count."
        },
        {
            "id": "OFFERTYPE_04",
            "type_id": 10,
            "type_name": "Offer-type aware",
            "question": "What is the difference between FTE offers and PPO offers in 2020-2024 batch?",
            "entities": {"companies": [], "branches": [], "years": ["2020-2024"]},
            "sql": "SELECT COUNT(CASE WHEN o.offer_type IN ('FTE', 'Intern+FTE') THEN 1 END) AS fte_count, COUNT(CASE WHEN o.offer_type IN ('PPO', 'Intern+PPO') THEN 1 END) AS ppo_count FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '2020-2024';",
            "answer_type": "table",
            "notes": "FTE vs PPO offers breakdown."
        },
        {
            "id": "OFFERTYPE_05",
            "type_id": 10,
            "type_name": "Offer-type aware",
            "question": "How many long intern offers were converted with full-time confirmation?",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT COUNT(o.offer_id) AS confirmed_long_interns FROM offers o WHERE o.offer_type = 'Intern+FTE';",
            "answer_type": "scalar",
            "notes": "Intern+FTE count."
        },
        {
            "id": "OFFERTYPE_06",
            "type_id": 10,
            "type_name": "Offer-type aware",
            "question": "What stipend was offered by American Express for summer internship?",
            "entities": {"companies": ["American Express"], "branches": [], "years": []},
            "sql": "SELECT DISTINCT o.stipend_monthly_inr FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'American Express' AND o.stipend_monthly_inr IS NOT NULL;",
            "answer_type": "number_list",
            "notes": "American Express monthly stipend: 125,000 INR."
        },
        {
            "id": "OFFERTYPE_07",
            "type_id": 10,
            "type_name": "Offer-type aware",
            "question": "Which companies offered unpaid internships?",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT DISTINCT c.canonical_name FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.package_reason = 'unpaid' ORDER BY c.canonical_name ASC;",
            "answer_type": "list",
            "notes": "Companies with unpaid internships."
        },
        {
            "id": "OFFERTYPE_08",
            "type_id": 10,
            "type_name": "Offer-type aware",
            "question": "How many offers had compound packages with both stipend and CTC?",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT COUNT(o.offer_id) AS compound_offers FROM offers o WHERE o.package_reason = 'compound_split';",
            "answer_type": "scalar",
            "notes": "Compound packages split."
        },
        {
            "id": "OFFERTYPE_09",
            "type_id": 10,
            "type_name": "Offer-type aware",
            "question": "How many PPOs did Reliance Industries give in Chemical Engineering?",
            "entities": {"companies": ["Reliance Industries"], "branches": ["CHE"], "years": []},
            "sql": "SELECT COUNT(o.offer_id) AS reliance_che_ppos FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Reliance Industries' AND b.short_name = 'CHE' AND o.offer_type IN ('PPO', 'Intern+PPO');",
            "answer_type": "scalar",
            "notes": "Reliance PPOs in CHE."
        },
        {
            "id": "OFFERTYPE_10",
            "type_id": 10,
            "type_name": "Offer-type aware",
            "question": "Top 3 companies by highest monthly internship stipend",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT c.canonical_name, MAX(o.stipend_monthly_inr) AS max_monthly_stipend FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.stipend_monthly_inr IS NOT NULL GROUP BY c.canonical_name ORDER BY max_monthly_stipend DESC LIMIT 3;",
            "answer_type": "table",
            "notes": "Highest paying internship companies."
        },

        # ==========================================
        # 11. HYBRID (SQL + RAG metadata) (10 questions)
        # ==========================================
        {
            "id": "HYBRID_01",
            "type_id": 11,
            "type_name": "Hybrid",
            "question": "Which companies gave > 18 LPA and what did they ask in interviews?",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT DISTINCT c.canonical_name FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.ctc_lpa > 18.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') ORDER BY c.canonical_name ASC;",
            "answer_type": "hybrid",
            "notes": "SQL extracts companies with CTC > 18 LPA; RAG retrieves alumni interview topics."
        },
        {
            "id": "HYBRID_02",
            "type_id": 11,
            "type_name": "Hybrid",
            "question": "What is the CTC of Microsoft for CSE and how was the technical round?",
            "entities": {"companies": ["Microsoft"], "branches": ["CSE"], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Microsoft' AND b.short_name = 'CSE' AND o.ctc_lpa IS NOT NULL;",
            "answer_type": "hybrid",
            "notes": "SQL retrieves 52.0 LPA; RAG retrieves Microsoft technical round experience."
        },
        {
            "id": "HYBRID_03",
            "type_id": 11,
            "type_name": "Hybrid",
            "question": "Which companies hired CSE with CTC >= 20 LPA and what projects did students discuss?",
            "entities": {"companies": [], "branches": ["CSE"], "years": []},
            "sql": "SELECT DISTINCT c.canonical_name FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = 'CSE' AND o.ctc_lpa >= 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') ORDER BY c.canonical_name ASC;",
            "answer_type": "hybrid",
            "notes": "SQL retrieves list of companies; RAG retrieves project details."
        },
        {
            "id": "HYBRID_04",
            "type_id": 11,
            "type_name": "Hybrid",
            "question": "Package offered by Google and what coding topics were asked?",
            "entities": {"companies": ["Google"], "branches": [], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Google' AND o.ctc_lpa IS NOT NULL ORDER BY o.ctc_lpa DESC;",
            "answer_type": "hybrid",
            "notes": "SQL provides CTC; RAG retrieves coding topics."
        },
        {
            "id": "HYBRID_05",
            "type_id": 11,
            "type_name": "Hybrid",
            "question": "How many offers did Amazon make and what was their online assessment like?",
            "entities": {"companies": ["Amazon"], "branches": [], "years": []},
            "sql": "SELECT COUNT(o.offer_id) AS amazon_offers FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Amazon';",
            "answer_type": "hybrid",
            "notes": "SQL provides offer counts; RAG provides OA details."
        },
        {
            "id": "HYBRID_06",
            "type_id": 11,
            "type_name": "Hybrid",
            "question": "Package of Uber and how many interview rounds did they conduct?",
            "entities": {"companies": ["Uber"], "branches": [], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Uber' AND o.ctc_lpa IS NOT NULL;",
            "answer_type": "hybrid",
            "notes": "SQL provides CTC (59.0 LPA); RAG provides interview rounds."
        },
        {
            "id": "HYBRID_07",
            "type_id": 11,
            "type_name": "Hybrid",
            "question": "What package did Goldman Sachs offer and what questions were asked in HR round?",
            "entities": {"companies": ["Goldman Sachs"], "branches": [], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Goldman Sachs' AND o.ctc_lpa IS NOT NULL;",
            "answer_type": "hybrid",
            "notes": "SQL provides CTC (24.0 LPA); RAG provides HR round questions."
        },
        {
            "id": "HYBRID_08",
            "type_id": 11,
            "type_name": "Hybrid",
            "question": "Which core companies hired with CTC > 10 LPA and what domain questions were asked?",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": "SELECT DISTINCT c.canonical_name FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.division = 'Core' AND o.ctc_lpa > 10.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') ORDER BY c.canonical_name ASC;",
            "answer_type": "hybrid",
            "notes": "SQL filters core recruiters >10 LPA; RAG retrieves technical domain questions."
        },
        {
            "id": "HYBRID_09",
            "type_id": 11,
            "type_name": "Hybrid",
            "question": "Package of Oracle and what SQL questions did they ask?",
            "entities": {"companies": ["Oracle"], "branches": [], "years": []},
            "sql": "SELECT DISTINCT o.ctc_lpa FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Oracle' AND o.ctc_lpa IS NOT NULL ORDER BY o.ctc_lpa DESC;",
            "answer_type": "hybrid",
            "notes": "SQL provides Oracle CTC; RAG provides SQL interview questions."
        },
        {
            "id": "HYBRID_10",
            "type_id": 11,
            "type_name": "Hybrid",
            "question": "What was the package for Cadence VLSI intern and how was the interview process?",
            "entities": {"companies": ["Cadence"], "branches": ["VLSI"], "years": []},
            "sql": "SELECT DISTINCT o.stipend_monthly_inr FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = 'Cadence' AND o.stipend_monthly_inr IS NOT NULL;",
            "answer_type": "hybrid",
            "notes": "SQL provides stipend; RAG provides VLSI interview process."
        },

        # ==========================================
        # 12. UNANSWERABLE / AMBIGUOUS (10 questions)
        # ==========================================
        {
            "id": "UNANSWERABLE_01",
            "type_id": 12,
            "type_name": "Unanswerable / ambiguous",
            "question": "What is the CTC of Apple?",
            "entities": {"companies": ["Apple"], "branches": [], "years": []},
            "sql": None,
            "answer_type": "unanswerable",
            "expected_behavior": "NO_DATA",
            "notes": "Apple never visited NIT Jalandhar in the dataset. Must report no data available."
        },
        {
            "id": "UNANSWERABLE_02",
            "type_id": 12,
            "type_name": "Unanswerable / ambiguous",
            "question": "What is the average CGPA of placed students in CSE?",
            "entities": {"companies": [], "branches": ["CSE"], "years": []},
            "sql": None,
            "answer_type": "unanswerable",
            "expected_behavior": "OUT_OF_SCOPE",
            "notes": "CGPA is not tracked in the placement spreadsheet. Must state CGPA data is unavailable."
        },
        {
            "id": "UNANSWERABLE_03",
            "type_id": 12,
            "type_name": "Unanswerable / ambiguous",
            "question": "Which company visited yesterday?",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": None,
            "answer_type": "unanswerable",
            "expected_behavior": "OUT_OF_SCOPE",
            "notes": "Relative temporal references ('yesterday') without batch context cannot be answered."
        },
        {
            "id": "UNANSWERABLE_04",
            "type_id": 12,
            "type_name": "Unanswerable / ambiguous",
            "question": "Tell me about placements",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": None,
            "answer_type": "ambiguous",
            "expected_behavior": "CLARIFICATION_REQUIRED",
            "notes": "Vague request without branch, year, or company. Must prompt for clarification."
        },
        {
            "id": "UNANSWERABLE_05",
            "type_id": 12,
            "type_name": "Unanswerable / ambiguous",
            "question": "What is the 10th and 12th board percentage requirement for Microsoft?",
            "entities": {"companies": ["Microsoft"], "branches": [], "years": []},
            "sql": None,
            "answer_type": "unanswerable",
            "expected_behavior": "OUT_OF_SCOPE",
            "notes": "School board percentages are not in the placement database."
        },
        {
            "id": "UNANSWERABLE_06",
            "type_id": 12,
            "type_name": "Unanswerable / ambiguous",
            "question": "Show me student roll numbers and phone numbers placed in Google",
            "entities": {"companies": ["Google"], "branches": [], "years": []},
            "sql": None,
            "answer_type": "unanswerable",
            "expected_behavior": "PRIVACY_BLOCKED",
            "notes": "Privacy policy strictly forbids disclosing individual student roll numbers or contacts."
        },
        {
            "id": "UNANSWERABLE_07",
            "type_id": 12,
            "type_name": "Unanswerable / ambiguous",
            "question": "What was the placement package in 2018?",
            "entities": {"companies": [], "branches": [], "years": ["2018"]},
            "sql": None,
            "answer_type": "unanswerable",
            "expected_behavior": "NO_DATA",
            "notes": "Data covers batches from 2020 onwards; 2018 is outside data scope."
        },
        {
            "id": "UNANSWERABLE_08",
            "type_id": 12,
            "type_name": "Unanswerable / ambiguous",
            "question": "Who is the HR contact for Amazon?",
            "entities": {"companies": ["Amazon"], "branches": [], "years": []},
            "sql": None,
            "answer_type": "unanswerable",
            "expected_behavior": "PRIVACY_BLOCKED",
            "notes": "HR contact sheet is strictly excluded from chatbot data."
        },
        {
            "id": "UNANSWERABLE_09",
            "type_id": 12,
            "type_name": "Unanswerable / ambiguous",
            "question": "How many offers were made to Aeronautical Engineering?",
            "entities": {"companies": [], "branches": ["Aeronautical Engineering"], "years": []},
            "sql": None,
            "answer_type": "unanswerable",
            "expected_behavior": "NO_DATA",
            "notes": "Aeronautical Engineering does not exist at NIT Jalandhar."
        },
        {
            "id": "UNANSWERABLE_10",
            "type_id": 12,
            "type_name": "Unanswerable / ambiguous",
            "question": "Which branch is the best?",
            "entities": {"companies": [], "branches": [], "years": []},
            "sql": None,
            "answer_type": "ambiguous",
            "expected_behavior": "CLARIFICATION_REQUIRED",
            "notes": "Subjective opinion without metric. Must ask clarifying question (highest package vs placement %)."
        }
    ]

    # Compute gold answers by executing SQL on data/nitj_placement.db
    verified_questions = []
    for q in raw_questions:
        q_copy = dict(q)
        sql = q_copy.get("sql")
        if sql:
            try:
                cur.execute(sql)
                rows = cur.fetchall()
                if q_copy["answer_type"] == "scalar":
                    q_copy["gold_answer"] = rows[0][0] if rows else None
                elif q_copy["answer_type"] == "number_list" or q_copy["answer_type"] == "list":
                    q_copy["gold_answer"] = [r[0] for r in rows]
                elif q_copy["answer_type"] == "table" or q_copy["answer_type"] == "hybrid":
                    # store list of dicts/tuples
                    col_names = [d[0] for d in cur.description]
                    q_copy["gold_columns"] = col_names
                    q_copy["gold_answer"] = [list(r) for r in rows]
            except Exception as e:
                print(f"Error executing SQL for {q_copy['id']}: {e}")
                q_copy["gold_answer"] = None
        else:
            q_copy["gold_answer"] = q_copy.get("expected_behavior", "UNANSWERABLE")

        verified_questions.append(q_copy)

    conn.close()

    # Save to eval/questions.json
    with open("eval/questions.json", "w", encoding="utf-8") as f:
        json.dump(verified_questions, f, indent=2)

    print(f"Successfully generated eval/questions.json with {len(verified_questions)} questions!")
    # Count per type
    type_counts = Counter([q["type_name"] for q in verified_questions])
    for tname, cnt in type_counts.items():
        print(f"  Type '{tname}': {cnt} questions")

if __name__ == "__main__":
    create_eval_dataset()
