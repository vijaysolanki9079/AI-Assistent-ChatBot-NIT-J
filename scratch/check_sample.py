import json

data = json.load(open('eval/user_showcase_results.json', encoding='utf-8'))
sample_indices = [0, 1, 2, 8, 9, 10, 16, 24, 25, 30, 36, 45, 50, 56, 64, 73, 76, 83, 89, 93]
for idx in sample_indices:
    if idx < len(data):
        d = data[idx]
        print(f"=== [{idx+1}] {d['category']} ===")
        print(f"Q: {d['query']}")
        print(f"ANS: {d['answer']}")
        print()

