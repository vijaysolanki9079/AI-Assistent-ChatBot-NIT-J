import sys, os, time, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.rag.retriever import ExperienceRetriever

retriever = ExperienceRetriever()

with open("eval/questions_dev.json", encoding="utf-8") as f:
    dev_qs = json.load(f)

hybrids = [q for q in dev_qs if q.get("category") == "Hybrid"]

print(f"Testing {len(hybrids)} Hybrid / RAG questions:\n")
for q in hybrids:
    qid = q["id"]
    query = q["question"]
    
    t0 = time.time()
    # If the question mentions specific companies, extract them or pass query
    results = retriever.search(query=query, top_k=3)
    latency_ms = (time.time() - t0) * 1000.0
    
    print(f"[{qid}] Q: {query}")
    print(f"  Latency: {latency_ms:.2f}ms | Hits: {len(results)}")
    for i, r in enumerate(results):
        print(f"    Hit {i+1}: [{r['company']}] {r['title']} (ID: {r['experience_id'][:12]}...)")
        print(f"           Topics: {r['technical_topics']}")
        print(f"           Questions: {r['key_questions'][:2]}")
        print(f"           Rounds: {len(r['rounds'])}")
    print()

