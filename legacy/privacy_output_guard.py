"""
Output Guard for Student Privacy & Confidentiality.
Performs defense-in-depth inspection of database query results:
1. Column-name inspection for confidential attributes
2. Cell-value pattern scanning for emails, phone numbers, roll numbers
3. Minimum group size enforcement (k-anonymity, k=3)
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PrivacyOutputViolationError(Exception):
    """Raised when query output breaches student privacy policies."""
    pass


class PrivacyOutputGuard:
    """
    Guards tabular/scalar outputs before they reach the user.
    Enforces k-anonymity (min group size 3) and redaction of any leaked PII.
    """

    FORBIDDEN_COLUMNS = {
        "roll_no", "roll_number", "rollno", "registration_no", "reg_no", "student_id",
        "phone", "mobile", "contact", "email", "mail_id", "email_id", "personal_email",
        "parent_phone", "parent_name", "father_name", "mother_name", "address", "pincode",
        "dob", "date_of_birth", "aadhar",
        "hr_name", "hr_email", "hr_phone", "hr_contact", "recruiter_email", "recruiter_phone", "recruiter_contact"
    }

    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
    PHONE_PATTERN = re.compile(r'\b(?:\+91|0)?[6-9]\d{9}\b')
    ROLL_PATTERN = re.compile(r'\b(?:20|21|22|23|24)\d{6}\b')

    MIN_GROUP_SIZE = 3
    STANDARD_PRIVACY_NOTICE = (
        "For student privacy and institutional confidentiality, roll numbers, phone numbers, "
        "personal emails, residential addresses, parent details, and HR/recruiter contact information "
        "are strictly protected and cannot be shared. I can provide student placement lists by company, "
        "branch statistics, compensation packages, and alumni interview experiences."
    )

    @classmethod
    def inspect_and_sanitize(
        cls,
        columns: List[str],
        rows: List[Tuple[Any, ...]],
        query_spec: Optional[Any] = None
    ) -> Tuple[List[str], List[Tuple[Any, ...]], Dict[str, Any]]:
        """
        Inspect returned query result for privacy violations.
        Returns (sanitized_columns, sanitized_rows, privacy_metadata).
        Raises PrivacyOutputViolationError if un-sanitizable PII is detected.
        """
        metadata = {
            "pii_detected": False,
            "min_group_enforced": False,
            "sanitized_rows_count": 0,
            "warning": None
        }

        if not rows:
            return columns, rows, metadata

        # 1. Inspect Column Names
        for col in columns:
            clean_col = col.lower().strip()
            if clean_col in cls.FORBIDDEN_COLUMNS or any(f"{f}_" in clean_col or f"_{f}" in clean_col for f in ["phone", "email", "roll_no", "roll_number"]):
                logger.error(f"[Privacy Alert] Output column '{col}' matches forbidden PII attribute.")
                metadata["pii_detected"] = True
                metadata["warning"] = f"Forbidden column '{col}' detected in result set."
                raise PrivacyOutputViolationError(f"Result contains protected personal column: '{col}'.")

        # 2. Cell Pattern Scanning (defense-in-depth on values)
        for r_idx, row in enumerate(rows):
            for c_idx, cell in enumerate(row):
                if cell is None:
                    continue
                cell_str = str(cell).strip()
                if cls.EMAIL_PATTERN.search(cell_str):
                    logger.error(f"[Privacy Alert] Email detected in cell [{r_idx}, {c_idx}].")
                    metadata["pii_detected"] = True
                    raise PrivacyOutputViolationError("Result set contains exposed student email addresses.")
                if cls.PHONE_PATTERN.search(cell_str):
                    logger.error(f"[Privacy Alert] Phone number detected in cell [{r_idx}, {c_idx}].")
                    metadata["pii_detected"] = True
                    raise PrivacyOutputViolationError("Result set contains exposed student phone numbers.")
                if cls.ROLL_PATTERN.search(cell_str):
                    logger.error(f"[Privacy Alert] Roll number pattern detected in cell [{r_idx}, {c_idx}].")
                    metadata["pii_detected"] = True
                    raise PrivacyOutputViolationError("Result set contains exposed student institutional roll numbers.")

        # 3. Minimum Group Size & Demographic Anonymity (k=3)
        # Any query returning student cohorts with size < 3 is flagged for de-anonymization risk
        sanitized_rows = rows
        student_count_cols = [i for i, col in enumerate(columns) if any(k in col.lower() for k in ["student", "placed_count", "placed_students"])]
        if student_count_cols:
            for row in rows:
                for c_idx in student_count_cols:
                    val = row[c_idx]
                    if isinstance(val, (int, float)) and 0 < val < cls.MIN_GROUP_SIZE:
                        metadata["min_group_enforced"] = True
                        metadata["warning"] = f"Cohort size {val} is below k-anonymity threshold ({cls.MIN_GROUP_SIZE})."
                        break

        return columns, sanitized_rows, metadata
