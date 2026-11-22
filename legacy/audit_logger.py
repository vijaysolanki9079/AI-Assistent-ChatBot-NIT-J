"""
Audit Logger for NITJ Placement Assistant.
Logs every question, QuerySpec, confidence, SQL, and result size
to logs/query_audit.jsonl for production telemetry, monitoring, and active learning.
"""

import os
import json
import time
import datetime
from typing import Dict, Any, Optional

LOGS_DIR = os.path.abspath("logs")
AUDIT_LOG_FILE = os.path.join(LOGS_DIR, "query_audit.jsonl")


class AuditLogger:
    """Handles structured JSONL telemetry logging for all query executions."""

    @classmethod
    def ensure_log_dir(cls):
        """Ensure the logs directory exists."""
        if not os.path.exists(LOGS_DIR):
            os.makedirs(LOGS_DIR, exist_ok=True)

    @classmethod
    def log(
        cls,
        question: str,
        query_spec: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        sql: Optional[str] = None,
        result_size: int = 0,
        category: str = "structured",
        status: str = "success",
        duration_ms: float = 0.0,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Append a structured JSON line to logs/query_audit.jsonl."""
        cls.ensure_log_dir()

        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "question": question,
            "query_spec": query_spec,
            "confidence": round(float(confidence), 3),
            "sql": sql,
            "result_size": int(result_size) if result_size is not None else 0,
            "category": category,
            "status": status,
            "duration_ms": round(float(duration_ms), 2),
            "error": error
        }

        try:
            line = json.dumps(entry, ensure_ascii=False) + "\n"
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            # Non-blocking: failure to log must never crash the primary query pipeline
            pass

        return entry

