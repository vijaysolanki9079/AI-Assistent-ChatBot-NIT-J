import sqlite3
import re
import os
import yaml
from difflib import SequenceMatcher
from typing import Dict, List, Any, Optional

import sys
sys.path.insert(0, os.path.abspath("."))
from data.db_authorizer import get_readonly_connection
from src.rag.retriever import ExperienceRetriever

DB_PATH = "data/nitj_placement.db"
SCHEMA_NOTES_PATH = "schema_notes.yaml"

# Load schema notes once if present
SCHEMA_NOTES = {}
if os.path.exists(SCHEMA_NOTES_PATH):
    try:
        with open(SCHEMA_NOTES_PATH, "r", encoding="utf-8") as f:
            SCHEMA_NOTES = yaml.safe_load(f) or {}
    except Exception:
        pass


def execute_sql(query: str, db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Executes a read-only SQL query against SQLite placement database.
    - Runs through strict sqlite3 authorizer denying writes, DDL, and PII.
    - Enforces SELECT/WITH only.
    - Automatically appends LIMIT 100 if no LIMIT clause is present.
    - Returns structured columns metadata {name, type, unit}, typed rows, and row count.
    - On syntax error, returns detailed error string for agent self-correction.
    """
    clean_sql = query.strip().rstrip(";")
    upper_sql = clean_sql.upper()

    # Enforce SELECT/WITH only
    if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
        return {
            "error": "Security Error: Only SELECT and CTE (WITH) queries are permitted.",
            "sql": clean_sql
        }

    # Automatically append LIMIT 100 if no LIMIT clause exists
    if not re.search(r'\bLIMIT\s+\d+\b', clean_sql, re.IGNORECASE):
        clean_sql += "\nLIMIT 100"

    try:
        conn = get_readonly_connection(db_path)
        cur = conn.cursor()
        cur.execute(clean_sql)
        raw_rows = cur.fetchall()
        description = cur.description or []

        columns = []
        for col_desc in description:
            col_name = col_desc[0]
            col_type = "string"
            unit = None

            low = col_name.lower()
            if any(k in low for k in ["ctc", "lpa", "package", "max_ctc", "avg_ctc", "median_ctc"]):
                col_type = "float"
                unit = "LPA"
            elif any(k in low for k in ["stipend"]):
                col_type = "float"
                unit = "INR/mo"
            elif any(k in low for k in ["pct", "percent", "rate"]):
                col_type = "float"
                unit = "%"
            elif any(k in low for k in ["count", "offers", "students", "placed", "eligible"]):
                col_type = "integer"
                unit = "count"
            elif any(k in low for k in ["year", "admission_year", "passout_year"]):
                col_type = "integer"
                unit = "year"

            columns.append({
                "name": col_name,
                "type": col_type,
                "unit": unit
            })

        rows = [list(r) for r in raw_rows]
        conn.close()

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "sql": clean_sql
        }

    except sqlite3.DatabaseError as e:
        return {
            "error": f"SQLite Error: {str(e)}",
            "sql": clean_sql
        }
    except Exception as e:
        return {
            "error": f"Execution Error: {str(e)}",
            "sql": clean_sql
        }


class EntityResolver:
    """
    Deterministic DB-grounded entity resolver.
    Uses ONLY the DB tables: companies, company_aliases, branches, branch_aliases, batch_aliases.
    Performs exact, case-insensitive, and Levenshtein fuzzy matching (similarity >= 0.82).
    CRITICAL: Never fuzzy matches short tokens (<= 3 chars) to prevent 'stasts' -> branch bug.
    """
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._load_db_entities()

    def _load_db_entities(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # 1. Batches & Batch Aliases
        self.batch_alias_map = {}
        cur.execute("SELECT alias, batch_id FROM batch_aliases")
        for alias, bid in cur.fetchall():
            self.batch_alias_map[alias.lower().strip()] = bid
            
        cur.execute("SELECT batch_id FROM batches")
        for (bid,) in cur.fetchall():
            self.batch_alias_map[bid.lower().strip()] = bid

        # 2. Branches & Branch Aliases
        self.branch_map = {}
        cur.execute("SELECT branch_code, canonical_name, short_name FROM branches")
        for bcode, cname, sname in cur.fetchall():
            self.branch_map[sname.lower().strip()] = sname
            self.branch_map[cname.lower().strip()] = sname

        cur.execute("SELECT ba.alias, b.short_name FROM branch_aliases ba JOIN branches b ON ba.branch_code = b.branch_code")
        for alias, sname in cur.fetchall():
            self.branch_map[alias.lower().strip()] = sname

        # 3. Companies & Company Aliases
        self.company_map = {}
        cur.execute("SELECT company_id, canonical_name FROM companies")
        for cid, cname in cur.fetchall():
            self.company_map[cname.lower().strip()] = cname

        cur.execute("SELECT ca.alias, c.canonical_name FROM company_aliases ca JOIN companies c ON ca.company_id = c.company_id")
        for alias, cname in cur.fetchall():
            self.company_map[alias.lower().strip()] = cname

        conn.close()

    def resolve(self, text: str) -> Dict[str, List[str]]:
        text_clean = text.strip()
        low_text = text_clean.lower()

        found_companies = []
        found_branches = []
        found_batches = []

        # 1. Batch resolution (exact / alias)
        for alias in sorted(self.batch_alias_map.keys(), key=lambda x: -len(x)):
            pattern = r'(?:\b|^)' + re.escape(alias) + r'(?:\b|$)'
            if re.search(pattern, low_text):
                bid = self.batch_alias_map[alias]
                if bid not in found_batches:
                    found_batches.append(bid)

        # 2. Company resolution (exact match on full aliases first)
        for alias in sorted(self.company_map.keys(), key=lambda x: -len(x)):
            # Ignore very short aliases if they conflict with common English words
            if len(alias) <= 3 and alias in ["in", "it", "at", "to", "or", "on", "as", "by", "is", "of"]:
                continue
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, low_text):
                cname = self.company_map[alias]
                if cname not in found_companies:
                    found_companies.append(cname)

        # 3. Branch resolution
        BRANCH_EXCLUSIONS = {"stats", "stasts", "status", "all", "the", "and", "for", "with", "batch", "branch", "department"}
        # Check explicit branch phrases first (e.g. "it branch", "cse branch", "ece department")
        for alias, sname in self.branch_map.items():
            if alias in BRANCH_EXCLUSIONS:
                continue
            # If alias is "me", ensure it's not the Hindi preposition "in" (e.g. "branch me" or "cse me")
            if alias == "me":
                if re.search(r'\b(?:mechanical|mech)\b', low_text) or re.search(r'\bme\s+(?:branch|dept|department)\b', low_text):
                    if sname not in found_branches:
                        found_branches.append(sname)
                continue

            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, low_text):
                if sname not in found_branches:
                    found_branches.append(sname)

        # 4. Levenshtein Fuzzy matching for potential typos (if company not found yet)
        if not found_companies:
            words = re.findall(r'[a-zA-Z0-9]+', low_text)
            COMMON_QUERY_WORDS = {
                "what", "which", "package", "ctc", "lpa", "offer", "placed", "placement", 
                "stats", "stasts", "student", "students", "highest", "average", "median", 
                "branch", "batch", "department", "college", "company", "recruiters", 
                "interview", "experiences", "kisne", "diya", "sabse", "jyada", "kitne", "hai", "batao"
            }
            for w in words:
                if len(w) <= 3 or w in COMMON_QUERY_WORDS:
                    continue
                for alias, cname in self.company_map.items():
                    if len(alias) <= 3:
                        continue
                    sim = SequenceMatcher(None, w, alias).ratio()
                    if sim >= 0.82:
                        if cname not in found_companies:
                            found_companies.append(cname)
                        break

        return {
            "companies": found_companies,
            "branches": found_branches,
            "batches": found_batches
        }


# Singleton resolver
_RESOLVER = None

def resolve_entities(text: str) -> Dict[str, List[str]]:
    """Resolves companies, branches, and batches from text using DB tables with zero hallucination."""
    global _RESOLVER
    if _RESOLVER is None:
        _RESOLVER = EntityResolver()
    return _RESOLVER.resolve(text)


def search_interview_experiences(query: str, company: Optional[str] = None, top_k: int = 3) -> Dict[str, Any]:
    """Retrieves qualitative alumni interview experiences and questions with full provenance citations."""
    retriever = ExperienceRetriever()
    results = retriever.search(query=query, company=company, top_k=top_k)
    return {
        "query": query,
        "company": company,
        "hit_count": len(results),
        "chunks": results
    }


def lookup_schema(table_or_view: Optional[str] = None) -> Dict[str, Any]:
    """Returns documentation and gotchas for database tables and views from schema_notes.yaml."""
    if not table_or_view:
        return SCHEMA_NOTES
    
    key = table_or_view.lower().strip()
    tables = SCHEMA_NOTES.get("tables", {})
    views = SCHEMA_NOTES.get("views", {})

    if key in tables:
        return {key: tables[key]}
    if key in views:
        return {key: views[key]}

    return {"error": f"Table or view '{table_or_view}' not found in schema documentation."}
