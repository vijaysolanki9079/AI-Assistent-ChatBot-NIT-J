import sys, os
sys.path.insert(0, os.path.abspath("."))
import importlib.util
import json

spec = importlib.util.spec_from_file_location("run_eval", "eval/run_eval.py")
run_eval_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_eval_mod)
run_evaluation = run_eval_mod.run_evaluation
from src.nlp.query_planner import QueryPlanner

planner = QueryPlanner()

with open("eval/questions.json", "r", encoding="utf-8") as f:
    q_all = {q["id"]: q for q in json.load(f)}

def evaluate_planner(q_dict):
    q_text = q_dict["question"]
    ans_type = q_dict.get("answer_type", "scalar")
    res = planner.plan_and_execute(q_text)
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

results = run_evaluation(query_executor=evaluate_planner)

os.makedirs("eval", exist_ok=True)
with open("eval/failures_detailed.txt", "w", encoding="utf-8") as out:
    for q_type, stats in sorted(results["type_stats"].items()):
        if stats["failed"] > 0:
            out.write(f"\n=======================================================\n")
            out.write(f"=== {q_type} ({stats['failed']} failed) ===\n")
            out.write(f"=======================================================\n")
            for f in stats["failures"]:
                qid = f["id"]
                gold_q = q_all.get(qid, {})
                out.write(f"\n[{qid}] {f['question']}\n")
                out.write(f"  Gold Answer: {f['gold_answer']}\n")
                out.write(f"  Cand Answer: {f['candidate_result']}\n")
                out.write(f"  Gold SQL:    {gold_q.get('sql')}\n")
                out.write(f"  Cand SQL:    {f['executed_sql']}\n")
                if f.get('error'):
                    out.write(f"  Error:       {f['error']}\n")

print("Saved detailed failures to scratch/failures_detailed.txt")
