import sys, os
sys.path.insert(0, os.path.abspath("."))
import importlib.util
spec = importlib.util.spec_from_file_location("run_eval", "eval/run_eval.py")
run_eval_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_eval_mod)
run_evaluation = run_eval_mod.run_evaluation
from src.nlp.query_planner import QueryPlanner

planner = QueryPlanner()

def evaluate_planner(q_dict):
    q_text = q_dict["question"]
    ans_type = q_dict.get("answer_type", "scalar")
    res = planner.plan_and_execute(q_text)
    # If unanswerable / ambiguous, return intent
    if res.get("category") in ["out_of_scope", "ambiguous"]:
        return res.get("intent"), None

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

    return cand_result, res.get("sql")

if __name__ == "__main__":
    print("Testing QueryPlanner with run_evaluation...")
    results = run_evaluation(query_executor=evaluate_planner)
