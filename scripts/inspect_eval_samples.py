import json

with open("eval/questions.json") as f:
    questions = json.load(f)

print(f"Total questions: {len(questions)}")
# Let's inspect questions by type
by_type = {}
for q in questions:
    by_type.setdefault(q["type_name"], []).append(q)

for tname, qlist in by_type.items():
    print(f"\n--- {tname} (Sample 3) ---")
    for q in qlist[:3]:
        print(f"  [{q['id']}] {q['question']}")
        print(f"    Entities: {q['entities']}")
        print(f"    SQL: {q.get('sql')[:80]}...")

