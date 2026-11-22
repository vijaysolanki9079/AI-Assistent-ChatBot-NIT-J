import sys
import os
sys.path.insert(0, os.path.abspath("."))
import json
from src.nlp.query_planner import QueryPlanner

planner = QueryPlanner()
q1 = "Which branch had the most offers above 20 LPA in 2020-2024 batch?"
spec1 = planner.llm_parser.parse(q1)
print("Q1 spec:", spec1.model_dump())

q2 = "Top 5 branches by average CTC in 2020-2024 batch"
spec2 = planner.llm_parser.parse(q2)
print("Q2 spec:", spec2.model_dump())

q3 = "Which B.Tech branches had zero female placements in 2020-2024 batch?"
spec3 = planner.llm_parser.parse(q3)
print("Q3 spec:", spec3.model_dump())

