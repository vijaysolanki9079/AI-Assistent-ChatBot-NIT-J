"""
Evaluation Harness for NITJ Placement Assistant.
Runs evaluation questions from eval/questions.json, executes SQL queries against data/nitj_placement.db,
and generates detailed accuracy metrics per question type and failure logs.
"""

import json
import sqlite3
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

DB_PATH = "data/nitj_placement.db"
QUESTIONS_FILE = "eval/questions.json"
REPORT_OUTPUT = "eval/eval_report.md"

def normalize_val(val: Any) -> Any:
    """Normalize numeric, list, or string values for robust comparison."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    if isinstance(val, str):
        # try to parse as float
        try:
            return round(float(val), 2)
        except ValueError:
            return val.strip().lower()
    if isinstance(val, list):
        return [normalize_val(x) for x in val]
    return val

def compare_results(candidate: Any, gold: Any, answer_type: str) -> bool:
    """Compare candidate query output against gold answer."""
    if gold in ["NO_DATA", "OUT_OF_SCOPE", "CLARIFICATION_REQUIRED", "PRIVACY_BLOCKED", "UNANSWERABLE"]:
        if isinstance(candidate, str):
            return candidate.upper() == gold
        return False

    if candidate is None and gold is None:
        return True
    if candidate is None or gold is None:
        return False

    if answer_type == "scalar":
        cand_norm = normalize_val(candidate)
        gold_norm = normalize_val(gold)
        if isinstance(cand_norm, (int, float)) and isinstance(gold_norm, (int, float)):
            return abs(cand_norm - gold_norm) < 0.05
        return cand_norm == gold_norm

    elif answer_type in ["number_list", "list"]:
        if not isinstance(candidate, (list, tuple)) or not isinstance(gold, (list, tuple)):
            return False
        cand_norm = sorted([normalize_val(x) for x in candidate])
        gold_norm = sorted([normalize_val(x) for x in gold])
        return cand_norm == gold_norm

    elif answer_type in ["table", "hybrid"]:
        if not isinstance(candidate, (list, tuple)) or not isinstance(gold, (list, tuple)):
            return False
        if len(candidate) != len(gold):
            return False
        # Normalize rows
        cand_norm = [tuple(normalize_val(x) for x in row) if isinstance(row, (list, tuple)) else (normalize_val(row),) for row in candidate]
        gold_norm = [tuple(normalize_val(x) for x in row) if isinstance(row, (list, tuple)) else (normalize_val(row),) for row in gold]
        # Compare as sorted lists of tuples if order is not strict, or direct match
        return sorted(cand_norm) == sorted(gold_norm)

    return candidate == gold

def run_evaluation(questions_file: str = QUESTIONS_FILE, query_executor=None, set_name: str = "Standard") -> Dict[str, Any]:
    """
    Run evaluation across all questions in the specified question file.
    If query_executor is None, runs the gold_sql as baseline verification.
    Otherwise, passes question to query_executor(question_dict) -> (result, generated_sql).
    """
    if not os.path.exists(questions_file):
        print(f"Error: {questions_file} not found!")
        return {"total_questions": 0, "total_passed": 0, "overall_accuracy": 0.0}

    with open(questions_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    if not questions:
        print(f"\n=======================================================")
        print(f"EVALUATION: [{set_name.upper()} SET] (0 Questions - Empty)")
        print(f"=======================================================")
        print(f"File {questions_file} is currently empty. Add your test questions to evaluate.")
        if "heldout" in set_name.lower():
            print("Strict constraint enforced: Prompts and semantic rules are NEVER tuned on heldout questions.")
        print("=======================================================\n")
        return {"total_questions": 0, "total_passed": 0, "overall_accuracy": 0.0, "status": "EMPTY"}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    type_stats = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "failures": []})
    total_questions = len(questions)
    total_passed = 0

    print(f"\n=======================================================")
    print(f"RUNNING EVALUATION ON [{set_name.upper()} SET] ({total_questions} TEST QUESTIONS)")
    print(f"=======================================================\n")

    for q in questions:
        q_id = q["id"]
        q_type = q["type_name"]
        q_text = q["question"]
        gold_ans = q.get("gold_answer")
        ans_type = q.get("answer_type", "scalar")

        type_stats[q_type]["total"] += 1

        cand_result = None
        executed_sql = None
        error_msg = None

        if query_executor is not None:
            # Custom query generator (e.g. LLM / planner)
            try:
                cand_result, executed_sql = query_executor(q)
            except Exception as e:
                error_msg = str(e)
        else:
            # Baseline execution of gold_sql
            executed_sql = q.get("sql")
            if executed_sql:
                try:
                    cur.execute(executed_sql)
                    rows = cur.fetchall()
                    if ans_type == "scalar":
                        cand_result = rows[0][0] if rows else None
                    elif ans_type in ["number_list", "list"]:
                        cand_result = [r[0] for r in rows]
                    elif ans_type in ["table", "hybrid"]:
                        cand_result = [list(r) for r in rows]
                except Exception as e:
                    error_msg = str(e)
            else:
                cand_result = q.get("expected_behavior", "UNANSWERABLE")

        # Evaluate correctness
        is_pass = False
        if error_msg is None:
            is_pass = compare_results(cand_result, gold_ans, ans_type)

        if is_pass:
            total_passed += 1
            type_stats[q_type]["passed"] += 1
        else:
            type_stats[q_type]["failed"] += 1
            type_stats[q_type]["failures"].append({
                "id": q_id,
                "question": q_text,
                "gold_answer": gold_ans,
                "candidate_result": cand_result,
                "executed_sql": executed_sql,
                "error": error_msg
            })

    conn.close()

    overall_accuracy = (total_passed / total_questions) * 100.0

    # Print summary table
    print(f"{'Question Type':<40} | {'Total':<6} | {'Passed':<6} | {'Failed':<6} | {'Accuracy':<8}")
    print("-" * 75)
    for tname, stats in sorted(type_stats.items()):
        acc = (stats["passed"] / stats["total"]) * 100.0 if stats["total"] > 0 else 0.0
        print(f"{tname:<40} | {stats['total']:<6} | {stats['passed']:<6} | {stats['failed']:<6} | {acc:>6.1f}%")
    print("-" * 75)
    print(f"{'OVERALL TOTAL':<40} | {total_questions:<6} | {total_passed:<6} | {total_questions - total_passed:<6} | {overall_accuracy:>6.1f}%\n")

    # Generate Markdown Report
    report_lines = [
        "# NITJ Placement Assistant - Evaluation Report",
        "",
        f"- **Total Questions Evaluated**: {total_questions}",
        f"- **Total Passed**: {total_passed}",
        f"- **Total Failed**: {total_questions - total_passed}",
        f"- **Overall Accuracy**: **{overall_accuracy:.1f}%**",
        "",
        "## Accuracy by Question Type",
        "",
        "| Question Type | Total Questions | Passed | Failed | Accuracy Rate |",
        "|---|---|---|---|---|"
    ]

    for tname, stats in sorted(type_stats.items()):
        acc = (stats["passed"] / stats["total"]) * 100.0 if stats["total"] > 0 else 0.0
        report_lines.append(f"| {tname} | {stats['total']} | {stats['passed']} | {stats['failed']} | **{acc:.1f}%** |")

    report_lines.extend([
        "",
        "## Summary of Question Types Covered",
        "1. **Lookup**: Direct company CTC / stipend lookups by branch and role.",
        "2. **Count by condition**: Offers and placed student counts under specific criteria.",
        "3. **Branch-wise / year-wise breakdowns**: Multi-row cross-tabulations and category distributions.",
        "4. **Ranking / top-N**: Highest paying companies, top branches by offers, top recruiters.",
        "5. **Aggregates with filters**: Average CTC, median package (via window functions), min/max stats.",
        "6. **Percentages / ratios**: Placement percentages, share of offers above thresholds, double offer rates.",
        "7. **Trends / comparisons**: Cohort comparisons, company comparisons (Amazon vs Google, Infosys vs TCS).",
        "8. **Multi-condition**: Joint branch queries (CSE + ECE), demographic filters, threshold cuts.",
        "9. **Negative / existence**: Zero offer branches (PayPal, Uber), unplaced student counts.",
        "10. **Offer-type aware**: Strict segregation of PPOs, FTEs, 6-month interns, summer stipends.",
        "11. **Hybrid**: Relational company/package query coupled with interview round metadata.",
        "12. **Unanswerable / ambiguous**: Non-existent entities (Apple), missing dimensions (CGPA), vague queries."
    ])

    with open(REPORT_OUTPUT, "w", encoding="utf-8") as out:
        out.write("\n".join(report_lines))

    print(f"Detailed evaluation report saved to {REPORT_OUTPUT}")

    return {
        "total_questions": total_questions,
        "total_passed": total_passed,
        "overall_accuracy": overall_accuracy,
        "type_stats": dict(type_stats)
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NITJ Placement Assistant Evaluation Suite")
    parser.add_argument("--set", choices=["standard", "fuzzed", "heldout"], default="standard",
                        help="Which test set to evaluate (standard, fuzzed, or heldout)")
    parser.add_argument("--all", action="store_true", help="Run evaluations on all test sets and report separately")

    args = parser.parse_args()

    # Import evaluator modules
    from eval.fuzz import evaluate_fuzzed_suite, evaluate_heldout_suite

    if args.all:
        print("\n" + "=" * 60)
        print("COMPREHENSIVE MULTI-SET EVALUATION REPORT")
        print("=" * 60)
        # 1. Standard
        res_std = run_evaluation(QUESTIONS_FILE, set_name="Standard (120 Gold Questions)")
        # 2. Fuzzed
        res_fuzz = evaluate_fuzzed_suite()
        # 3. Heldout
        res_held = evaluate_heldout_suite()

        print("\n" + "=" * 60)
        print("CONSOLIDATED SCORECARD")
        print("=" * 60)
        print(f"1. Standard Test Set : {res_std.get('total_passed', 0)}/{res_std.get('total_questions', 0)} ({res_std.get('overall_accuracy', 0.0):.1f}%)")
        print(f"2. Fuzzed Test Set   : {res_fuzz.get('passed', 0)}/{res_fuzz.get('total', 0)} ({res_fuzz.get('accuracy', 0.0):.1f}%)")
        if res_held.get("total", 0) > 0:
            print(f"3. Heldout Test Set  : {res_held.get('passed', 0)}/{res_held.get('total', 0)} ({res_held.get('accuracy', 0.0):.1f}%)")
        else:
            print(f"3. Heldout Test Set  : Empty (0 questions in eval/heldout.json) - Waiting for user input")
        print("=" * 60)
        print("Strict policy enforced: Never tune prompts or rules on heldout questions.\n")

    elif args.set == "fuzzed":
        evaluate_fuzzed_suite()
    elif args.set == "heldout":
        evaluate_heldout_suite()
    else:
        run_evaluation(QUESTIONS_FILE, set_name="Standard")

