import json
from collections import defaultdict

data = json.load(open('eval/user_showcase_results.json', encoding='utf-8'))
cats = defaultdict(list)
for d in data:
    cats[d['category']].append(d)

out = ["# Benchmark Showcase: Model Output Across All 14 Test Categories\n"]
out.append("This document contains the exact model responses, SQL queries, and tool grounding for all 99 questions across the 14 stress-test categories.\n")

for cat in sorted(cats.keys(), key=lambda x: int(x.split('.')[0])):
    out.append(f"## {cat} ({len(cats[cat])} queries)\n")
    for d in cats[cat]:
        out.append(f"**Q: \"{d['query']}\"**")
        ans = d['answer'].replace("\n", "\n> ")
        out.append(f"> {ans}\n")
        if d.get('sql'):
            clean_sql = " ".join(d['sql'].split())
            out.append(f"*SQL*: `{clean_sql}`  \n")
        if d.get('citations'):
            cites = ", ".join(f"{c['company']} ({c['source']})" for c in d['citations'])
            out.append(f"*Citations*: {cites}  \n")
        out.append("\n---\n")

with open('reports/user_showcase_answers.md', 'w', encoding='utf-8') as f:
    f.write("\n".join(out))

print("Successfully written reports/user_showcase_answers.md")
