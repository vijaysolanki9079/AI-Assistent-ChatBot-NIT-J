import sqlite3

conn = sqlite3.connect("data/nitj_placement.db")
cur = conn.cursor()

clean_tokens = ["What", "the", "CTC", "Microsoft", "for", "CSE", "and", "how"]
fts_query = " OR ".join([f'"{tok}"' for tok in clean_tokens[:8]])
print("fts_query:", fts_query)

sql = """
SELECT 
    e.experience_id, e.company_name, bm25(interview_experiences_fts) AS rank_score
FROM interview_experiences_fts
JOIN interview_experiences e ON interview_experiences_fts.experience_id = e.experience_id
WHERE interview_experiences_fts MATCH ?
ORDER BY rank_score ASC
LIMIT 3;
"""

try:
    cur.execute(sql, [fts_query])
    rows = cur.fetchall()
    print("FTS Rows:", rows)
except Exception as e:
    print("FTS Exception:", type(e), e)
