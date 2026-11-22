import json

with open("eval/questions.json") as f:
    qs = json.load(f)

for q in qs:
    if q.get("type_name") == "Branch-wise / year-wise breakdowns":
        print(f"ID: {q['id']}")
        print(f"  Q: {q['question']}")
        print(f"  SQL: {q.get('sql')}")

