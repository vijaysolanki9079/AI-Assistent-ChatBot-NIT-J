import sys
import os
sys.path.insert(0, os.path.abspath("."))

import json
from src.nlp.query_planner import QueryPlanner
from eval.run_eval import compare_results

planner = QueryPlanner()
with open("eval/questions.json") as f:
    questions = json.load(f)

print(f"Testing {len(questions)} standard evaluation questions...")
passed = 0
failed = 0
failures = []

for q in questions:
    q_id = q["id"]
    q_text = q["question"]
    gold_ans = q.get("gold_answer")
    ans_type = q.get("answer_type", "scalar")

    res = planner.plan_and_execute(q_text)
    cand_sql = res.get("sql")
    if res.get("category") in ["out_of_scope", "ambiguous", "privacy"]:
        cand_result = res.get("intent")
    else:
        exec_res = res.get("exec_result", {})
        rows = exec_res.get("rows", [])
        if ans_type == "scalar":
            cand_result = rows[0][0] if rows and rows[0] else None
        elif ans_type in ["number_list", "list"]:
            cand_result = [r[0] for r in rows]
        elif ans_type in ["table", "hybrid"]:
            cand_result = [list(r) for r in rows]
        else:
            cand_result = res.get("raw_result")

    if compare_results(cand_result, gold_ans, ans_type):
        passed += 1
    else:
        failed += 1
        failures.append({
            "id": q_id,
            "question": q_text,
            "gold": gold_ans,
            "cand": cand_result,
            "sql": cand_sql
        })

print(f"Standard Results: Passed={passed}, Failed={failed}, Accuracy={round(passed/len(questions)*100, 1)}%")
if failures:
    print(f"Sample failures (up to 3):")
    for f in failures[:3]:
        print(f)
