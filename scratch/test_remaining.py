import sys
import os
sys.path.insert(0, os.path.abspath("."))
from src.nlp.query_planner import QueryPlanner

planner = QueryPlanner()
qs = [
    "Which companies hired both B.Tech and M.Tech students?",
    "How many long intern offers were converted with full-time confirmation?",
    "Which companies offered unpaid internships?",
    "How many offers had compound packages with both stipend and CTC?",
    "Which companies hired zero students from Information Technology?",
    "Which companies never hired in 2020-2024 batch but hired in 2021-2025 batch?"
]

for q in qs:
    spec = planner.llm_parser.parse(q)
    print("Q:", q)
    print("  Spec:", spec.intent, spec.metric, spec.companies, spec.branches, spec.batches, spec.needs_clarification, spec.confidence)
    res = planner.plan_and_execute(q)
    print("  Res :", res.get("intent"), res.get("category"), res.get("sql") is not None)

