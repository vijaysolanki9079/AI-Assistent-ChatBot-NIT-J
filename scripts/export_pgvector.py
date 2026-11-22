import json
import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer

JSON_PATH = "data/interview_experiences_structured.json"
SQL_OUTPUT = "data/nitj_experiences_pgvector.sql"

def generate_pgvector_sql(json_path: str = JSON_PATH, sql_output: str = SQL_OUTPUT):
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"{json_path} not found.")

    with open(json_path, "r", encoding="utf-8") as f:
        experiences = json.load(f)

    # Generate 128-dimensional dense representation via Truncated LSA / TF-IDF for pgvector
    texts = [e.get("title", "") + " " + e.get("full_text", "") for e in experiences]
    vectorizer = TfidfVectorizer(max_features=128, stop_words="english")
    X = vectorizer.fit_transform(texts).toarray()

    lines = [
        "-- NIT Jalandhar Alumni Interview Experiences - PostgreSQL + pgvector Migration",
        "-- Generated automatically for Phase 5 Vector Store",
        "",
        "CREATE EXTENSION IF NOT EXISTS vector;",
        "",
        "DROP TABLE IF EXISTS interview_experiences_pgvector CASCADE;",
        "",
        "CREATE TABLE interview_experiences_pgvector (",
        "    id SERIAL PRIMARY KEY,",
        "    experience_id VARCHAR(64) UNIQUE NOT NULL,",
        "    company_name VARCHAR(128) NOT NULL,",
        "    role VARCHAR(128),",
        "    batch VARCHAR(32),",
        "    branch VARCHAR(32),",
        "    offer_type VARCHAR(32),",
        "    author VARCHAR(128),",
        "    date VARCHAR(64),",
        "    title TEXT,",
        "    technical_topics TEXT[],",
        "    key_questions TEXT[],",
        "    preparation_tips TEXT,",
        "    full_text TEXT,",
        "    embedding vector(128)",
        ");",
        "",
        "-- Create IVFFlat index for fast cosine vector similarity search",
        "CREATE INDEX ON interview_experiences_pgvector USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);",
        "",
        "-- Insert structured experiences with vector embeddings",
    ]

    for i, exp in enumerate(experiences):
        eid = exp["experience_id"].replace("'", "''")
        cname = exp["company"].replace("'", "''")
        role = (exp.get("role") or "").replace("'", "''")
        batch = (exp.get("batch") or "").replace("'", "''")
        branch = (exp.get("branch") or "").replace("'", "''")
        author = (exp.get("author") or "").replace("'", "''")
        date = (exp.get("date") or "").replace("'", "''")
        title = exp["title"].replace("'", "''")
        full_text = exp["full_text"].replace("'", "''")
        tips = (exp.get("preparation_tips") or "").replace("'", "''")

        topics = "{" + ",".join([f'"{t}"' for t in exp.get("technical_topics", [])]) + "}"
        questions = "{" + ",".join([f'"{q.replace("\"", "")}"' for q in exp.get("key_questions", [])[:4]]) + "}"

        vec = "[" + ",".join([f"{v:.5f}" for v in X[i]]) + "]"

        sql = f"INSERT INTO interview_experiences_pgvector (experience_id, company_name, role, batch, branch, author, date, title, technical_topics, key_questions, preparation_tips, full_text, embedding) VALUES ('{eid}', '{cname}', '{role}', '{batch}', '{branch}', '{author}', '{date}', '{title}', '{topics}', '{questions}', '{tips}', '{full_text}', '{vec}');"
        lines.append(sql)

    with open(sql_output, "w", encoding="utf-8") as out:
        out.write("\n".join(lines))

    print(f"Generated PostgreSQL + pgvector SQL file with {len(experiences)} vector records at {sql_output}")

if __name__ == "__main__":
    generate_pgvector_sql()

