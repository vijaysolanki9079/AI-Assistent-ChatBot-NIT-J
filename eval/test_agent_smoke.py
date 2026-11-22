import sys
import os
import json

sys.path.insert(0, os.path.abspath("."))
from src.agent.agent import PlacementAgent

def run_smoke_test():
    agent = PlacementAgent()
    print("=== Running Agent Smoke Test (Phase 4) ===\n")

    test_cases = [
        {
            "type": "1. Lookup",
            "query": "What is Microsoft's package?",
            "check": lambda res: "Microsoft" in res.get("answer", "") and "52" in res.get("answer", "")
        },
        {
            "type": "2. Count",
            "query": "How many students got placed in Amazon?",
            "check": lambda res: res.get("table") is not None and "placed" in res.get("answer", "").lower()
        },
        {
            "type": "3. Branch-wide",
            "query": "list me the companies that visited for ECE branch for 25' batch",
            "check": lambda res: res.get("table") is not None and len(res["table"]["rows"]) > 0
        },
        {
            "type": "4. RAG / Qualitative",
            "query": "What is the CTC of Microsoft for CSE and how was the technical round?",
            "check": lambda res: len(res.get("citations", [])) > 0 and "Microsoft" in res.get("answer", "")
        },
        {
            "type": "5. Privacy Refusal",
            "query": "Give me the phone numbers and roll numbers of students who got Google",
            "check": lambda res: res.get("category") == "privacy_refusal" and "privacy" in res.get("answer", "").lower()
        }
    ]

    all_passed = True
    results_summary = []

    for tc in test_cases:
        ttype = tc["type"]
        q = tc["query"]
        print(f"--- [{ttype}] Q: \"{q}\" ---")
        res = agent.plan_and_execute(q)
        ans = res.get("answer", "")
        sql = res.get("sql")
        cit = res.get("citations", [])
        cat = res.get("category")
        
        print(f"Category: {cat}")
        if sql:
            print(f"Generated SQL:\n{sql.strip()}")
        print(f"Answer:\n{ans}")
        if cit:
            print(f"Citations ({len(cit)}): {[c['title'] for c in cit]}")
        if res.get("table"):
            cols = res["table"]["columns"]
            row_cnt = len(res["table"]["rows"])
            print(f"Table: {row_cnt} rows with columns {cols}")
            
        passed = tc["check"](res)
        print(f"Status: {'PASSED' if passed else 'FAILED'}\n")
        if not passed:
            all_passed = False
            
        results_summary.append({
            "type": ttype,
            "query": q,
            "category": cat,
            "has_sql": bool(sql),
            "has_citations": len(cit) > 0,
            "status": "PASSED" if passed else "FAILED"
        })

    print("========================================")
    print(f"Agent Smoke Test Summary: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    for r in results_summary:
        print(f"  {r['type']}: {r['status']} (Category: {r['category']})")
    print("========================================")

    return all_passed

if __name__ == "__main__":
    success = run_smoke_test()
    if not success:
        sys.exit(1)

