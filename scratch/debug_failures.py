import sys
import os
sys.path.insert(0, os.path.abspath("."))
import json
from src.nlp.query_planner import QueryPlanner

planner = QueryPlanner()
q1 = 'Branch-wise placed students count in 2020-2024 batch'
spec1 = planner.llm_parser.parse(q1)
print("Q1:", q1)
print("Spec1:", spec1.model_dump())

q2 = 'Year-wise average package for Computer Science and Engineering'
spec2 = planner.llm_parser.parse(q2)
print("\nQ2:", q2)
print("Spec2:", spec2.model_dump())

