import sqlite3
import json
import re
from typing import List, Dict, Any, Optional

DB_PATH = "data/nitj_placement.db"

STOP_WORDS = {
    "what", "which", "when", "where", "who", "whom", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having",
    "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because",
    "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between",
    "into", "through", "during", "before", "after", "above", "below", "to", "from", "up",
    "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "all", "any", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "can",
    "will", "just", "should", "now", "how", "package", "ctc", "lpa", "offer", "offers",
    "give", "gave", "given", "hire", "hired", "hiring", "student", "students", "much", "many"
}

SYNONYMS = {
    "oa": '("online assessment" OR "oa")',
    "online assessment": '("online assessment" OR "oa")',
    "coding": '("coding" OR "dsa" OR "data structures")',
    "dsa": '("dsa" OR "coding" OR "data structures")',
    "technical": '("technical" OR "tech round")',
    "tech": '("technical" OR "tech round")',
    "interview": '("interview" OR "rounds")',
    "rounds": '("round" OR "rounds" OR "interview")',
    "sql": '("sql" OR "database" OR "dbms")',
    "hr": '("hr" OR "behavioral")',
    "behavioral": '("hr" OR "behavioral")'
}

class ExperienceRetriever:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._load_metadata()

    def _load_metadata(self):
        self.company_alias_map = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Map canonical names and aliases
            cur.execute("""
                SELECT ca.alias, c.canonical_name 
                FROM company_aliases ca 
                JOIN companies c ON ca.company_id = c.company_id
            """)
            for alias, canon in cur.fetchall():
                self.company_alias_map[alias.lower().strip()] = canon
                
            cur.execute("SELECT canonical_name FROM companies")
            for (canon,) in cur.fetchall():
                self.company_alias_map[canon.lower().strip()] = canon
                
            # Also include company names directly present in interview_experiences
            cur.execute("SELECT DISTINCT company_name FROM interview_experiences WHERE company_name IS NOT NULL")
            for (cname,) in cur.fetchall():
                if cname and cname.lower() not in self.company_alias_map:
                    self.company_alias_map[cname.lower().strip()] = cname
                    
            conn.close()
        except Exception:
            pass

    def search(
        self,
        query: str,
        company: Optional[str] = None,
        companies: Optional[List[str]] = None,
        branch: Optional[str] = None,
        topic: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search alumni interview experiences with full-text search and metadata filtering.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        target_companies = []
        if company:
            canon = self.company_alias_map.get(company.lower().strip(), company)
            target_companies.append(canon)
        if companies:
            for c in companies:
                canon = self.company_alias_map.get(c.lower().strip(), c)
                if canon not in target_companies:
                    target_companies.append(canon)

        # Auto-extract company from query if not explicitly passed
        if not target_companies:
            query_lower = query.lower()
            # Sort by descending length so "Goldman Sachs" matches before "Goldman"
            for k, canon in sorted(self.company_alias_map.items(), key=lambda x: -len(x[0])):
                pattern = r'\b' + re.escape(k) + r'\b'
                if re.search(pattern, query_lower):
                    if canon not in target_companies:
                        target_companies.append(canon)
                    break

        where_clauses = []
        params = []

        if target_companies:
            # Match either canonical name, experience company_name, or company_id
            comp_clauses = []
            for tc in target_companies:
                comp_clauses.append("(LOWER(e.company_name) = ? OR e.company_id IN (SELECT company_id FROM companies WHERE LOWER(canonical_name) = ?))")
                params.extend([tc.lower(), tc.lower()])
            where_clauses.append("(" + " OR ".join(comp_clauses) + ")")

        if branch:
            where_clauses.append("(UPPER(e.branch) = ? OR e.branch_code IN (SELECT branch_code FROM branches WHERE UPPER(short_name) = ?))")
            params.extend([branch.upper(), branch.upper()])

        # Build clean FTS tokens with synonym expansion
        words = re.findall(r'[a-zA-Z0-9\+]+', query.lower())
        fts_parts = []
        for w in words:
            if w in STOP_WORDS:
                continue
            # If word is a recognized company and we already filter on it, skip adding to general match to avoid noise
            if target_companies and any(w in tc.lower() for tc in target_companies):
                continue
            if w in SYNONYMS:
                fts_parts.append(SYNONYMS[w])
            elif len(w) >= 3:
                fts_parts.append(f'"{w}"')

        fts_query = " OR ".join(fts_parts[:6]) if fts_parts else ""

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        results = []
        if fts_query:
            try:
                sql = f"""
                SELECT 
                    e.experience_id, e.company_name, e.role, e.batch, e.branch,
                    e.author, e.date, e.title, e.technical_topics, e.rounds_json,
                    e.key_questions_json, e.preparation_tips, e.full_text,
                    e.source_file,
                    bm25(interview_experiences_fts) AS rank_score
                FROM interview_experiences_fts
                JOIN interview_experiences e ON interview_experiences_fts.experience_id = e.experience_id
                {where_sql}
                {"AND" if where_sql else "WHERE"} interview_experiences_fts MATCH ?
                ORDER BY rank_score ASC
                LIMIT ?;
                """
                exec_params = list(params) + [fts_query, top_k]
                cur.execute(sql, exec_params)
                for r in cur.fetchall():
                    results.append(self._format_row(r))
            except sqlite3.OperationalError:
                pass

        # Fallback if FTS returned fewer than top_k results
        if len(results) < top_k:
            existing_ids = {x["experience_id"] for x in results}
            fallback_where = list(where_clauses)
            if existing_ids:
                ph = ",".join(["?"] * len(existing_ids))
                fallback_where.append(f"e.experience_id NOT IN ({ph})")
                fb_params = list(params) + list(existing_ids)
            else:
                fb_params = list(params)

            fb_where_sql = ("WHERE " + " AND ".join(fallback_where)) if fallback_where else ""
            sql_fb = f"""
            SELECT 
                e.experience_id, e.company_name, e.role, e.batch, e.branch,
                e.author, e.date, e.title, e.technical_topics, e.rounds_json,
                e.key_questions_json, e.preparation_tips, e.full_text,
                e.source_file,
                0.0 AS rank_score
            FROM interview_experiences e
            {fb_where_sql}
            ORDER BY e.word_count DESC
            LIMIT ?;
            """
            cur.execute(sql_fb, fb_params + [top_k - len(results)])
            for r in cur.fetchall():
                results.append(self._format_row(r))

        conn.close()
        return results

    def _format_row(self, r: tuple) -> Dict[str, Any]:
        rounds = json.loads(r[9]) if r[9] else []
        questions = json.loads(r[10]) if r[10] else []
        topics = json.loads(r[8]) if r[8] else []

        snippet = r[12][:350].strip() + ("..." if len(r[12]) > 350 else "")

        return {
            "experience_id": r[0],
            "company": r[1],
            "role": r[2],
            "batch": r[3],
            "branch": r[4],
            "author": r[5],
            "date": r[6],
            "title": r[7],
            "technical_topics": topics,
            "rounds": rounds,
            "key_questions": questions,
            "preparation_tips": r[11],
            "excerpt": snippet,
            "source_file": r[13] if len(r) > 13 else None
        }

if __name__ == "__main__":
    retriever = ExperienceRetriever()
    for q in [
        "What is the CTC of Microsoft for CSE and how was the technical round?",
        "Package of Uber and how many interview rounds did they conduct?",
        "Package of Oracle and what SQL questions did they ask?"
    ]:
        print(f"\n--- Query: {q} ---")
        hits = retriever.search(q, top_k=2)
        print(f"Hits: {len(hits)}")
        for h in hits:
            print(f"  [{h['company']}] {h['title']} (File: {h['source_file']}, ID: {h['experience_id'][:10]}...)")
