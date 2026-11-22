import json

with open("eval/user_showcase_results.json", encoding="utf-8") as f:
    results = json.load(f)

for r in results:
    cat = r["category"]
    q = r["query"]
    ans = r["answer"].replace("\n", " ").strip()
    sql = r["sql"]
    print(f"[{cat}] Q: \"{q}\"")
    print(f"   A: {ans[:150]}...")
    if r["citations"]:
        print(f"   Citations: {len(r['citations'])}")
    print()

