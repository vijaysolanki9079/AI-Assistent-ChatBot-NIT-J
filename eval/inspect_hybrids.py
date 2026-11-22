import json

with open("eval/questions_dev.json", encoding="utf-8") as f:
    dev_qs = json.load(f)

hybrids = [q for q in dev_qs if q.get("category") == "Hybrid"]
for q in hybrids:
    print(f"[{q['id']}] Q: {q['question']}")
    print(f"    Gold: {q.get('gold')}")
    print(f"    Notes: {q.get('notes')}\n")

