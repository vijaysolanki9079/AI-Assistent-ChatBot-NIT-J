import sys
import os
sys.path.insert(0, os.path.abspath("."))
import json
from src.nlp.query_planner import QueryPlanner
from eval.run_eval import compare_results

planner = QueryPlanner()
with open("eval/questions.json") as f:
    questions = json.load(f)

failures = []
for q in questions:
    q_id = q["id"]
    q_type = q["type_name"]
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

    if not compare_results(cand_result, gold_ans, ans_type):
        failures.append({
            "id": q_id,
            "type": q_type,
            "q": q_text,
            "gold": gold_ans,
            "cand": cand_result,
            "sql": cand_sql
        })

print(f"Total failures: {len(failures)}")
for f in failures:
    print(f"[{f['id']}] ({f['type']}): {f['q']}")
    print(f"   Gold: {f['gold']}")
    print(f"   Cand: {f['cand']}")
    print(f"   SQL : {f['sql']}")

