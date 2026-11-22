import sys, os
sys.path.insert(0, os.path.abspath("."))
from src.nlp.query_planner import QueryPlanner

planner = QueryPlanner()

questions = [
    "how many ppl got selected in MS bacth wise",
    "What is the CTC of Microsoft for CSE?",
    "What package does Zomato offer for Chemical Engineering?",
    "Compare Infosys and TCS hiring across all batches",
    "How many total offers were given to Mechanical Engineering students?"
]

for q in questions:
    res = planner.plan_and_execute(q)
    md = planner.render_markdown(res)
    print(f"\n=======================================================")
    print(f"QUESTION: {q}")
    print(f"=======================================================")
    print("RENDERED CHAT OUTPUT:")
    print(md)

