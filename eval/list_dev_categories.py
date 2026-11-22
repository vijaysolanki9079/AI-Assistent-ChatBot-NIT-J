import json

with open("eval/questions_dev.json", encoding="utf-8") as f:
    dev_qs = json.load(f)

categories = set(q.get("category", "") for q in dev_qs)
print("Categories:", categories)

for cat in sorted(categories):
    matching = [q for q in dev_qs if q.get("category") == cat]
    print(f"  {cat}: {len(matching)} questions")

