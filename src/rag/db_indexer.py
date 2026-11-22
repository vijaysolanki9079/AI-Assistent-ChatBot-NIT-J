import sqlite3
import json
import os

DB_PATH = "data/nitj_placement.db"
JSON_PATH = "data/interview_experiences_structured.json"

def index_experiences(db_path: str = DB_PATH, json_path: str = JSON_PATH):
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"{json_path} does not exist.")

    with open(json_path, "r", encoding="utf-8") as f:
        experiences = json.load(f)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Drop old tables if exist
    cur.execute("DROP TABLE IF EXISTS interview_experiences_fts;")
    cur.execute("DROP TABLE IF EXISTS interview_experiences;")

    # Create relational table
    cur.execute("""
    CREATE TABLE interview_experiences (
        experience_id TEXT PRIMARY KEY,
        source_file TEXT,
        company_name TEXT NOT NULL,
        role TEXT,
        batch TEXT,
        branch TEXT,
        offer_type TEXT,
        author TEXT,
        date TEXT,
        title TEXT,
        technical_topics TEXT,
        rounds_json TEXT,
        key_questions_json TEXT,
        preparation_tips TEXT,
        full_text TEXT,
        word_count INTEGER
    );
    """)

    # Create FTS5 virtual table for lightning-fast BM25 full text search
    cur.execute("""
    CREATE VIRTUAL TABLE interview_experiences_fts USING fts5(
        experience_id UNINDEXED,
        company_name,
        role,
        title,
        technical_topics,
        key_questions,
        full_text,
        tokenize = 'porter unicode61'
    );
    """)

    # Create index on company_name
    cur.execute("CREATE INDEX idx_exp_company ON interview_experiences(company_name);")
    cur.execute("CREATE INDEX idx_exp_branch ON interview_experiences(branch);")

    # Insert all records
    for exp in experiences:
        topics_str = ", ".join(exp.get("technical_topics", []))
        questions_str = " | ".join(exp.get("key_questions", []))
        rounds_json = json.dumps(exp.get("rounds", []), ensure_ascii=False)
        questions_json = json.dumps(exp.get("key_questions", []), ensure_ascii=False)

        cur.execute("""
        INSERT INTO interview_experiences (
            experience_id, source_file, company_name, role, batch, branch,
            offer_type, author, date, title, technical_topics, rounds_json,
            key_questions_json, preparation_tips, full_text, word_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            exp["experience_id"],
            exp.get("source_file"),
            exp["company"],
            exp.get("role"),
            exp.get("batch"),
            exp.get("branch"),
            exp.get("offer_type"),
            exp.get("author"),
            exp.get("date"),
            exp["title"],
            json.dumps(exp.get("technical_topics", []), ensure_ascii=False),
            rounds_json,
            questions_json,
            exp.get("preparation_tips"),
            exp["full_text"],
            exp.get("word_count", 0)
        ))

        cur.execute("""
        INSERT INTO interview_experiences_fts (
            experience_id, company_name, role, title, technical_topics, key_questions, full_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            exp["experience_id"],
            exp["company"],
            exp.get("role", ""),
            exp["title"],
            topics_str,
            questions_str,
            exp["full_text"]
        ))

    conn.commit()
    conn.close()
    print(f"Successfully indexed {len(experiences)} experiences into {db_path} (tables: interview_experiences, interview_experiences_fts)")

if __name__ == "__main__":
    index_experiences()

