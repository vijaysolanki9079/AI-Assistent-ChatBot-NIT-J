import json

with open('eval/questions.json') as f:
    qs = json.load(f)

types = {}
for q in qs:
    t = q['type_name']
    types.setdefault(t, []).append(q)

print(f'Total categories: {len(types)}')
for t, items in types.items():
    print(f'- {t}: {len(items)} questions (e.g. "{items[0]["question"]}")')

