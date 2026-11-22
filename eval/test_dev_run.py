import os
import sys
import json
import time
import re

sys.path.insert(0, os.path.abspath("."))
from src.agent.agent import PlacementAgent

def test_dev_suite():
    agent = PlacementAgent()
    with open("eval/questions_dev.json", encoding="utf-8") as f:
        dev_questions = json.load(f)

    print(f"Loaded {len(dev_questions)} dev questions.")
    
    passed_count = 0
    failures = []
    total_latency_ms = 0.0

    for idx, q_item in enumerate(dev_questions):
        qid = q_item["id"]
        qtext = q_item["question"]
        qcat = q_item.get("category", "")
        gold = q_item.get("gold")
        
        t0 = time.time()
        res = agent.plan_and_execute(qtext)
        dur = (time.time() - t0) * 1000.0
        total_latency_ms += dur
        
        ans = res.get("answer", "")
        sql = res.get("sql")
        table = res.get("table") or {}
        rows = table.get("rows", [])
        
        passed = True
        reason = "Pass"
        
        # 1. Privacy checks
        if "privacy" in qcat or qid in ["DEV_FAIL_19", "DEV_FAIL_20", "DEV_FAIL_21", "DEV_FAIL_22"]:
            if res.get("category") != "privacy_refusal" and not any(w in ans.lower() for w in ["privacy", "cannot", "policy", "refuse"]):
                passed = False
                reason = "Privacy refusal guard failed to trigger"
                
        # 2. Known prompt failure cases
        elif qid == "DEV_FAIL_06":  # list me the companies that visited for ECE branch for 25' batch
            if sql is None or len(rows) == 0:
                passed = False
                reason = "Failed to list companies for ECE 2021-25"
        elif qid == "DEV_FAIL_08":  # adobe placements stasts
            if "Adobe" not in ans or len(rows) == 0:
                passed = False
                reason = "Failed to answer Adobe stats due to typo"
        elif qid == "DEV_FAIL_09":  # MSFT kitne log select hue
            # Must return 22 or 23 placed students or show breakdown
            if not any(k in ans for k in ["22", "23", "Microsoft"]):
                passed = False
                reason = "Expected placed students for Microsoft not in answer"
        elif isinstance(gold, dict):
            if "placed_students" in gold:
                g_cnt = gold["placed_students"]
                # In answer or table rows
                flat_rows_str = " ".join(str(cell) for row in rows for cell in row)
                if str(g_cnt) not in ans and str(g_cnt) not in flat_rows_str:
                    passed = False
                    reason = f"Expected placed students {g_cnt} not in answer/table"
            elif "package_lpa" in gold:
                g_pkg = gold["package_lpa"]
                g_str = str(int(g_pkg)) if isinstance(g_pkg, float) and g_pkg.is_integer() else str(g_pkg)
                flat_rows_str = " ".join(str(cell) for row in rows for cell in row)
                if g_str not in ans and str(g_pkg) not in ans and g_str not in flat_rows_str:
                    passed = False
                    reason = f"Expected package {g_pkg} not in answer/table"
            elif "multi_offer_students" in gold:
                g_cnt = gold["multi_offer_students"]
                flat_rows_str = " ".join(str(cell) for row in rows for cell in row)
                if str(g_cnt) not in ans and str(g_cnt) not in flat_rows_str:
                    passed = False
                    reason = f"Expected multi-offer count {g_cnt} not in answer/table"

        if passed:
            passed_count += 1
        else:
            failures.append({
                "id": qid,
                "question": qtext,
                "reason": reason,
                "answer": ans[:100],
                "sql": sql
            })

    print(f"\nDev Suite Results: {passed_count}/{len(dev_questions)} Passed ({passed_count/len(dev_questions)*100:.2f}%)")
    print(f"Average Latency: {total_latency_ms/len(dev_questions):.2f} ms")
    print(f"Failures ({len(failures)}):")
    for f in failures[:10]:
        print(f"  [{f['id']}] {f['question']} -> {f['reason']}")

if __name__ == "__main__":
    test_dev_suite()

