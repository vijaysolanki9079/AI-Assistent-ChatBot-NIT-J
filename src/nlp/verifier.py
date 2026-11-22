from typing import Dict, Any, List, Optional

class VerificationError(Exception):
    pass

class QueryVerifier:
    def verify(self, question_type: str, query_result: Dict[str, Any], query_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs post-execution sanity checks on SQL query results.
        Returns verification status, confidence (High/Medium/Low), and caveats.
        """
        rows = query_result.get("rows", [])
        columns = query_result.get("columns", [])
        caveats = []
        confidence = "High"

        # 1. Empty Result Handling
        if len(rows) == 0:
            return {
                "is_valid": True,
                "confidence": "Medium",
                "is_empty": True,
                "message": "No records found matching the specified criteria in the placement database.",
                "caveats": ["Query executed successfully but matched 0 rows."]
            }

        # 2. Percentage Sanity Check (0.0 to 100.0)
        pct_columns = [i for i, c in enumerate(columns) if any(term in c.lower() for term in ["pct", "percentage", "share", "ratio"])]
        for r in rows:
            for c_idx in pct_columns:
                val = r[c_idx]
                if val is not None:
                    try:
                        fval = float(val)
                        if fval < 0.0 or fval > 100.0:
                            return {
                                "is_valid": False,
                                "confidence": "Low",
                                "error": f"Sanity Failure: Calculated percentage value {fval}% is outside valid range [0, 100]."
                            }
                    except (ValueError, TypeError):
                        pass

        # 3. CTC Sanity Check
        ctc_columns = [i for i, c in enumerate(columns) if any(term in c.lower() for term in ["ctc", "package", "lpa"])]
        for r in rows:
            for c_idx in ctc_columns:
                val = r[c_idx]
                if val is not None:
                    try:
                        fval = float(val)
                        if fval > 200.0:
                            # Suspicious: likely monthly stipend in INR was mistakenly read as LPA
                            return {
                                "is_valid": False,
                                "confidence": "Low",
                                "error": f"Sanity Failure: CTC value {fval} LPA exceeds plausible range; check stipend vs CTC segregation."
                            }
                        if fval <= 0.0:
                            caveats.append(f"Recorded CTC {fval} is non-positive.")
                    except (ValueError, TypeError):
                        pass

        # 4. Count vs Distinct Count Check
        # If result is student count, check min group size rule for privacy
        if len(rows) == 1 and len(columns) == 1 and isinstance(rows[0][0], int):
            count_val = rows[0][0]
            if count_val < 3 and count_val > 0 and question_type in ["Count by condition"]:
                caveats.append(f"Small cohort size ({count_val} student(s)).")
                confidence = "High"

        return {
            "is_valid": True,
            "confidence": confidence,
            "is_empty": False,
            "caveats": caveats
        }

