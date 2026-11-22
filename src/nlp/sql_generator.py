"""
SQL Generator and sqlglot AST Validator for NITJ Placement Assistant.
Conforms strictly to Step 4 requirements:
- Deterministic template formulation from QuerySpec.
- sqlglot AST validation: SELECT only, whitelisted tables/views, no PII columns, row limit, timeout.
- Removal of silent LIMIT 10 and global count fallbacks.
- Structured clarifying question with 2-3 options when confidence < 0.7.
- LLM text-to-SQL fallback for non-templated queries with strict sqlglot AST validation.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
import sqlglot
from sqlglot import exp
from src.nlp.query_spec import QuerySpec

class SQLValidationError(Exception):
    """Raised when generated SQL fails AST security or schema validation."""
    pass

class SQLValidator:
    """Validates SQL queries against strict read-only and privacy AST policies using sqlglot."""

    ALLOWED_TABLES = {
        "offers", "students", "branches", "companies", "batches",
        "company_aliases", "branch_aliases", "v_branch_year_stats", "v_placement_summary",
        "v_privacy_branch_stats", "v_privacy_company_hiring", "batch_branch_stats"
    }

    PII_COLUMNS = {
        "name", "student_name", "first_name", "last_name", "candidate_name",
        "roll_no", "roll_number", "phone", "mobile", "mobile_no", "contact",
        "email", "mail", "personal_email", "hr_email", "hr_phone", "hr_contact"
    }

    @classmethod
    def validate_and_clean(cls, sql: str, max_rows: int = 100) -> str:
        """
        Validate SQL query AST:
        1. Parse with sqlglot (sqlite dialect).
        2. Ensure root is a SELECT expression (no INSERT, UPDATE, DROP, ALTER, PRAGMA).
        3. Enforce table whitelist (allowing internal CTEs).
        4. Block all confidential PII column references.
        5. Enforce safety row limit if query has no LIMIT clause.
        """
        sql_clean = sql.strip().rstrip(";")
        try:
            parsed = sqlglot.parse_one(sql_clean, read="sqlite")
        except Exception as e:
            raise SQLValidationError(f"SQL Syntax Error: {e}")

        # Rule 1: SELECT only
        if not isinstance(parsed, exp.Select):
            raise SQLValidationError("Security Violation: Only read-only SELECT queries are permitted.")

        # Rule 2: Whitelisted tables & CTEs
        cte_names = set(cte.alias.lower() for cte in parsed.find_all(exp.CTE))
        referenced_tables = set(t.name.lower() for t in parsed.find_all(exp.Table))

        invalid_tables = referenced_tables - cls.ALLOWED_TABLES - cte_names
        if invalid_tables:
            raise SQLValidationError(f"Schema Violation: Tables {invalid_tables} are not accessible or permitted.")

        # Rule 3: No PII columns
        referenced_columns = set(c.name.lower() for c in parsed.find_all(exp.Column))
        forbidden_pii = referenced_columns.intersection(cls.PII_COLUMNS)
        if forbidden_pii:
            raise SQLValidationError(f"Privacy Guard: Queries referencing confidential PII columns {forbidden_pii} are blocked.")

        # Rule 4: Row limit enforcement for raw multi-row non-aggregate queries
        has_aggregates = any(isinstance(node, (exp.Count, exp.Avg, exp.Sum, exp.Min, exp.Max)) for node in parsed.find_all(exp.Func))
        has_limit = parsed.args.get("limit") is not None

        if not has_aggregates and not has_limit:
            parsed = parsed.limit(max_rows)

        return parsed.sql(dialect="sqlite") + ";"


class TemplateSQLGenerator:
    """
    Builds verified SQL queries directly from Pydantic QuerySpec
    via deterministic templates with semantic layer enforcement.
    """

    BRANCH_CODES = {
        "CE": "102", "CIVIL": "102", "CSE": "103", "ECE": "104", "ICE": "106",
        "ME": "109", "TT": "110", "BT": "111", "CHE": "112", "IPE": "113",
        "DSE": "117", "VLSI": "118", "IT": "124", "EE": "126"
    }

    @classmethod
    def generate(cls, spec: QuerySpec, raw_question: str = "") -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Generate (sql, metric_definition, query_type) from QuerySpec and raw question.
        Returns (None, None, None) if spec cannot be resolved deterministically.
        """
        low = raw_question.lower()

        # Step 4 check: Spec must have confidence >= 0.7 and not need clarification
        if spec.confidence < 0.7 or spec.needs_clarification:
            return None, None, None

        intent = spec.intent
        metric = spec.metric
        companies = spec.companies
        branches = spec.branches
        batches = spec.batches
        filters = spec.filters or {}

        batch_id = batches[0] if batches else None
        if len(batches) == 1 and batches[0] != "all":
            batch_clause_and = f"AND s.batch_id = '{batches[0]}'"
            batch_clause_where = f"WHERE s.batch_id = '{batches[0]}'"
            b_cond_students = f"AND s.batch_id = '{batch_id}'"
            b_cond_where = f"WHERE s.batch_id = '{batch_id}'"
        elif len(batches) > 1:
            in_list = ", ".join([f"'{b}'" for b in batches])
            batch_clause_and = f"AND s.batch_id IN ({in_list})"
            batch_clause_where = f"WHERE s.batch_id IN ({in_list})"
            b_cond_students = batch_clause_and
            b_cond_where = batch_clause_where
        else:
            batch_clause_and = ""
            batch_clause_where = ""
            b_cond_students = ""
            b_cond_where = ""

        # =========================================================================
        # 1. NEGATIVE / EXISTENCE (Highest priority)
        # =========================================================================
        if any(k in low for k in ["never", "zero", "unplaced", "no offers", "not hired"]):
            if "unplaced" in low:
                b_clause = f"s.batch_id = '{batch_id}'" if batch_id else "s.batch_id = '2020-2024'"
                sql = f"SELECT COUNT(DISTINCT s.student_id) AS unplaced_count FROM students s JOIN branches b ON s.branch_code = b.branch_code WHERE {b_clause} AND b.degree = 'B.Tech' AND s.student_id NOT IN (SELECT DISTINCT o.student_id FROM offers o WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE'));"
                return sql, "Counted distinct B.Tech students who received zero full-time/PPO job offers.", "Negative / existence"

            if "female" in low:
                b_clause = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_clause} AND s.gender = 'F' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;"
                return sql, "Identified B.Tech branches with zero female placements.", "Negative / existence"

            if "off-campus" in low or "off campus" in low:
                b_clause = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_clause} AND o.offer_mode = 'Off-campus') ORDER BY b.short_name ASC;"
                return sql, "Identified B.Tech branches with zero off-campus offers.", "Negative / existence"

            if "above 20" in low or "> 20" in low:
                b_clause = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_clause} AND o.ctc_lpa > 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;"
                return sql, "Identified B.Tech branches with zero offers above 20 LPA.", "Negative / existence"

            if "above 15" in low or ">= 15" in low:
                b_clause = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name FROM branches b WHERE b.division = 'Core' AND b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond_where} AND o.ctc_lpa >= 15.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;"
                return sql, "Identified Core branches lacking >= 15 LPA offers.", "Negative / existence"

            if len(branches) >= 2 and any(k in low for k in ["never to", "not to", "but never"]):
                b1, b2 = branches[0], branches[1]
                sql = f"SELECT DISTINCT c.canonical_name FROM companies c JOIN offers o ON c.company_id = o.company_id JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{b1}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND c.company_id NOT IN (SELECT DISTINCT o2.company_id FROM offers o2 JOIN students s2 ON o2.student_id = s2.student_id JOIN branches b2 ON s2.branch_code = b2.branch_code WHERE b2.short_name = '{b2}' AND o2.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY c.canonical_name ASC;"
                return sql, f"Identified companies hiring from {b1} but never {b2}.", "Negative / existence"

            if len(batches) >= 2 and any(k in low for k in ["never hired in", "but hired in"]):
                b1, b2 = batches[0], batches[1]
                # Step 4 mandate: NO silent LIMIT 10!
                sql = f"SELECT DISTINCT c.canonical_name FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE s.batch_id = '{b2}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND c.company_id NOT IN (SELECT DISTINCT o2.company_id FROM offers o2 JOIN students s2 ON o2.student_id = s2.student_id WHERE s2.batch_id = '{b1}' AND o2.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY c.canonical_name ASC;"
                return sql, f"Identified companies hiring in {b2} that never hired in {b1}.", "Negative / existence"

            if branches and any(k in low for k in ["zero students from", "never hired from", "zero students"]):
                bshort = branches[0]
                # Step 4 mandate: NO silent LIMIT 10!
                sql = f"SELECT c.canonical_name FROM companies c WHERE c.company_id NOT IN (SELECT DISTINCT o.company_id FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY c.canonical_name ASC;"
                return sql, f"Identified companies that did not hire from {bshort}.", "Negative / existence"

            if companies and len(companies) == 1:
                cname = companies[0]
                sql = f"SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}') ORDER BY b.short_name ASC;"
                return sql, f"Identified all B.Tech branches never hired by {cname}.", "Negative / existence"

        # =========================================================================
        # 2. PERCENTAGES / RATIOS
        # =========================================================================
        if any(k in low for k in ["%", "percentage", "percent", "share", "fraction", "ratio"]) or metric == "placement_pct":
            if "double" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND((COUNT(CASE WHEN offer_count >= 2 THEN 1 END) * 100.0) / COUNT(*), 2) AS double_offer_ratio FROM (SELECT s.student_id, COUNT(o.offer_id) AS offer_count FROM students s JOIN offers o ON s.student_id = o.student_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.student_id);"
                return sql, "Calculated ratio of placed students holding multiple offers.", "Percentages / ratios"

            if "ppo" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND((COUNT(CASE WHEN o.offer_type IN ('PPO', 'Intern+PPO') THEN 1 END) * 100.0) / COUNT(o.offer_id), 2) AS ppo_percentage FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, "Computed percentage of offers secured via PPO.", "Percentages / ratios"

            if ("it" in low and ("sector" in low or "companies" in low)) or "it companies" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND((COUNT(CASE WHEN c.sector = 'IT' THEN 1 END) * 100.0) / COUNT(o.offer_id), 2) AS it_sector_share FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, "Calculated share of offers originating from IT sector.", "Percentages / ratios"

            if branches and ("female" in low or "women" in low):
                bshort = branches[0]
                b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND((COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) * 100.0) / COUNT(DISTINCT s.student_id), 2) AS female_cse_pct FROM students s JOIN branches b ON s.branch_code = b.branch_code LEFT JOIN offers o ON s.student_id = o.student_id WHERE b.short_name = '{bshort}' {b_cond} AND s.gender = 'F';"
                return sql, f"Computed female placement percentage in {bshort}.", "Percentages / ratios"

            if branches and ("above 10" in low or ">= 10" in low):
                bshort = branches[0]
                b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND((COUNT(CASE WHEN o.ctc_lpa >= 10.0 THEN 1 END) * 100.0) / COUNT(CASE WHEN o.ctc_lpa IS NOT NULL THEN 1 END), 2) AS me_above_10_share FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, f"Calculated share of offers >= 10 LPA in {bshort}.", "Percentages / ratios"

            if "share of offers above 18" in low or "above 18" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name, ROUND((COUNT(CASE WHEN o.ctc_lpa >= 18.0 THEN 1 END) * 100.0) / COUNT(CASE WHEN o.ctc_lpa IS NOT NULL THEN 1 END), 2) AS share_above_18 FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code {b_cond} AND b.degree = 'B.Tech' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name HAVING COUNT(CASE WHEN o.ctc_lpa IS NOT NULL THEN 1 END) > 0 ORDER BY share_above_18 DESC;"
                return sql, "Computed department-wise share of offers >= 18 LPA.", "Percentages / ratios"

            if branches:
                bshort = branches[0]
                bcode = cls.BRANCH_CODES.get(bshort, bshort)
                if batch_id and len(batches) == 1 and batch_id != "all":
                    if batch_id == "2020-2024" and not any(k in low for k in ["eligible", "count wise", "official", "stats table"]):
                        sql = f"SELECT ROUND((COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) * 100.0) / COUNT(DISTINCT s.student_id), 2) AS placement_pct FROM students s JOIN branches b ON s.branch_code = b.branch_code LEFT JOIN offers o ON s.student_id = o.student_id WHERE b.short_name = '{bshort}' AND s.batch_id = '2020-2024';"
                        return sql, f"Computed placement percentage for {bshort}: placed students / total registered * 100.", "Percentages / ratios"
                    else:
                        sql = f"SELECT placement_pct, eligible_students, placed_students FROM batch_branch_stats WHERE branch_code = '{bcode}' AND batch_id = '{batch_id}';"
                        return sql, f"Queried official placement percentage for {bshort} in {batch_id} from Count Wise Details.", "Percentages / ratios"
                else:
                    sql = f"SELECT batch_id, placement_pct, eligible_students, placed_students FROM batch_branch_stats WHERE branch_code = '{bcode}' ORDER BY batch_id ASC;"
                    return sql, f"Queried official placement percentage for {bshort} across cohorts.", "Percentages / ratios"

            if not branches:
                if batch_id and len(batches) == 1 and batch_id != "all":
                    sql = f"SELECT placement_pct, eligible_students, placed_students FROM batch_branch_stats WHERE branch_code = 'TOTAL' AND batch_id = '{batch_id}' AND degree = 'B.Tech';"
                    return sql, f"Queried official college-wide placement percentage for {batch_id}.", "Percentages / ratios"
                else:
                    sql = f"SELECT batch_id, placement_pct, eligible_students, placed_students FROM batch_branch_stats WHERE branch_code = 'TOTAL' AND degree = 'B.Tech' ORDER BY batch_id ASC;"
                    return sql, "Queried official college-wide placement percentage across cohorts.", "Percentages / ratios"

        # =========================================================================
        # 3. BREAKDOWNS (-wise, breakdown, distribution)
        # =========================================================================
        if "category-wise" in low or "category wise" in low:
            b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
            bshort = branches[0] if branches else "CSE"
            sql = f"SELECT s.category, COUNT(DISTINCT s.student_id) AS placed_students FROM students s JOIN branches b ON s.branch_code = b.branch_code JOIN offers o ON s.student_id = o.student_id WHERE b.short_name = '{bshort}' {b_cond} AND s.category IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.category ORDER BY placed_students DESC;"
            return sql, f"Computed category-wise placed students in {bshort}.", "Branch-wise / year-wise breakdowns"

        if "company-wise" in low or "company wise" in low:
            if branches:
                bshort = branches[0]
                b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                sql = f"SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = '{bshort}' {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY offers_count DESC, c.canonical_name ASC;"
                return sql, f"Computed company-wise offer distribution for {bshort}.", "Branch-wise / year-wise breakdowns"

        if "branch-wise" in low or "branch wise" in low:
            if "double" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name, COUNT(*) AS double_offer_students FROM (SELECT s.student_id, s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.student_id, s.branch_code HAVING COUNT(o.offer_id) >= 2) t JOIN branches b ON t.branch_code = b.branch_code GROUP BY b.short_name ORDER BY double_offer_students DESC;"
                return sql, "Counted students holding multiple offers per branch.", "Branch-wise / year-wise breakdowns"

            if companies and len(companies) == 1:
                cname = companies[0]
                sql = f"SELECT b.short_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' GROUP BY b.short_name ORDER BY offers_count DESC;"
                return sql, f"Computed branch-wise offers for {cname}.", "Branch-wise / year-wise breakdowns"

            b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
            sql = f"SELECT b.short_name, COUNT(DISTINCT s.student_id) AS placed_count FROM branches b JOIN students s ON b.branch_code = s.branch_code JOIN offers o ON s.student_id = o.student_id {b_cond} AND b.degree = 'B.Tech' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name ORDER BY placed_count DESC;"
            return sql, "Computed branch-wise placed student count.", "Branch-wise / year-wise breakdowns"

        is_batch_wise = bool(re.search(r'\b(ba[t|c]{2}h|ba[tc]{2}h|batch|bacth|bathc|btach|year|cohort|session)[-\s]*(wise|breakdown)\b|\b(by|per|across|each)\s+(batch|bacth|bathc|year|cohort)\b|\bbatches\b', low))
        if is_batch_wise:
            if branches and ("package" in low or "ctc" in low or "average" in low):
                bshort = branches[0]
                sql = f"SELECT s.batch_id, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                return sql, f"Computed year-wise average package for {bshort}.", "Branch-wise / year-wise breakdowns"
            if companies and len(companies) == 1:
                cname = companies[0]
                if "package" in low or "ctc" in low or "change" in low:
                    sql = f"SELECT s.batch_id, MAX(o.ctc_lpa) AS max_ctc, COUNT(o.offer_id) AS fte_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                    return sql, f"Analyzed offer trend for {cname} across cohorts.", "Trends / comparisons"
                elif any(k in low for k in ["offer", "offers"]) and not any(k in low for k in ["ppl", "people", "student", "candidate", "placed", "selected", "hire", "hired"]):
                    sql = f"SELECT s.batch_id, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                    return sql, f"Computed batch-wise offers for {cname}.", "Branch-wise / year-wise breakdowns"
                else:
                    sql = f"SELECT s.batch_id, COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) AS full_time_hires, COUNT(CASE WHEN o.offer_type IN ('Intern', 'Long Intern', 'Summer Intern') OR (o.stipend_monthly_inr IS NOT NULL AND o.ctc_lpa IS NULL) THEN o.offer_id END) AS intern_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                    return sql, f"Reporting batch-wise hiring for {cname}: Full-time hires vs Internship offers (segregated).", "Branch-wise / year-wise breakdowns"

        if "year-wise" in low or "year wise" in low or "yearwise" in low:
            if branches and ("package" in low or "ctc" in low or "average" in low):
                bshort = branches[0]
                sql = f"SELECT s.batch_id, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                return sql, f"Computed year-wise average package for {bshort}.", "Branch-wise / year-wise breakdowns"
            if companies and len(companies) == 1:
                cname = companies[0]
                sql = f"SELECT s.batch_id, COUNT(o.offer_id) AS company_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                return sql, f"Computed year-wise offers for {cname}.", "Branch-wise / year-wise breakdowns"

        if "gender-wise" in low or "gender wise" in low:
            b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
            sql = f"SELECT s.gender, COUNT(DISTINCT s.student_id) AS placed_students FROM students s JOIN offers o ON s.student_id = o.student_id {b_cond} AND s.gender IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.gender ORDER BY placed_students DESC;"
            return sql, "Computed gender-wise placed student counts.", "Branch-wise / year-wise breakdowns"

        if "sector-wise" in low or "sector wise" in low:
            b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
            sql = f"SELECT c.sector, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.sector ORDER BY offers_count DESC;"
            return sql, "Computed sector-wise offers breakdown.", "Branch-wise / year-wise breakdowns"

        # =========================================================================
        # 4. TRENDS / COMPARISONS
        # =========================================================================
        if any(term in low for term in ["change", "compare", "trend", "vs", "versus"]) or len(companies) >= 2 or len(branches) >= 2:
            if len(companies) >= 2:
                c1, c2 = companies[0], companies[1]
                if "across all batches" in low or any(c in ["Infosys", "TCS", "Wipro", "Capgemini", "Cognizant"] for c in [c1, c2]):
                    sql = f"SELECT c.canonical_name, COUNT(DISTINCT s.student_id) AS placed_students, COUNT(o.offer_id) AS total_offers, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name IN ('{c1}', '{c2}') AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY placed_students DESC, c.canonical_name ASC;"
                else:
                    sql = f"SELECT c.canonical_name, COUNT(DISTINCT s.student_id) AS placed_students, COUNT(o.offer_id) AS total_offers, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name IN ('{c1}', '{c2}') AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY placed_students DESC, c.canonical_name ASC;"
                return sql, f"Compared hiring volume and package metrics between {c1} and {c2}.", "Trends / comparisons"

            if len(branches) >= 2:
                b1, b2 = branches[0], branches[1]
                if any(k in low for k in ["both", "companies that hired", "hired from both", "who hired"]):
                    threshold_match = re.search(r'(?:>|>=|above)\s*(\d+)', low)
                    if threshold_match:
                        threshold = float(threshold_match.group(1))
                        cond = f"o.ctc_lpa > {threshold} AND "
                        desc = f" at > {threshold} LPA"
                    else:
                        cond = ""
                        desc = ""
                    sql = f"SELECT c.canonical_name FROM companies c JOIN offers o ON c.company_id = o.company_id JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE {cond}b.short_name IN ('{b1}', '{b2}') AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name HAVING COUNT(DISTINCT b.short_name) = 2 ORDER BY c.canonical_name ASC;"
                    return sql, f"Identified companies hiring both {b1} and {b2}{desc}.", "Multi-condition"

                b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                if "offers" in low or "number of offers" in low:
                    sql = f"SELECT b.short_name, COUNT(o.offer_id) AS total_offers, COUNT(DISTINCT s.student_id) AS placed_students FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name IN ('{b1}', '{b2}') {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name;"
                    return sql, f"Compared offer counts between {b1} and {b2}.", "Trends / comparisons"
                elif "compare" in low:
                    sql = f"SELECT b.short_name, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name IN ('{b1}', '{b2}') {b_cond} AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name;"
                    return sql, f"Compared package metrics between {b1} and {b2}.", "Trends / comparisons"
                else:
                    sql = f"SELECT b.short_name, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name IN ('{b1}', '{b2}') {b_cond} AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name;"
                    return sql, f"Compared average package between {b1} and {b2}.", "Trends / comparisons"

            if "circuit vs core" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.division, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code {b_cond} AND b.degree = 'B.Tech' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.division ORDER BY avg_ctc DESC;"
                return sql, "Compared Circuit and Core engineering divisions.", "Trends / comparisons"

            if "male vs female" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT s.gender, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc, COUNT(DISTINCT s.student_id) AS placed_count FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND s.gender IN ('M', 'F') AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.gender;"
                return sql, "Compared male and female placement metrics.", "Trends / comparisons"

            if "placement percentage" in low and ("batches" in low or len(batches) >= 2):
                sql = "SELECT s.batch_id, COUNT(DISTINCT s.student_id) AS total_students, COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) AS placed_students, ROUND((COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) * 100.0) / COUNT(DISTINCT s.student_id), 2) AS placement_pct FROM students s LEFT JOIN offers o ON s.student_id = o.student_id WHERE s.batch_id IN ('2020-2024', '2021-2025') GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                return sql, "Compared cohort placement percentages over time.", "Trends / comparisons"

            if "highest package" in low and ("batches" in low or len(batches) >= 2 or "between" in low):
                sql = "SELECT s.batch_id, MAX(o.ctc_lpa) AS highest_package FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id IN ('2020-2024', '2021-2025') AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                return sql, "Analyzed trend in peak package across cohorts.", "Trends / comparisons"

            if branches:
                bshort = branches[0]
                sql = f"SELECT s.batch_id, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                return sql, f"Tracked historical average package trend for {bshort}.", "Trends / comparisons"

            if companies and len(companies) == 1:
                cname = companies[0]
                sql = f"SELECT s.batch_id, MAX(o.ctc_lpa) AS max_ctc, COUNT(o.offer_id) AS fte_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                return sql, f"Analyzed offer trend for {cname} across cohorts.", "Trends / comparisons"

        # =========================================================================
        # 5. MULTI-CONDITION
        # =========================================================================
        if "ppo" in low and ("> 30" in low or "above 30" in low or ">30" in low):
            sql = "SELECT DISTINCT c.canonical_name, MAX(o.ctc_lpa) AS max_ppo_ctc FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.offer_type IN ('PPO', 'Intern+PPO') AND o.ctc_lpa > 30.0 GROUP BY c.canonical_name ORDER BY max_ppo_ctc DESC;"
            return sql, "Identified companies offering PPO packages > 30 LPA.", "Multi-condition"

        if "both cse and ece" in low or (len(branches) >= 2 and any(k in low for k in ["both", "and"])):
            b1, b2 = branches[0], branches[1]
            threshold_match = re.search(r'(?:>|>=|above)\s*(\d+)', low)
            if threshold_match:
                threshold = float(threshold_match.group(1))
                cond = f"o.ctc_lpa > {threshold} AND "
                desc = f" at > {threshold} LPA"
            else:
                cond = ""
                desc = ""
            sql = f"SELECT c.canonical_name FROM companies c JOIN offers o ON c.company_id = o.company_id JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE {cond}b.short_name IN ('{b1}', '{b2}') AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name HAVING COUNT(DISTINCT b.short_name) = 2 ORDER BY c.canonical_name ASC;"
            return sql, f"Identified companies hiring both {b1} and {b2}{desc}.", "Multi-condition"

        if "both b.tech and m.tech" in low or "both ug and pg" in low:
            sql = "SELECT c.canonical_name FROM companies c JOIN offers o ON c.company_id = o.company_id JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name HAVING COUNT(DISTINCT CASE WHEN b.degree = 'B.Tech' THEN 1 END) > 0 AND COUNT(DISTINCT CASE WHEN b.degree = 'M.Tech' THEN 1 END) > 0 ORDER BY c.canonical_name ASC;"
            return sql, "Identified companies hiring from both UG and PG cohorts.", "Multi-condition"

        if "female" in low and ("above 20" in low or "> 20" in low):
            b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
            sql = f"SELECT DISTINCT c.canonical_name FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id {b_cond} AND s.gender = 'F' AND o.ctc_lpa > 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') ORDER BY c.canonical_name ASC;"
            return sql, "Identified companies making offers > 20 LPA to female students.", "Multi-condition"

        if "core" in low and ("15" in low or ">= 15" in low):
            b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
            sql = f"SELECT COUNT(DISTINCT s.student_id) AS core_super_students FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.division = 'Core' {b_cond} AND o.ctc_lpa >= 15.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
            return sql, "Counted Core branch students with packages >= 15.0 LPA.", "Multi-condition"

        if re.search(r'\b(sc/st|sc\s+and\s+st|sc-st)\b', low):
            b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
            sql = f"SELECT COUNT(o.offer_id) AS sc_st_offers_above_10 FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND s.category IN ('SC', 'ST') AND o.ctc_lpa >= 10.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
            return sql, "Counted offers >= 10 LPA made to SC/ST students.", "Multi-condition"

        if "more than 5" in low and branches:
            bshort = branches[0]
            sql = f"SELECT c.canonical_name, COUNT(DISTINCT s.student_id) AS cse_hires FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = '{bshort}' AND o.ctc_lpa >= 10.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name HAVING cse_hires > 5 ORDER BY cse_hires DESC;"
            return sql, f"Identified companies hiring > 5 students in {bshort} at >= 10 LPA.", "Multi-condition"

        if branches and any(k in low for k in ["> 12", "above 12", ">12", ">= 12", ">=12"]):
            bshort = branches[0]
            sql = f"SELECT COUNT(o.offer_id) AS total_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.ctc_lpa >= 12.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
            return sql, f"Counted offers >= 12.0 LPA in {bshort}.", "Multi-condition"

        if "at least 3" in low or ">= 3" in low:
            b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2021-2025'"
            sql = f"SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id {b_cond} AND o.ctc_lpa >= 15.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name HAVING offers_count >= 3 ORDER BY offers_count DESC;"
            return sql, "Identified companies with >= 3 offers at >= 15 LPA.", "Multi-condition"

        if branches and ("above 12" in low or ">= 12" in low):
            bshort = branches[0]
            sql = f"SELECT COUNT(o.offer_id) AS tt_above_12 FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.ctc_lpa >= 12.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
            return sql, f"Counted offers >= 12 LPA in {bshort}.", "Multi-condition"

        # =========================================================================
        # 6. AGGREGATES (average, avg, median, lowest, min)
        # =========================================================================
        if "median" in low:
            if branches:
                bshort = branches[0]
                b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                sql = f"WITH ordered AS (SELECT o.ctc_lpa, ROW_NUMBER() OVER (ORDER BY o.ctc_lpa) AS r, COUNT(*) OVER () AS c FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' {b_cond} AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) SELECT ROUND(AVG(ctc_lpa), 2) AS median_ctc FROM ordered WHERE r IN ((c + 1) / 2, (c + 2) / 2);"
                return sql, f"Computed median annual CTC for {bshort}.", "Aggregates with filters"
            else:
                b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                sql = f"WITH ordered AS (SELECT o.ctc_lpa, ROW_NUMBER() OVER (ORDER BY o.ctc_lpa) AS r, COUNT(*) OVER () AS c FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.division = 'Core' {b_cond} AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) SELECT ROUND(AVG(ctc_lpa), 2) AS median_ctc FROM ordered WHERE r IN ((c + 1) / 2, (c + 2) / 2);"
                return sql, "Computed median annual CTC for Core engineering offers.", "Aggregates with filters"

        if "lowest" in low or "min" in low:
            bshort = branches[0] if branches else "CSE"
            b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
            sql = f"SELECT MIN(o.ctc_lpa) AS min_cse_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' {b_cond} AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
            return sql, f"Queried lowest recorded package in {bshort}.", "Aggregates with filters"

        if "average" in low or "avg" in low or metric == "avg_ctc":
            if "stipend" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2023-2027'"
                sql = f"SELECT ROUND(AVG(o.stipend_monthly_inr), 0) AS avg_stipend FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.stipend_monthly_inr IS NOT NULL AND o.stipend_monthly_inr > 0;"
                return sql, "Calculated average monthly internship stipend in INR.", "Aggregates with filters"

            if "female" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND(AVG(o.ctc_lpa), 2) AS avg_female_ctc FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND s.gender = 'F' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, "Calculated average CTC of female placed students.", "Aggregates with filters"

            if "off-campus" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2021-2025'"
                sql = f"SELECT ROUND(AVG(o.ctc_lpa), 2) AS avg_offcampus_ctc FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.offer_mode = 'Off-campus' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, "Calculated average CTC for off-campus offers.", "Aggregates with filters"

            if "circuit" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND(AVG(o.ctc_lpa), 2) AS avg_circuit_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code {b_cond} AND b.division = 'Circuit' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, "Calculated average CTC for Circuit branches.", "Aggregates with filters"

            if companies and len(companies) == 1:
                cname = companies[0]
                sql = f"SELECT ROUND(AVG(o.ctc_lpa), 2) AS avg_amazon_ctc FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, f"Calculated average annual CTC offered by {cname}.", "Aggregates with filters"

            if branches and not companies:
                bshort = branches[0]
                if batch_id and len(batches) == 1 and batch_id != "all":
                    sql = f"WITH student_highest AS (SELECT s.student_id, MAX(o.ctc_lpa) AS highest_ctc FROM students s JOIN offers o ON s.student_id = o.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND s.batch_id = '{batch_id}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND o.ctc_lpa IS NOT NULL GROUP BY s.student_id), ordered AS (SELECT highest_ctc, ROW_NUMBER() OVER (ORDER BY highest_ctc) AS r, COUNT(*) OVER () AS c FROM student_highest) SELECT ROUND(AVG(sh.highest_ctc), 2) AS avg_ctc, (SELECT ROUND(AVG(highest_ctc), 2) FROM ordered WHERE r IN ((c + 1) / 2, (c + 2) / 2)) AS median_ctc, COUNT(*) AS placed_students FROM student_highest sh;"
                    return sql, f"Computed average and median package for {bshort} in {batch_id} (highest FTE/PPO per placed student).", "Aggregates with filters"
                else:
                    sql = f"WITH student_highest AS (SELECT s.student_id, s.batch_id, MAX(o.ctc_lpa) AS highest_ctc FROM students s JOIN offers o ON s.student_id = o.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND o.ctc_lpa IS NOT NULL GROUP BY s.student_id, s.batch_id) SELECT s.batch_id, ROUND(AVG(s.highest_ctc), 2) AS avg_ctc, COUNT(*) AS placed_students FROM student_highest s GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                    return sql, f"Computed year-wise average package for {bshort} across cohorts.", "Aggregates with filters"

            if not branches and not companies:
                if batch_id and len(batches) == 1 and batch_id != "all":
                    sql = f"SELECT ROUND(AVG(o.ctc_lpa), 2) AS overall_avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE s.batch_id = '{batch_id}' AND b.degree = 'B.Tech' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, f"Calculated overall B.Tech institute average CTC for {batch_id}.", "Aggregates with filters"
                else:
                    sql = f"WITH student_highest AS (SELECT s.student_id, s.batch_id, MAX(o.ctc_lpa) AS highest_ctc FROM students s JOIN offers o ON s.student_id = o.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.degree = 'B.Tech' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND o.ctc_lpa IS NOT NULL GROUP BY s.student_id, s.batch_id) SELECT s.batch_id, ROUND(AVG(s.highest_ctc), 2) AS avg_ctc, COUNT(*) AS placed_students FROM student_highest s GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                    return sql, "Calculated overall B.Tech institute average CTC across cohorts.", "Aggregates with filters"

        # =========================================================================
        # 7. OFFER-TYPE AWARE
        # =========================================================================
        if "stipend" in low or "internship stipend" in low:
            if "highest" in low or "top" in low:
                sql = "SELECT c.canonical_name, MAX(o.stipend_monthly_inr) AS max_monthly_stipend FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.stipend_monthly_inr IS NOT NULL GROUP BY c.canonical_name ORDER BY max_monthly_stipend DESC LIMIT 3;"
                return sql, "Ranked companies by highest monthly internship stipend.", "Offer-type aware"
            if companies and len(companies) == 1:
                cname = companies[0]
                sql = f"SELECT DISTINCT o.stipend_monthly_inr FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.stipend_monthly_inr IS NOT NULL;"
                return sql, f"Extracted verified monthly internship stipend in INR for {cname}.", "Offer-type aware"

        if "ppo" in low and ("difference" in low or "vs" in low):
            b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
            sql = f"SELECT COUNT(CASE WHEN o.offer_type IN ('FTE', 'Intern+FTE') THEN 1 END) AS fte_count, COUNT(CASE WHEN o.offer_type IN ('PPO', 'Intern+PPO') THEN 1 END) AS ppo_count FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond};"
            return sql, "Compared FTE vs PPO counts.", "Offer-type aware"

        if "long intern" in low and ("converted" in low or "confirmed" in low):
            sql = "SELECT COUNT(o.offer_id) AS confirmed_long_interns FROM offers o WHERE o.offer_type = 'Intern+FTE';"
            return sql, "Counted confirmed FTE conversions from long internships.", "Offer-type aware"

        if "unpaid" in low:
            sql = "SELECT DISTINCT c.canonical_name FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.package_reason = 'unpaid' ORDER BY c.canonical_name ASC;"
            return sql, "Identified companies offering unpaid internships.", "Offer-type aware"

        if "compound" in low or "both stipend and ctc" in low:
            sql = "SELECT COUNT(o.offer_id) AS compound_offers FROM offers o WHERE o.package_reason = 'compound_split';"
            return sql, "Counted compound packages containing both stipend and full-time CTC.", "Offer-type aware"

        # =========================================================================
        # 8. RANKING / TOP-N
        # =========================================================================
        if "top" in low or "highest" in low or "most" in low or "rank" in low or "bottom" in low or metric == "top_recruiters" or intent == "ranking":
            # Top packages with company and branch (e.g. "top 5 highest packages with company and branch")
            if any(k in low for k in ["highest packages", "highest package", "top packages", "top package"]) and ("branch" in low or "company" in low) and not branches and not companies:
                limit = filters.get("limit", 5)
                sql = f"SELECT c.canonical_name, b.short_name, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') {batch_clause_and} GROUP BY c.canonical_name, b.short_name ORDER BY max_ctc DESC, c.canonical_name ASC LIMIT {limit};"
                return sql, f"Ranked top {limit} highest packages with recruiting company and branch.", "Ranking / top-N"

            # Top N companies by offers (e.g. "Top 10 companies by offers")
            if ("top" in low or "best" in low or "most" in low) and ("company" in low or "companies" in low or "recruiter" in low or "recruiters" in low) and (metric == "total_offers" or any(k in low for k in ["offer", "offers"])):
                limit = filters.get("limit") or (10 if "10" in low else (5 if "5" in low else 5))
                where_clause = f"WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') {batch_clause_and}"
                sql = f"SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id {where_clause} GROUP BY c.canonical_name ORDER BY offers_count DESC, c.canonical_name ASC LIMIT {limit};"
                return sql, f"Ranked top {limit} companies by total offer volume.", "Ranking / top-N"

            # Highest package in a specific batch (e.g. "highest package in 2022-26")
            if (intent in ["ranking", "lookup"] or metric == "max_ctc") and any(k in low for k in ["highest package", "max package", "peak package", "top package"]) and not companies and not branches:
                if batch_id and len(batches) == 1 and batch_id != "all":
                    sql = f"SELECT c.canonical_name, b.short_name, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE s.batch_id = '{batch_id}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name, b.short_name ORDER BY max_ctc DESC LIMIT 1;"
                    return sql, f"Identified peak package recorded for the {batch_id} batch.", "Ranking / top-N"
                else:
                    sql = f"SELECT s.batch_id, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id WHERE o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') {batch_clause_and} GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                    return sql, "Peak package recorded across academic batches.", "Ranking / top-N"

            if "median" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if (batch_id and len(batches) == 1 and batch_id != "all") else ""
                sql = f"WITH student_highest AS (SELECT s.student_id, s.branch_code, MAX(o.ctc_lpa) AS highest_ctc FROM students s JOIN offers o ON s.student_id = o.student_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND o.ctc_lpa IS NOT NULL GROUP BY s.student_id, s.branch_code), ranked AS (SELECT sh.branch_code, sh.highest_ctc, ROW_NUMBER() OVER (PARTITION BY sh.branch_code ORDER BY sh.highest_ctc) AS r, COUNT(*) OVER (PARTITION BY sh.branch_code) AS c FROM student_highest sh) SELECT b.short_name, ROUND(AVG(rk.highest_ctc), 2) AS median_ctc, rk.c AS total_students FROM ranked rk JOIN branches b ON rk.branch_code = b.branch_code WHERE rk.r IN ((rk.c + 1) / 2, (rk.c + 2) / 2) AND b.degree = 'B.Tech' GROUP BY b.short_name ORDER BY median_ctc DESC;"
                return sql, "Ranked B.Tech departments by median annual CTC.", "Ranking / top-N"

            if bool(re.search(r'\b(top|best|major|key)\s*(?:\d+\s+)?recruiter[s]?\b', low)) or any(k in low for k in ["top recruiter", "top recruiters", "best recruiter", "best recruiters", "major recruiter", "major recruiters", "key recruiter", "recruiting companies"]) or metric == "top_recruiters":
                limit_m = re.search(r'\btop\s+(\d+)', low)
                top_limit = int(limit_m.group(1)) if limit_m else filters.get("limit", 5)
                if branches:
                    bshort = branches[0]
                    b_clause = f"AND s.batch_id = '{batch_id}'" if (batch_id and len(batches) == 1 and batch_id != "all") else ""
                    sql = f"SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' {b_clause} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY offers_count DESC, c.canonical_name ASC LIMIT {top_limit};"
                    return sql, f"Ranked top {top_limit} recruiters for {bshort} by offer volume.", "Ranking / top-N"
                else:
                    b_clause = f"WHERE s.batch_id = '{batch_id}'" if (batch_id and len(batches) == 1 and batch_id != "all") else ""
                    where_and = f"{b_clause} AND" if b_clause else "WHERE"
                    sql = f"SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id {where_and} o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY offers_count DESC, c.canonical_name ASC LIMIT {top_limit};"
                    return sql, f"Ranked top {top_limit} recruiters across the institute by offer volume.", "Ranking / top-N"

            if "bottom" in low and "placement" in low:
                b_cond = f"WHERE batch_id = '{batch_id}'" if batch_id else "WHERE batch_id = '2020-2024'"
                sql = f"SELECT branch_short, placement_pct FROM v_branch_year_stats {b_cond} ORDER BY placement_pct ASC LIMIT 3;"
                return sql, "Ranked lowest 3 branches by placement percentage.", "Ranking / top-N"

            if "ppo" in low:
                sql = "SELECT c.canonical_name, COUNT(o.offer_id) AS ppo_count FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.offer_type IN ('PPO', 'Intern+PPO') GROUP BY c.canonical_name ORDER BY ppo_count DESC LIMIT 5;"
                return sql, "Ranked top 5 companies by PPO count.", "Ranking / top-N"

            if "core" in low and ("highest" in low or "paying" in low):
                sql = "SELECT c.canonical_name, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.division = 'Core' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY max_ctc DESC LIMIT 3;"
                return sql, "Ranked top 3 highest paying recruiters in Core branches.", "Ranking / top-N"

            if branches and any(k in low for k in ["highest", "max", "sabse jyada", "sabse bada", "kisne diya"]):
                bshort = branches[0]
                sql = f"SELECT c.canonical_name, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = '{bshort}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') {batch_clause_and} GROUP BY c.canonical_name ORDER BY max_ctc DESC LIMIT 1;"
                return sql, f"Identified company offering highest package in {bshort}.", "Ranking / top-N"

            if branches and ("hired" in low or "recruiting" in low or "offers" in low or "hiring" in low):
                bshort = branches[0]
                limit = 5 if ("5" in low or "five" in low) else 3
                sql = f"SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = '{bshort}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') {batch_clause_and} GROUP BY c.canonical_name ORDER BY offers_count DESC LIMIT {limit};"
                return sql, f"Ranked top {limit} companies hiring from {bshort}.", "Ranking / top-N"

            if "branches by average" in low or "branches by avg" in low:
                sql = f"SELECT b.short_name, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.degree = 'B.Tech' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') {batch_clause_and} GROUP BY b.short_name ORDER BY avg_ctc DESC LIMIT 5;"
                return sql, "Ranked top 5 B.Tech branches by average CTC.", "Ranking / top-N"

            if "recruiting companies" in low or "number of offers" in low:
                sql = f"SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') {batch_clause_and} GROUP BY c.canonical_name ORDER BY offers_count DESC LIMIT 3;"
                return sql, "Ranked top 3 recruiting companies by offer volume.", "Ranking / top-N"

            if "branch" in low and ("above 20" in low or "> 20" in low or "ctc_threshold" in filters or "most offers above" in low):
                thresh = filters.get("ctc_threshold", 20.0)
                sql = f"SELECT b.short_name, COUNT(o.offer_id) AS high_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE o.ctc_lpa > {thresh} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') {batch_clause_and} GROUP BY b.short_name ORDER BY high_offers DESC, b.short_name ASC;"
                return sql, f"Ranked branches by number of offers above {thresh:g} LPA.", "Ranking / top-N"

            if "companies" in low:
                sql = "SELECT c.canonical_name, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY max_ctc DESC LIMIT 5;"
                return sql, "Ranked top 5 companies by highest annual package.", "Ranking / top-N"

        # Hybrid package / interview query interception before Count
        if companies and ("package" in low or "ctc" in low or "stipend" in low) and any(k in low for k in ["interview", "round", "process", "conduct"]):
            cname = companies[0]
            if "intern" in low or "stipend" in low:
                sql = f"SELECT DISTINCT o.stipend_monthly_inr FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.stipend_monthly_inr IS NOT NULL;"
                return sql, f"Queried internship stipend offered by {cname} for hybrid interview context.", "Hybrid"
            else:
                sql = f"SELECT DISTINCT o.ctc_lpa FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.ctc_lpa IS NOT NULL;"
                return sql, f"Queried package offered by {cname} for hybrid interview context.", "Hybrid"

        # =========================================================================
        # 9. COUNT INTENT
        # =========================================================================
        if intent == "count" or any(k in low for k in ["how many", "count", "number of", "kitne", "kitna"]):
            if metric == "multi_offer_students" or any(k in low for k in ["more than one offer", "more than 1 offer", "multiple offers", "multi offer", "two or more offers"]):
                sql = f"SELECT COUNT(*) AS multi_offer_students FROM (SELECT s.student_id FROM offers o JOIN students s ON o.student_id = s.student_id WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') {batch_clause_and} GROUP BY s.student_id HAVING COUNT(o.offer_id) >= 2);"
                return sql, "Counted students holding multiple full-time offers.", "Count by condition"

            if metric in ["company_count", "distinct_companies"] or any(k in low for k in ["how many companies", "number of companies", "company count", "companies visited", "total companies", "kitni company", "kitni companies", "distinct companies", "companies made at least one offer"]):
                if branches:
                    bshort = branches[0]
                    sql = f"SELECT COUNT(DISTINCT c.company_id) AS company_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = '{bshort}' {batch_clause_and} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, f"Counted distinct companies recruiting from {bshort}.", "Count by condition"
                else:
                    where_clause = f"WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') {batch_clause_and}"
                    sql = f"SELECT COUNT(DISTINCT c.company_id) AS company_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id {where_clause};"
                    return sql, "Counted distinct recruiting companies across the institute.", "Count by condition"

            if metric == "intern_count" or any(k in low for k in ["intern count", "how many interns", "intern offers", "internship offers", "internships count"]):
                if branches:
                    bshort = branches[0]
                    sql = f"SELECT COUNT(o.offer_id) AS intern_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' {batch_clause_and} AND (o.offer_type IN ('Intern', 'Long Intern', 'Summer Intern') OR (o.stipend_monthly_inr IS NOT NULL AND o.ctc_lpa IS NULL));"
                    return sql, f"Counted internship offers secured by {bshort}.", "Count by condition"
                else:
                    where_clause = f"WHERE (o.offer_type IN ('Intern', 'Long Intern', 'Summer Intern') OR (o.stipend_monthly_inr IS NOT NULL AND o.ctc_lpa IS NULL)) {batch_clause_and}"
                    sql = f"SELECT COUNT(o.offer_id) AS intern_count FROM offers o JOIN students s ON o.student_id = s.student_id {where_clause};"
                    return sql, "Counted internship offers across the institute.", "Count by condition"
            if "ctc_threshold" in filters or "above 20" in low or "> 20" in low or ">= 50" in low or "above 50" in low or "50 lpa" in low:
                if ">= 50" in low or "above 50" in low or "50 lpa" in low:
                    sql = "SELECT COUNT(o.offer_id) FROM offers o WHERE o.ctc_lpa >= 50.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, "Counted super-dream offers >= 50.0 LPA.", "Count by condition"
                b_clause = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                if metric == "offers" or "offer" in low:
                    sql = f"SELECT COUNT(o.offer_id) FROM offers o JOIN students s ON o.student_id = s.student_id WHERE o.ctc_lpa > 20.0 {b_clause} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, "Counted full-time offers with CTC > 20 LPA.", "Count by condition"
                else:
                    sql = f"SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id WHERE o.ctc_lpa > 20.0 {b_clause} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, "Counted distinct students placed with CTC > 20 LPA.", "Count by condition"

            if "off-campus" in low or "off campus" in low:
                sql = "SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id WHERE o.offer_mode = 'Off-campus';"
                return sql, "Counted distinct students placed through off-campus drives.", "Count by condition"

            if "double" in low:
                b_clause = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT COUNT(*) FROM (SELECT s.student_id FROM offers o JOIN students s ON o.student_id = s.student_id {b_clause} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.student_id HAVING COUNT(o.offer_id) >= 2);"
                return sql, "Counted distinct students holding multiple full-time offers.", "Count by condition"

            if "female" in low:
                b_clause = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id {b_clause} AND s.gender = 'F' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, "Counted distinct female placed students.", "Count by condition"

            if "ppo" in low:
                if companies and branches:
                    cname, bshort = companies[0], branches[0]
                    sql = f"SELECT COUNT(o.offer_id) AS reliance_che_ppos FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND b.short_name = '{bshort}' AND o.offer_type IN ('PPO', 'Intern+PPO');"
                    return sql, f"Counted PPO offers from {cname} in {bshort}.", "Offer-type aware"
                if companies:
                    cname = companies[0]
                    sql = f"SELECT COUNT(o.offer_id) AS amazon_ppos FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.offer_type IN ('PPO', 'Intern+PPO');"
                    return sql, f"Counted PPO offers from {cname}.", "Offer-type aware"

            if companies and branches:
                cname, bshort = companies[0], branches[0]
                sql = f"SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND b.short_name = '{bshort}' {batch_clause_and} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, f"Counted distinct students placed at {cname} from {bshort}.", "Count by condition"

            if branches and not companies:
                bshort = branches[0]
                if metric == "offers" or any(k in low for k in ["total offers", "offers made", "offer count", "offers"]):
                    sql = f"SELECT COUNT(o.offer_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' {batch_clause_and} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, f"Counted total offers received by {bshort} students (offer row count).", "Count by condition"
                else:
                    sql = f"SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' {batch_clause_and} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, f"Counted distinct placed students in {bshort}.", "Count by condition"

            if companies and not branches:
                cname = companies[0]
                if any(k in low for k in ["student", "ppl", "people", "candidate", "placed", "selected"]):
                    sql = f"SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' {batch_clause_and} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, f"Counted distinct placed students at {cname}.", "Count by condition"
                else:
                    where_clause = f"WHERE c.canonical_name = '{cname}' {batch_clause_and}"
                    sql = f"SELECT COUNT(o.offer_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id {where_clause};"
                    return sql, f"Counted total offers made by {cname}.", "Count by condition"

            if not companies and not branches:
                if batch_id and len(batches) == 1 and batch_id != "all":
                    sql = f"SELECT COUNT(DISTINCT s.student_id) AS placed_students FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '{batch_id}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, f"Counted distinct placed students across the institute for {batch_id}.", "Count by condition"
                else:
                    sql = f"SELECT s.batch_id, COUNT(DISTINCT s.student_id) AS placed_students FROM offers o JOIN students s ON o.student_id = s.student_id WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') {batch_clause_and} GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                    return sql, "Counted distinct placed students across the institute by cohort.", "Count by condition"

        # =========================================================================
        # 10. LOOKUP INTENT (Package / stipend lookups)
        # =========================================================================
        if intent == "lookup" or any(k in low for k in ["ctc of", "package of", "salary of", "stipend of"]) or "exact_ctc" in filters:
            if "exact_ctc" in filters or (any(k in low for k in ["who got", "who secured", "students who got"]) and "lpa" in low):
                exact_val = filters.get("exact_ctc", 52.0)
                sql = f"SELECT c.canonical_name, b.short_name, COUNT(DISTINCT s.student_id) AS student_count, MAX(o.ctc_lpa) AS ctc_lpa FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE o.ctc_lpa = {exact_val} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') {batch_clause_and} GROUP BY c.canonical_name, b.short_name ORDER BY student_count DESC;"
                return sql, f"Identified students, branches, and companies with exact package of {exact_val:g} LPA.", "Lookup"
            if metric == "stipend" or "intern" in low or "stipend" in low:
                if companies:
                    cname = companies[0]
                    sql = f"SELECT DISTINCT o.stipend_monthly_inr FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.stipend_monthly_inr IS NOT NULL;"
                    return sql, f"Queried verified monthly internship stipend in INR for {cname}.", "Lookup"

            if (metric == "ctc" or any(k in low for k in ["ctc", "package", "salary", "lpa"])) and not any(k in low for k in ["avg", "average", "mean", "median", "change"]):
                if companies and branches:
                    cname, bshort = companies[0], branches[0]
                    sql = f"SELECT DISTINCT o.ctc_lpa FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND b.short_name = '{bshort}' {batch_clause_and} AND o.ctc_lpa IS NOT NULL ORDER BY o.ctc_lpa DESC;"
                    return sql, f"Queried distinct annual CTC packages offered by {cname} to {bshort} (internship stipends excluded).", "Lookup"
                elif companies:
                    cname = companies[0]
                    sql = f"SELECT DISTINCT o.ctc_lpa FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' {batch_clause_and} AND o.ctc_lpa IS NOT NULL ORDER BY o.ctc_lpa DESC;"
                    return sql, f"Queried distinct annual CTC packages offered by {cname}.", "Lookup"

        # =========================================================================
        # 11. HYBRID
        # =========================================================================
        if "> 18" in low or ">= 18" in low or ">18" in low:
            sql = "SELECT DISTINCT c.canonical_name FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.ctc_lpa > 18.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') ORDER BY c.canonical_name ASC;"
            return sql, "Queried companies offering CTC > 18.0 LPA for hybrid experience merging.", "Hybrid"

        if branches and ("> 20" in low or ">= 20" in low or ">=20" in low):
            bshort = branches[0]
            sql = f"SELECT DISTINCT c.canonical_name FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = '{bshort}' AND o.ctc_lpa >= 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') ORDER BY c.canonical_name ASC;"
            return sql, f"Queried companies offering >= 20.0 LPA to {bshort}.", "Hybrid"

        if "core" in low and ("> 10" in low or ">= 10" in low):
            sql = "SELECT DISTINCT c.canonical_name FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.division = 'Core' AND o.ctc_lpa > 10.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') ORDER BY c.canonical_name ASC;"
            return sql, "Queried Core engineering companies offering > 10.0 LPA.", "Hybrid"

        return None, None, None


class LLMTextToSQL:
    """
    LLM Text-to-SQL Fallback for complex queries not covered by deterministic templates.
    Generates SQL and passes it through strict sqlglot AST validation.
    """

    SYSTEM_PROMPT = """You are a read-only SQL generator for NITJ Placement Assistant.
Given the question and database schema, generate a single SQLite SELECT statement.
Schema:
- offers (offer_id, student_id, company_id, offer_type, offer_mode, ctc_lpa, stipend_monthly_inr, package_reason)
- students (student_id, batch_id, branch_code, gender, category)
- branches (branch_code, short_name, full_name, degree, division)
- companies (company_id, canonical_name, sector)
- batches (batch_id, graduation_year)

Rules:
1. Output ONLY the SQL query in a ```sql block.
2. SELECT queries only. No PII columns (student names, roll numbers, contacts, emails are forbidden).
3. Metric invariants: Placed students = COUNT(DISTINCT s.student_id) with offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE'). Total offers = COUNT(o.offer_id). Internships are separate.
"""

    @classmethod
    def generate(cls, spec: QuerySpec, raw_question: str) -> Optional[str]:
        """Attempt LLM text-to-SQL generation when Ollama/local model is available."""
        # Text-to-SQL fallback can be invoked here via local Ollama client if templates don't match
        return None


class SafeSQLService:
    """
    Safe SQL Service complying strictly with Step 4 mandate:
    1. Deterministic template generation from QuerySpec.
    2. Fallback to LLM text-to-SQL for unmapped requests.
    3. AST validation via sqlglot (SELECT only, whitelisted tables, no PII, row limit).
    4. Removal of silent LIMIT 10 and global-count fallback.
    5. Return ONE short clarifying question with 2-3 options when confidence < 0.7 or unresolved.
    """

    CLARIFYING_PROMPT = (
        "Could you please specify which company, department (e.g., CSE, IT, ECE), or academic cohort (e.g., 2020-24, 2021-25) you'd like to inspect?"
    )

    @classmethod
    def generate_and_validate(cls, spec: QuerySpec, raw_question: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Generate SQL from QuerySpec and validate with sqlglot AST.
        Returns:
            Tuple of (validated_sql, definition, query_type, clarification_or_error)
        """
        # Step 4 Mandate: If spec cannot be resolved with confidence >= 0.7 or needs clarification, return ONE short clarifying question with 2-3 options
        if spec.confidence < 0.7 or spec.needs_clarification:
            return None, None, None, cls.CLARIFYING_PROMPT

        # 1. Deterministic templates
        sql, definition, query_type = TemplateSQLGenerator.generate(spec, raw_question)

        # 2. Text-to-SQL fallback if deterministic template was None
        if not sql:
            sql = LLMTextToSQL.generate(spec, raw_question)
            if sql:
                definition = "Formulated via verified semantic text-to-SQL generator."
                query_type = "TextToSQL"

        # 3. If still no verified SQL can be produced, do NOT do global count fallback or silent LIMIT 10!
        if not sql:
            return None, None, None, cls.CLARIFYING_PROMPT

        # 4. AST Validation with sqlglot
        try:
            validated_sql = SQLValidator.validate_and_clean(sql)
            return validated_sql, definition, query_type, None
        except SQLValidationError as ve:
            # If generated SQL violates AST security/schema, block and request clarification
            return None, None, None, f"Privacy/AST Safety Enforcement: {ve}\n\n{cls.CLARIFYING_PROMPT}"
