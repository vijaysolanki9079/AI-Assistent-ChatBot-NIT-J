import sys
sys.path.insert(0, ".")
from src.nlp.query_planner import QueryPlanner

planner = QueryPlanner()
queries = [
    'adobe placements stats',
    'adobe placement stats',
    'stats of adobe',
    'adobe placement',
    'adobe stats',
    'placement stats of adobe',
    'what are the placement stats of adobe',
    'adobe placements'
]
for q in queries:
    res = planner.plan_and_execute(q)
    print(f"Q: {q}")
    print(f"   Spec: {res.get('query_spec')}")
    print(f"   SQL: {res.get('sql')}")
    print(f"   Answer: {res.get('answer')}")
    print("-" * 50)

