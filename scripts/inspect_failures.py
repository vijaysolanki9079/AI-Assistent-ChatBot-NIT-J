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
    res = planner.plan_and_execute(q_text)
    if res.get("category") in ["out_of_scope", "ambiguous"]:
        return res.get("intent"), None
    return res.get("raw_result"), res.get("sql")

results = run_evaluation(query_executor=evaluate_planner)
for q_type, stats in sorted(results["type_stats"].items()):
    if stats["failed"] > 0:
        print(f"\n=== {q_type} ({stats['failed']} failed) ===")
        for f in stats["failures"]:
            print(f"[{f['id']}] Q: {f['question']}")
            print(f"  Gold: {f['gold_answer']}")
            print(f"  Cand: {f['candidate_result']}")
            print(f"  SQL:  {f['executed_sql']}")
            if f.get('error'):
                print(f"  Err:  {f['error']}")
