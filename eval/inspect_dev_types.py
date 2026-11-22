import json

with open("eval/questions_dev.json", encoding="utf-8") as f:
    dev_qs = json.load(f)

types = set()
for q in dev_qs:
    types.add(q.get("type", "unknown"))

print("Types in dev_qs:", types)
for q in dev_qs[:10]:
    print(q["id"], q.get("type"), q["question"][:50])

