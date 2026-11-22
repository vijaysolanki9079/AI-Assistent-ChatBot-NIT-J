import sqlite3
import os
import re
from typing import Dict, List, Any, Optional, Tuple

DB_PATH = "data/nitj_placement.db"

class SQLEngineError(Exception):
    pass

class SQLEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found at {self.db_path}")

    def execute_query(self, sql: str, params: Optional[Tuple] = None, timeout_sec: float = 5.0) -> Dict[str, Any]:
        """
        Executes a safe read-only SQL query against the database.
        Returns columns and rows, or raises SQLEngineError.
        """
        clean_sql = sql.strip().rstrip(";")
        
        # 1. Safety check: SELECT only
        first_word = clean_sql.split()[0].upper()
        if first_word not in ["SELECT", "WITH"]:
            raise SQLEngineError(f"Security Error: Disallowed statement '{first_word}'. Only SELECT queries are permitted.")

        # Disallow dangerous SQL keywords and confidential tables
        forbidden_patterns = [
            r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b', 
            r'\bALTER\b', r'\bCREATE\b', r'\bTRUNCATE\b', r'\bATTACH\b',
            r'\bDETACH\b', r'\bPRAGMA\b',
            r'\bstudent_private_pii\b', r'\bstudents_pii\b', r'\bprivate_pii\b', r'\bpii_vault\b',
            r'\bhr_contacts\b', r'\bhr_details\b', r'\brecruiter_contacts\b', r'\bhr_email\b',
            r'\bhr_phone\b', r'\brecruiter_email\b', r'\brecruiter_phone\b', r'\bphone_number\b',
            r'\bpersonal_email\b', r'\bparent_phone\b'
        ]
        for fp in forbidden_patterns:
            if re.search(fp, clean_sql, re.I):
                raise SQLEngineError(f"Security Error: Forbidden keyword '{fp}' found in query.")

        # 2. Connect in read-only mode using SQLite URI
        abs_path = os.path.abspath(self.db_path).replace("\\", "/")
        uri = f"file:{abs_path}?mode=ro"
        
        try:
            conn = sqlite3.connect(uri, uri=True, timeout=timeout_sec)
            cur = conn.cursor()
            
            if params:
                cur.execute(clean_sql, params)
            else:
                cur.execute(clean_sql)

            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
            conn.close()

            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "sql": clean_sql
            }

        except sqlite3.Error as e:
            raise SQLEngineError(f"SQL Execution Error: {str(e)}")

