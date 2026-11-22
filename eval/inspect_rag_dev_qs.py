import json

with open("eval/questions_dev.json", encoding="utf-8") as f:
    dev_qs = json.load(f)

rag_qs = [q for q in dev_qs if q.get("type") == "rag" or "interview" in q.get("id", "").lower() or "rag" in q.get("id", "").lower()]
print(f"Found {len(rag_qs)} RAG questions in questions_dev.json:")
for q in rag_qs:
    print(f"ID: {q['id']} | Q: {q['question']}")
    print(f"  Gold answer/details: {q.get('gold_answer') or q.get('gold')}")

