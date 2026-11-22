import json

with open("eval/questions.json") as f:
    qs = json.load(f)

for q in qs:
    if q["id"] in ["NEGATIVE_08", "NEGATIVE_10"]:
        print("ID:", q["id"])
        print("Q:", q["question"])
        print("Gold SQL:", q.get("sql"))
        print("Gold Ans:", q.get("gold_answer"))

