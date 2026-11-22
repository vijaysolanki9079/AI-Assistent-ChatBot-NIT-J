import json

with open("eval/questions_dev.json", encoding="utf-8") as f:
    dev_qs = json.load(f)

print("Keys in question 0:", list(dev_qs[0].keys()))
for i, q in enumerate(dev_qs):
    if any(k in q["question"].lower() for k in ["interview", "round", "experience", "prepare", "tips", "dsa", "oa"]):
        print(f"[{q['id']}] Q: {q['question']}")

