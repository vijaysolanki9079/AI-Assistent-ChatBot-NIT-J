import json

with open("data/interview_experiences_structured.json", "r", encoding="utf-8") as f:
    exps = json.load(f)

print(f"Total structured experiences: {len(exps)}")
print("\nSample experience 1:")
print(json.dumps(exps[0], indent=2)[:600])

print("\nSample experience 2:")
print(json.dumps(exps[35], indent=2)[:600])

