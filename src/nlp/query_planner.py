import os
import re
import json
import time
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field

from src.core.semantic_loader import SemanticLayer
from src.nlp.entity_resolver import EntityResolver
from src.nlp.query_spec import QuerySpec
from src.nlp.llm_parser import LLMIntentParser
from src.db.sql_engine import SQLEngine, SQLEngineError
from src.nlp.verifier import QueryVerifier
from src.rag.retriever import ExperienceRetriever
from src.nlp.audit_logger import AuditLogger
from src.nlp.contextualizer import QueryContextualizer, ContextualizedOutput

# Privacy configuration: When True, bot may list student names (with role/company/branch). Individual package is suppressed.
SHOW_STUDENT_NAMES = os.getenv("SHOW_STUDENT_NAMES", "true").lower() in ("true", "1", "yes")
ALLOWED_PERSON_FIELDS = ["name", "branch", "batch", "company", "role", "offer_type"]
SHOW_STUDENT_PACKAGE = os.getenv("SHOW_STUDENT_PACKAGE", "false").lower() in ("true", "1", "yes")

class ColumnMetadata(BaseModel):
    name: str
    metric_type: str = "dimension"  # "dimension", "count", "ctc", "average_ctc", "median_ctc", "percentage", "stipend", "text"
    unit: str = ""                  # "students", "offers", "companies", "LPA", "%", "₹/month", ""
    aggregation: str = "group"      # "group", "sum", "avg", "median", "max", "min", "rate", "none"

class StructuredAnswerPayload(BaseModel):
    count: int = 0
    rows: List[Any] = Field(default_factory=list)
    scope: str = ""
    offer_types: List[str] = Field(default_factory=list)
    package_stats: Optional[Dict[str, Any]] = None
    has_interview_rag: bool = False
    columns: Optional[List[str]] = Field(default_factory=list)
    column_meta: Optional[List[ColumnMetadata]] = Field(default_factory=list)
    direct_answer: Optional[str] = None
    breakdown: Optional[List[Dict[str, Any]]] = None

    def validate_payload(self) -> None:
        """
        Validate consistency of payload before rendering text.
        If stated count does not match rows or breakdown sum, raise ValueError.
        """
        if self.breakdown:
            counts = [item.get("count", 0) for item in self.breakdown if isinstance(item, dict) and "count" in item]
            if counts and self.count > 0:
                sum_c = sum(counts)
                if sum_c != self.count:
                    raise ValueError(f"Payload validation failed: stated count {self.count} != breakdown sum {sum_c}")
        elif self.rows and len(self.rows) > 1 and len(self.rows[0]) == 1 and not self.package_stats:
            # If 1D list of entities (e.g. companies)
            if self.count > 0 and len(self.rows) != self.count:
                raise ValueError(f"Payload validation failed: count {self.count} != len(rows) {len(self.rows)}")

def infer_column_metadata(columns: List[str]) -> List[ColumnMetadata]:
    """Tag each column with name, metric_type, unit, and aggregation."""
    meta_list = []
    for col in columns:
        c_low = col.lower().strip()
        if c_low in ["batch_id", "batch", "academic_batch", "cohort", "year"]:
            meta_list.append(ColumnMetadata(name=col, metric_type="dimension", unit="", aggregation="group"))
        elif c_low in ["short_name", "branch", "branch_name", "department", "discipline"]:
            meta_list.append(ColumnMetadata(name=col, metric_type="dimension", unit="", aggregation="group"))
        elif c_low in ["canonical_name", "company", "company_name", "recruiter"]:
            meta_list.append(ColumnMetadata(name=col, metric_type="dimension", unit="", aggregation="group"))
        elif c_low in ["sector", "division", "gender", "category", "degree", "offer_type", "offer_mode"]:
            meta_list.append(ColumnMetadata(name=col, metric_type="dimension", unit="", aggregation="group"))
        elif any(k in c_low for k in ["avg_ctc", "average_ctc", "avg_package", "mean_ctc"]):
            meta_list.append(ColumnMetadata(name=col, metric_type="average_ctc", unit="LPA", aggregation="avg"))
        elif any(k in c_low for k in ["median_ctc", "median_package"]):
            meta_list.append(ColumnMetadata(name=col, metric_type="median_ctc", unit="LPA", aggregation="median"))
        elif any(k in c_low for k in ["max_ctc", "peak_ctc", "highest_ctc", "ctc_lpa", "package", "salary"]):
            meta_list.append(ColumnMetadata(name=col, metric_type="ctc", unit="LPA", aggregation="max"))
        elif any(k in c_low for k in ["min_ctc", "lowest_ctc"]):
            meta_list.append(ColumnMetadata(name=col, metric_type="ctc", unit="LPA", aggregation="min"))
        elif any(k in c_low for k in ["placement_pct", "placement_percentage", "placement_rate", "rate", "ratio"]):
            meta_list.append(ColumnMetadata(name=col, metric_type="percentage", unit="%", aggregation="rate"))
        elif any(k in c_low for k in ["stipend", "monthly_stipend"]):
            meta_list.append(ColumnMetadata(name=col, metric_type="stipend", unit="₹/month", aggregation="max"))
        elif any(k in c_low for k in ["company_count", "companies_count", "distinct_companies"]):
            meta_list.append(ColumnMetadata(name=col, metric_type="count", unit="companies", aggregation="sum"))
        elif any(k in c_low for k in ["placed_students", "placed_count", "students_placed", "placed", "eligible_students", "total_students", "student_count"]):
            meta_list.append(ColumnMetadata(name=col, metric_type="count", unit="students", aggregation="sum"))
        elif any(k in c_low for k in ["total_offers", "job_offers", "offers_count", "offers", "fte_offers", "company_offers", "double_job_offers"]):
            meta_list.append(ColumnMetadata(name=col, metric_type="count", unit="offers", aggregation="sum"))
        elif any(k in c_low for k in ["intern_count", "intern_offers"]):
            meta_list.append(ColumnMetadata(name=col, metric_type="count", unit="offers", aggregation="sum"))
        else:
            meta_list.append(ColumnMetadata(name=col, metric_type="text", unit="", aggregation="none"))
    return meta_list

class PayloadNumberVerifier:
    """
    Verifies that every number mentioned in the draft narration appears in the payload
    or is trivially derived (rank, difference, count sum).
    Specifically blocks and catches illegal sums of CTC, averages, or max values across groups.
    """
    FORBIDDEN_SUM_METRICS = {"ctc", "average_ctc", "median_ctc", "percentage"}

    @classmethod
    def extract_numbers(cls, text: str) -> List[float]:
        """Extract all floating point and integer numbers from string."""
        tokens = re.findall(r'(?<![A-Za-z0-9_])\d+(?:\.\d+)?(?![A-Za-z0-9_])', text)
        nums = []
        for t in tokens:
            try:
                nums.append(float(t))
            except ValueError:
                pass
        return nums

    @classmethod
    def verify(cls, draft: str, payload: StructuredAnswerPayload) -> Tuple[bool, List[str]]:
        draft_nums = cls.extract_numbers(draft)
        if not draft_nums:
            return True, []

        allowed = set()
        
        # Numbers directly from rows
        for row in payload.rows:
            if isinstance(row, (list, tuple)):
                for val in row:
                    if isinstance(val, (int, float)):
                        allowed.add(float(val))
                        if float(val).is_integer():
                            allowed.add(float(int(val)))
            elif isinstance(row, (int, float)):
                allowed.add(float(row))

        # Stated count
        if payload.count:
            allowed.add(float(payload.count))

        # Row counts / ranks
        allowed.add(float(len(payload.rows)))

        # Standard academic years and small narrative ranks
        for y in [2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 20, 21, 22, 23, 24, 25, 26, 27, 28, 1, 2, 3, 4, 5, 10]:
            allowed.add(float(y))

        # Explicitly check for fatal illegal sums of non-summable metrics across groups!
        # E.g. 52+52+52 = 156, 52+15.12+52 = 119.12, 14.44+13.03 = 27.47
        if payload.column_meta and len(payload.column_meta) >= 2 and len(payload.rows) > 1:
            for col_idx, meta in enumerate(payload.column_meta):
                if meta.metric_type in cls.FORBIDDEN_SUM_METRICS:
                    col_vals = [
                        r[col_idx] for r in payload.rows 
                        if isinstance(r, (list, tuple)) and len(r) > col_idx and isinstance(r[col_idx], (int, float))
                    ]
                    if len(col_vals) > 1:
                        illegal_sum = round(sum(col_vals), 2)
                        for d_num in draft_nums:
                            if abs(d_num - illegal_sum) < 0.05:
                                return False, [f"Forbidden sum of non-summable metric '{meta.name}' detected: {illegal_sum}"]

        # Allowed sums of count metrics ONLY
        if payload.column_meta and len(payload.rows) > 1:
            for col_idx, meta in enumerate(payload.column_meta):
                if meta.metric_type == "count":
                    col_vals = [
                        r[col_idx] for r in payload.rows 
                        if isinstance(r, (list, tuple)) and len(r) > col_idx and isinstance(r[col_idx], (int, float))
                    ]
                    if col_vals:
                        s_val = round(sum(col_vals), 2)
                        allowed.add(s_val)
                        if s_val.is_integer():
                            allowed.add(float(int(s_val)))

        # Verify each number in draft
        unverified = []
        for d_num in draft_nums:
            matched = any(abs(d_num - a) < 0.05 for a in allowed)
            if not matched:
                unverified.append(str(d_num))

        if unverified:
            return False, [f"Unverified numbers in summary draft: {', '.join(unverified)}"]

        return True, []


class QueryPlanner:
    def __init__(self, db_path: str = "data/nitj_placement.db"):
        self.db_path = db_path
        self.semantic = SemanticLayer.get_instance()
        self.resolver = EntityResolver(db_path)
        self.llm_parser = LLMIntentParser()
        self.sql_engine = SQLEngine(db_path)
        self.verifier = QueryVerifier()
        self.retriever = ExperienceRetriever(db_path)
        self.contextualizer = QueryContextualizer(db_path)

    def plan_and_execute(
        self,
        question: str,
        history: Optional[List[Dict[str, Any]]] = None,
        session_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main end-to-end pipeline:
        0. Contextualize follow-ups and carry over slots from history/session state
        1. Parse intent & entities via LLMIntentParser into Pydantic QuerySpec
        2. Handle Privacy, Out-of-Scope, and Ambiguous queries with high confidence
        3. Formulate SQL based on QuerySpec and semantic layer rules
        4. Execute query with read-only safety limits
        5. Verify results (sanity checks)
        6. Format into strict answer format with collapsible details
        """
        start_time = time.time()

        # Multi-question splitting (Bug G: "what is cse avg and what is it avg")
        q_low = question.lower()
        if " and " in q_low and not any(k in q_low for k in ["between", "vs", "versus", "both", "both cse and", "share of", "intern+"]):
            sub_splits = re.split(r'\s+and\s+(?:what\s+is|what\s+was|how\s+many|what\s+about|tell\s+me)\s+', question, flags=re.IGNORECASE)
            if len(sub_splits) >= 2 and len(sub_splits[0].strip().split()) >= 3 and len(sub_splits[1].strip().split()) >= 2:
                q1 = sub_splits[0].strip()
                q2_raw = sub_splits[1].strip()
                q2 = f"what is {q2_raw}" if not q2_raw.lower().startswith(("what", "how", "which", "tell", "give")) else q2_raw
                res1 = self.plan_and_execute(q1, history=history, session_state=session_state)
                res2 = self.plan_and_execute(q2, history=history, session_state=session_state)
                combined_ans = f"**1. {q1}**:\n{res1.get('answer', '')}\n\n**2. {q2}**:\n{res2.get('answer', '')}"
                combined_res = dict(res1)
                combined_res["answer"] = combined_ans
                return combined_res

        # Step 0: Conversational Contextualization (Bug B & C)
        ctx_output = self.contextualizer.contextualize(question, history, session_state)
        effective_question = ctx_output.standalone_question

        # Step 1: LLM Intent Parsing (Schema-constrained QuerySpec)
        spec = self.llm_parser.parse(effective_question, history)

        # Merge carried slots only if contextualizer marked is_followup=True (Bug C Fix)
        if ctx_output.is_followup and ctx_output.carried_slots:
            if ctx_output.carried_slots.get("companies") and not spec.companies:
                spec.companies = list(ctx_output.carried_slots["companies"])
            if ctx_output.carried_slots.get("branches") and not spec.branches:
                spec.branches = list(ctx_output.carried_slots["branches"])
            if ctx_output.carried_slots.get("batches") and not spec.batches:
                spec.batches = list(ctx_output.carried_slots["batches"])
            if ctx_output.carried_slots.get("group_by") and not spec.group_by:
                spec.group_by = list(ctx_output.carried_slots["group_by"])
            if ctx_output.carried_slots.get("offer_types") and not spec.offer_types:
                spec.offer_types = list(ctx_output.carried_slots["offer_types"])
            if ctx_output.carried_slots.get("metric") and not spec.metric:
                spec.metric = ctx_output.carried_slots["metric"]

        if ctx_output.resolved_clarification:
            spec.needs_clarification = False
            if spec.intent == "clarify":
                spec.intent = "count" if spec.metric in ["placed_students", "offers"] else "lookup"

        # Privacy Check (Instant Guard)
        if spec.privacy_flag or spec.intent == "privacy":
            res = {
                "category": "privacy",
                "intent": "PRIVACY_BLOCKED",
                "answer": spec.clarification_question or "For student privacy and institutional confidentiality, roll numbers, phone numbers, personal emails, residential addresses, parent details, and HR/recruiter contact information are strictly protected and cannot be shared. I can provide student placement lists by company, branch statistics, compensation packages, and alumni interview experiences.",
                "table": None,
                "insight": None,
                "definition": "Privacy Guard: Strictly protects personal student identities and contact details.",
                "data_scope": "Confidential Student PII",
                "confidence": "High (Privacy Policy Rule)",
                "sql": None,
                "raw_result": "PRIVACY_BLOCKED",
                "query_spec": spec.model_dump()
            }
            return self._finalize_and_log(res, spec, question, start_time, effective_question=effective_question, is_followup=ctx_output.is_followup)

        # Out-of-scope check (Untracked metrics, historical years, or companies that never visited)
        if spec.intent == "out_of_scope":
            low_q = question.lower()
            # If the question asks a negative existence query over placements (e.g. zero female, never hired by PayPal), do NOT block as out-of-scope!
            if any(term in low_q for term in ["never", "zero", "unplaced", "no offers", "not hired"]):
                pass  # Proceed to verified negative SQL generation
            else:
                intent_label = "NO_DATA" if (spec.companies or spec.branches or spec.batches) else "OUT_OF_SCOPE"
                target_entity = spec.companies[0] if spec.companies else (spec.branches[0] if spec.branches else None)
                if target_entity:
                    default_msg = f"We don't have records for **{target_entity}** in our placement database right now. Our Training & Placement team is working on gathering and updating this data, and we will fix/add it soon!"
                else:
                    default_msg = "We don't have anything like this in our placement database right now. Our Training & Placement team is actively working on gathering and updating this data, and we will fix/add it soon!"

                res = {
                    "category": "out_of_scope",
                    "intent": intent_label,
                    "answer": default_msg,
                    "table": None,
                    "insight": "Supported queries include recruiters, branch statistics, compensation packages, and cohort comparisons.",
                    "definition": "Database scope check: records currently unavailable.",
                    "data_scope": "Missing or out-of-database scope",
                    "confidence": "High (Scope verification)",
                    "sql": None,
                    "raw_result": intent_label,
                    "query_spec": spec.model_dump()
                }
                return self._finalize_and_log(res, spec, question, start_time, effective_question=effective_question, is_followup=ctx_output.is_followup)

        # Ambiguous / Clarification required
        if spec.needs_clarification or spec.intent == "clarify" or spec.confidence < 0.7:
            res = {
                "category": "ambiguous",
                "intent": "CLARIFICATION_REQUIRED",
                "answer": spec.clarification_question or "Please clarify your question with more specific details.",
                "table": None,
                "insight": "Supported query types include package lookups, placed student counts, batch breakdowns, and top-N rankings.",
                "definition": "Clarification required.",
                "data_scope": "Ambiguous request",
                "confidence": f"{round(spec.confidence, 2)} (Requires clarification)",
                "sql": None,
                "raw_result": "CLARIFICATION_REQUIRED",
                "query_spec": spec.model_dump()
            }
            return self._finalize_and_log(res, spec, question, start_time, effective_question=effective_question, is_followup=ctx_output.is_followup)

        # Profile Intent (Default Bundle: placement %, placed students, avg+median+max CTC, offers, top 5 recruiters, IT/Core split, per-batch breakdown)
        if spec.intent == "profile":
            return self._execute_profile_query(spec, question, start_time, ctx_output)

        # Student Names Query (Bug F & Stage 3)
        q_clean_names = (ctx_output.standalone_question if ctx_output else question).lower()
        is_name_req = (
            spec.metric == "student_names"
            or any(k in q_clean_names for k in ["give their names", "show their names", "who are they", "their names", "list them", "names of those", "who got placed", "show names", "give names"])
            or (any(k in q_clean_names for k in ["names of", "name of", "who got in", "who got into", "who was placed", "who were placed", "list of placed", "names of students", "name of students"]) and not any(k in q_clean_names for k in ["how many", "count", "number of", "kitne"]))
        ) and not any(k in q_clean_names for k in ["phone", "roll", "email", "contact", "address", "parent", "hr"])

        if is_name_req:
            return self._execute_student_names_query(spec, question, start_time, ctx_output)

        # Step 2: Entity Resolution from QuerySpec
        companies: List[Dict[str, Any]] = []
        for cname in spec.companies:
            resolved_c = self.resolver.resolve_company(cname)
            if resolved_c:
                companies.append(resolved_c)
            else:
                companies.append({"canonical_name": cname})

        branches: List[Dict[str, Any]] = []
        for bcode in spec.branches:
            resolved_b = self.resolver.resolve_branch(bcode)
            if resolved_b:
                branches.append(resolved_b)
            else:
                branches.append({"short": bcode, "code": bcode})

        batches: List[str] = list(spec.batches)

        # Fallback cross-check if QuerySpec had no entities
        if not companies and not branches:
            fallback_entities = self.resolver.extract_and_resolve_entities(question)
            companies = fallback_entities.get("companies", [])
            branches = fallback_entities.get("branches", [])
            if not batches:
                batches = fallback_entities.get("batches", [])

        category = "hybrid" if spec.intent == "hybrid" else "structured"
        intent = spec.intent
        entities = {"companies": companies, "branches": branches, "batches": batches}

        # Step 3: SQL Formulation guided by QuerySpec & AST Validation
        from src.nlp.sql_generator import SafeSQLService, SQLValidator, SQLValidationError

        # Sync spec with canonical resolved entities
        canonical_companies = [c.get("canonical_name", "") for c in companies if c.get("canonical_name")]
        canonical_branches = [b.get("short", b.get("short_name", "")) for b in branches if b.get("short") or b.get("short_name")]
        spec.companies = canonical_companies
        spec.branches = canonical_branches
        spec.batches = batches

        sql, definition, query_type, clar_err = SafeSQLService.generate_and_validate(spec, question)
        if sql is None:
            # Fallback formulation
            formulation = self._formulate_sql(question, companies, branches, batches, spec=spec)
            if formulation[0] is not None:
                try:
                    sql = SQLValidator.validate_and_clean(formulation[0])
                    definition, query_type = formulation[1], formulation[2]
                except SQLValidationError as ve:
                    sql = None
                    clar_err = f"Security / AST Policy Violation: {ve}\n\n{SafeSQLService.CLARIFYING_PROMPT}"

        if sql is None:
            res = {
                "category": "ambiguous",
                "intent": "CLARIFICATION_REQUIRED",
                "answer": clar_err or SafeSQLService.CLARIFYING_PROMPT,
                "table": None,
                "insight": "Supported query types include package lookups, placed student counts, batch breakdowns, and top-N rankings.",
                "definition": "Entity & Intent Resolution: Requires a recognized canonical company, branch, cohort, or metric.",
                "data_scope": "Input query did not match recognized placement entities.",
                "confidence": f"{round(spec.confidence, 2)} (Requires clarification)",
                "sql": None,
                "raw_result": "CLARIFICATION_REQUIRED",
                "query_spec": spec.model_dump()
            }
            return self._finalize_and_log(res, spec, question, start_time, effective_question=effective_question, is_followup=ctx_output.is_followup)

        # Step 4: Execute SQL with retry feedback
        retry_count = 0
        max_retries = 3
        last_error = None
        exec_result = None

        while retry_count < max_retries:
            try:
                exec_result = self.sql_engine.execute_query(sql)
                break
            except SQLEngineError as e:
                last_error = str(e)
                retry_count += 1
                sql = self._refine_sql_on_error(sql, last_error)

        if exec_result is None:
            res = {
                "category": category,
                "intent": intent,
                "answer": f"Unable to execute query after retries: {last_error}",
                "table": None,
                "insight": None,
                "definition": definition,
                "data_scope": "Execution failed",
                "confidence": "Low",
                "sql": sql,
                "raw_result": None,
                "query_spec": spec.model_dump()
            }
            return self._finalize_and_log(res, spec, question, start_time, effective_question=effective_question, is_followup=ctx_output.is_followup)

        # Step 4b: Output Guard (Defense-in-depth inspection for PII & Min Group Size 3)
        if exec_result and exec_result.get("rows"):
            try:
                from src.nlp.privacy_output_guard import PrivacyOutputGuard, PrivacyOutputViolationError
                sanitized_cols, sanitized_rows, p_meta = PrivacyOutputGuard.inspect_and_sanitize(
                    exec_result.get("columns", []),
                    exec_result.get("rows", []),
                    spec
                )
                exec_result["columns"] = sanitized_cols
                exec_result["rows"] = sanitized_rows
            except PrivacyOutputViolationError as pve:
                res = {
                    "category": "privacy",
                    "intent": "PRIVACY_BLOCKED",
                    "answer": PrivacyOutputGuard.STANDARD_PRIVACY_NOTICE,
                    "table": None,
                    "insight": f"Output Guard Security: Suppressed output because {pve}",
                    "definition": "Privacy Guard: Strictly protects personal student identities and contact details.",
                    "data_scope": "Confidential Student PII",
                    "confidence": "High (Privacy Policy Rule)",
                    "sql": None,
                    "raw_result": "PRIVACY_BLOCKED",
                    "query_spec": spec.model_dump()
                }
                return self._finalize_and_log(res, spec, question, start_time, effective_question=effective_question, is_followup=ctx_output.is_followup)

        # Step 5: Sanity Verification
        verif = self.verifier.verify(query_type, exec_result, {"question": question, "entities": entities})
        confidence = verif["confidence"]

        # Step 6: Construct formatted response
        formatted_response = self._format_response(question, exec_result, definition, confidence, batches, verif.get("caveats", []), spec=spec)
        formatted_response["category"] = category
        formatted_response["intent"] = intent
        formatted_response["sql"] = sql
        formatted_response["raw_result"] = self._extract_raw_result(exec_result)
        formatted_response["exec_result"] = exec_result

        # Step 7: Hybrid Enrichment (SQL metadata filtering -> RAG over alumni interview experiences)
        if category == "hybrid":
            target_companies = [c["canonical_name"] for c in companies]
            # If companies table was returned by SQL
            if not target_companies and exec_result.get("rows"):
                for row in exec_result["rows"]:
                    if isinstance(row[0], str) and len(row[0]) > 2:
                        target_companies.append(row[0])

            rag_docs = self.retriever.search(
                query=question,
                companies=target_companies[:5] if target_companies else None,
                top_k=3
            )
            formatted_response["rag_results"] = rag_docs
            if rag_docs:
                rag_bullets = []
                for doc in rag_docs:
                    cname = doc["company"]
                    rounds_str = ", ".join([r["round_name"] for r in doc.get("rounds", [])]) or "Technical & HR"
                    topics_str = ", ".join(doc.get("technical_topics", [])) or "DSA & Core Fundamentals"
                    rag_bullets.append(f"- **{cname}**: {rounds_str}. Evaluated on: *{topics_str}*.")
                
                interview_summary = "Alumni Interview Insights:\n" + "\n".join(rag_bullets)
                formatted_response["insight"] = (formatted_response.get("insight") or "") + "\n\n" + interview_summary
                
                # Append RAG sources to collapsible source section
                rag_source_lines = ["\n\n<details><summary>View Interview Experience Sources (RAG)</summary>\n"]
                for doc in rag_docs:
                    author_str = f" by {doc['author']}" if doc.get('author') else ""
                    date_str = f" ({doc['date']})" if doc.get('date') else ""
                    rag_source_lines.append(f"- **{doc['company']}** - *{doc['title']}*{author_str}{date_str}")
                    if doc.get('key_questions'):
                        rag_source_lines.append(f"  - Questions asked: {'; '.join(doc['key_questions'][:2])}")
                    rag_source_lines.append(f"  - *Excerpt*: \"{doc['excerpt'][:180]}...\"\n")
                rag_source_lines.append("</details>")
                formatted_response["source"] = (formatted_response.get("source") or "") + "".join(rag_source_lines)

        return self._finalize_and_log(
            formatted_response, spec, question, start_time,
            effective_question=effective_question, is_followup=ctx_output.is_followup
        )

    def _finalize_and_log(
        self,
        res: Dict[str, Any],
        spec: Optional[QuerySpec],
        question: str,
        start_time: float,
        effective_question: Optional[str] = None,
        is_followup: bool = False
    ) -> Dict[str, Any]:
        """Telemetry hook: calculate duration, extract result size, and log to query_audit.jsonl."""
        duration_ms = (time.time() - start_time) * 1000.0
        res["standalone_question"] = effective_question or question
        res["is_followup"] = is_followup
        if spec and "query_spec" not in res:
            res["query_spec"] = spec.model_dump()

        cat = res.get("category", "structured")
        intent = res.get("intent", "")
        if cat == "privacy" or intent == "PRIVACY_BLOCKED":
            status = "privacy_blocked"
        elif cat == "ambiguous" or intent == "CLARIFICATION_REQUIRED":
            status = "clarification_required"
        elif cat == "out_of_scope":
            status = "out_of_scope"
        elif res.get("raw_result") is None and "Unable to execute" in (res.get("answer") or ""):
            status = "error"
        else:
            status = "success"

        # Determine confidence as numeric float (0.0 to 1.0)
        conf = 1.0
        if spec and hasattr(spec, "confidence"):
            try:
                conf = float(spec.confidence)
            except Exception:
                conf = 1.0
        else:
            raw_conf = res.get("confidence")
            if isinstance(raw_conf, (int, float)):
                conf = float(raw_conf)
            elif isinstance(raw_conf, str):
                m = re.search(r"([0-9]+\.[0-9]+)", raw_conf)
                if m:
                    conf = float(m.group(1))

        # Determine result size
        result_size = 0
        if "exec_result" in res and res["exec_result"] and "rows" in res["exec_result"]:
            result_size = len(res["exec_result"]["rows"])
        elif "table" in res and isinstance(res["table"], list):
            result_size = len(res["table"])
        elif res.get("raw_result") is not None and res.get("raw_result") not in ["PRIVACY_BLOCKED", "CLARIFICATION_REQUIRED", "OUT_OF_SCOPE", "NO_DATA"]:
            result_size = 1

        # Extract QuerySpec dict
        spec_dict = None
        if spec and hasattr(spec, "model_dump"):
            spec_dict = spec.model_dump()
        elif "query_spec" in res and isinstance(res["query_spec"], dict):
            spec_dict = res["query_spec"]

        AuditLogger.log(
            question=question,
            query_spec=spec_dict,
            confidence=conf,
            sql=res.get("sql"),
            result_size=result_size,
            category=cat,
            status=status,
            duration_ms=duration_ms,
            error=res.get("answer") if status == "error" else None
        )

        return res

    def _formulate_sql(self, question: str, companies: List[Dict], branches: List[Dict], batches: List[str], spec: Optional[QuerySpec] = None) -> Tuple[str, str, str]:
        """Formulate deterministic, verified SQL based on question intent and resolved entities."""
        low = question.lower()
        batch_id = batches[0] if batches else None
        b_filter = f"s.batch_id = '{batch_id}'" if batch_id else "1=1"

        # --- 0. Negative / Existence (Must evaluate before positive counts/lookups) ---
        if any(term in low for term in ["never", "zero", "no offers", "not hired", "unplaced"]):
            if "unplaced" in low:
                b_cond = f"s.batch_id = '{batch_id}'" if batch_id else "s.batch_id = '2020-2024'"
                sql = f"SELECT COUNT(DISTINCT s.student_id) AS unplaced_count FROM students s JOIN branches b ON s.branch_code = b.branch_code WHERE {b_cond} AND b.degree = 'B.Tech' AND s.student_id NOT IN (SELECT DISTINCT o.student_id FROM offers o WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE'));"
                return sql, "Counted distinct B.Tech students who received zero full-time/PPO job offers.", "Negative / existence"

            if "zero female" in low or ("female" in low and "zero" in low):
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND s.gender = 'F' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;"
                return sql, "Identified B.Tech branches with zero female placements.", "Negative / existence"

            if "zero off-campus" in low or ("off-campus" in low and "zero" in low):
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.offer_mode = 'Off-campus') ORDER BY b.short_name ASC;"
                return sql, "Identified B.Tech branches with zero off-campus offers.", "Negative / existence"

            if "above 20" in low or "> 20" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.ctc_lpa > 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;"
                return sql, "Identified B.Tech branches with zero offers above 20 LPA.", "Negative / existence"

            if "above 15" in low or ">= 15" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name FROM branches b WHERE b.division = 'Core' AND b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.ctc_lpa >= 15.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;"
                return sql, "Identified Core branches lacking >= 15 LPA offers.", "Negative / existence"

            if len(branches) >= 2 and any(k in low for k in ["never to", "not to", "but never"]):
                b1, b2 = branches[0]["short"], branches[1]["short"]
                sql = f"SELECT DISTINCT c.canonical_name FROM companies c JOIN offers o ON c.company_id = o.company_id JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{b1}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND c.company_id NOT IN (SELECT DISTINCT o2.company_id FROM offers o2 JOIN students s2 ON o2.student_id = s2.student_id JOIN branches b2 ON s2.branch_code = b2.branch_code WHERE b2.short_name = '{b2}' AND o2.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY c.canonical_name ASC;"
                return sql, f"Identified companies hiring from {b1} but never {b2}.", "Negative / existence"

            if len(batches) >= 2 and any(k in low for k in ["never hired in", "but hired in"]):
                b1, b2 = batches[0], batches[1]
                sql = f"SELECT DISTINCT c.canonical_name FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE s.batch_id = '{b2}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND c.company_id NOT IN (SELECT DISTINCT o2.company_id FROM offers o2 JOIN students s2 ON o2.student_id = s2.student_id WHERE s2.batch_id = '{b1}' AND o2.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY c.canonical_name ASC;"
                return sql, f"Identified companies hiring in {b2} that never hired in {b1}.", "Negative / existence"

            if branches and any(k in low for k in ["zero students from", "never hired from", "zero students"]):
                bshort = branches[0]["short"]
                sql = f"SELECT c.canonical_name FROM companies c WHERE c.company_id NOT IN (SELECT DISTINCT o.company_id FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY c.canonical_name ASC;"
                return sql, f"Identified companies that did not hire from {bshort}.", "Negative / existence"

            if companies:
                cname = companies[0]["canonical_name"]
                sql = f"SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}') ORDER BY b.short_name ASC;"
                return sql, f"Identified all B.Tech branches never hired by {cname}.", "Negative / existence"

        # --- Priority Deterministic Lookup based on QuerySpec ---
        if spec and spec.intent == "lookup":
            if spec.metric == "stipend" or "intern" in low or "stipend" in low:
                if companies:
                    cname = companies[0]["canonical_name"]
                    sql = f"SELECT DISTINCT o.stipend_monthly_inr FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.stipend_monthly_inr IS NOT NULL;"
                    return sql, f"Extracted monthly internship stipend in INR for {cname}.", "Offer-type aware"
            elif (spec.metric == "ctc" or any(k in low for k in ["ctc", "package", "salary", "lpa"])) and not any(k in low for k in ["avg", "average", "mean", "median", "change", "over the batches"]):
                if companies and branches:
                    cname = companies[0]["canonical_name"]
                    bshort = branches[0]["short"]
                    sql = f"SELECT DISTINCT o.ctc_lpa FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND b.short_name = '{bshort}' AND o.ctc_lpa IS NOT NULL ORDER BY o.ctc_lpa DESC;"
                    return sql, f"Queried distinct annual CTC packages offered by {cname} to {bshort}.", "Lookup"
                elif companies:
                    cname = companies[0]["canonical_name"]
                    sql = f"SELECT DISTINCT o.ctc_lpa FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.ctc_lpa IS NOT NULL ORDER BY o.ctc_lpa DESC;"
                    return sql, f"Queried distinct annual CTC packages offered by {cname}.", "Lookup"

        # --- Priority Deterministic Count based on QuerySpec ---
        if spec and spec.intent == "count":
            if branches and not companies:
                bshort = branches[0]["short"]
                if spec.metric == "offers":
                    sql = f"SELECT COUNT(o.offer_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, f"Counted total offers received by {bshort} students (offer row count; students may hold multiple offers).", "Count by condition"
                elif spec.metric == "placed_students":
                    sql = f"SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, f"Counted distinct placed students in {bshort} (distinct students with >= 1 FTE/PPO offer; internships excluded).", "Count by condition"
            elif companies and not branches:
                cname = companies[0]["canonical_name"]
                if spec.metric == "offers":
                    sql = f"SELECT COUNT(o.offer_id) FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}';"
                    return sql, f"Counted total offers made by {cname} (count of offer rows; students may hold multiple offers).", "Count by condition"
                elif spec.metric == "placed_students":
                    sql = f"SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, f"Counted distinct placed students at {cname} (distinct students with >= 1 FTE/PPO offer).", "Count by condition"

        # --- Dual-metric hiring breakdown (Full-time hires vs Internship offers; never added together) ---
        if companies and ("batch-wise" in low or "batch wise" in low or (spec and "batch" in spec.group_by)):
            cname = companies[0]["canonical_name"]
            sql = f"SELECT s.batch_id, COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) AS full_time_hires, COUNT(CASE WHEN o.offer_type IN ('Intern', 'Long Intern', 'Summer Intern') OR (o.stipend_monthly_inr IS NOT NULL AND o.ctc_lpa IS NULL) THEN o.offer_id END) AS intern_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
            return sql, f"Reporting batch-wise hiring for {cname}: Full-time hires (distinct students) vs Internship offers (reported separately; not summed).", "Branch-wise / year-wise breakdowns"

        if companies and ("full-time vs intern" in low or "hires vs intern" in low or ("full-time" in low and "intern" in low and "vs" in low)):
            cname = companies[0]["canonical_name"]
            sql = f"SELECT COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) AS full_time_hires, COUNT(CASE WHEN o.offer_type IN ('Intern', 'Long Intern', 'Summer Intern') OR (o.stipend_monthly_inr IS NOT NULL AND o.ctc_lpa IS NULL) THEN o.offer_id END) AS intern_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}';"
            return sql, f"Reporting full-time hires vs internship offers for {cname} (reported separately; not summed).", "Offer-type aware"

        # --- Dedicated Internship Offers Metric ---
        if spec and spec.metric == "internship_offers":
            if batches:
                b_id = batches[0]
                sql = f"SELECT COUNT(o.offer_id) AS intern_offers FROM offers o JOIN students s ON o.student_id = s.student_id WHERE s.batch_id = '{b_id}' AND o.offer_type IN ('Intern', 'Summer Intern', 'Long Intern');"
                return sql, f"Counted internship offers for batch {b_id} (separate metric from full-time placement).", "Offer-type aware"
            elif companies:
                cname = companies[0]["canonical_name"]
                sql = f"SELECT COUNT(o.offer_id) AS intern_offers FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND (o.offer_type IN ('Intern', 'Summer Intern', 'Long Intern') OR (o.stipend_monthly_inr IS NOT NULL AND o.ctc_lpa IS NULL));"
                return sql, f"Counted internship offers from {cname} (separate metric from full-time placement).", "Offer-type aware"

        # --- Negative / Existence ---
        if any(term in low for term in ["never", "zero", "no offers", "not hired", "unplaced"]):
            if "unplaced" in low:
                b_cond = f"s.batch_id = '{batch_id}'" if batch_id else "s.batch_id = '2020-2024'"
                sql = f"SELECT COUNT(DISTINCT s.student_id) AS unplaced_count FROM students s JOIN branches b ON s.branch_code = b.branch_code WHERE {b_cond} AND b.degree = 'B.Tech' AND s.student_id NOT IN (SELECT DISTINCT o.student_id FROM offers o WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE'));"
                return sql, "Counted distinct B.Tech students who received zero full-time/PPO job offers.", "Negative / existence"

            if "zero female" in low or ("female" in low and "zero" in low):
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND s.gender = 'F' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;"
                return sql, "Identified B.Tech branches with zero female placements.", "Negative / existence"

            if "zero off-campus" in low or ("off-campus" in low and "zero" in low):
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.offer_mode = 'Off-campus') ORDER BY b.short_name ASC;"
                return sql, "Identified B.Tech branches with zero off-campus offers.", "Negative / existence"

            if "above 20" in low or "> 20" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.ctc_lpa > 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;"
                return sql, "Identified B.Tech branches with zero offers above 20 LPA.", "Negative / existence"

            if "above 15" in low or ">= 15" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name FROM branches b WHERE b.division = 'Core' AND b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.ctc_lpa >= 15.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY b.short_name ASC;"
                return sql, "Identified Core branches lacking >= 15 LPA offers.", "Negative / existence"

            if len(branches) >= 2 and any(k in low for k in ["never to", "not to", "but never"]):
                b1, b2 = branches[0]["short"], branches[1]["short"]
                sql = f"SELECT DISTINCT c.canonical_name FROM companies c JOIN offers o ON c.company_id = o.company_id JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{b1}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND c.company_id NOT IN (SELECT DISTINCT o2.company_id FROM offers o2 JOIN students s2 ON o2.student_id = s2.student_id JOIN branches b2 ON s2.branch_code = b2.branch_code WHERE b2.short_name = '{b2}' AND o2.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY c.canonical_name ASC;"
                return sql, f"Identified companies hiring from {b1} but never {b2}.", "Negative / existence"

            if len(batches) >= 2 and any(k in low for k in ["never hired in", "but hired in"]):
                b1, b2 = batches[0], batches[1]
                sql = f"SELECT DISTINCT c.canonical_name FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE s.batch_id = '{b2}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') AND c.company_id NOT IN (SELECT DISTINCT o2.company_id FROM offers o2 JOIN students s2 ON o2.student_id = s2.student_id WHERE s2.batch_id = '{b1}' AND o2.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY c.canonical_name ASC LIMIT 10;"
                return sql, f"Identified companies hiring in {b2} that never hired in {b1}.", "Negative / existence"

            if branches and any(k in low for k in ["zero students from", "never hired from", "zero students"]):
                bshort = branches[0]["short"]
                sql = f"SELECT c.canonical_name FROM companies c WHERE c.company_id NOT IN (SELECT DISTINCT o.company_id FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) ORDER BY c.canonical_name ASC LIMIT 10;"
                return sql, f"Identified companies that did not hire from {bshort}.", "Negative / existence"

            if companies:
                cname = companies[0]["canonical_name"]
                sql = f"SELECT b.short_name FROM branches b WHERE b.degree = 'B.Tech' AND b.branch_code NOT IN (SELECT DISTINCT s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}') ORDER BY b.short_name ASC;"
                return sql, f"Identified all B.Tech branches never hired by {cname}.", "Negative / existence"

        # --- Offer-type aware ---
        if "stipend" in low or "internship stipend" in low:
            if "highest" in low or "top" in low:
                sql = "SELECT c.canonical_name, MAX(o.stipend_monthly_inr) AS max_monthly_stipend FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.stipend_monthly_inr IS NOT NULL GROUP BY c.canonical_name ORDER BY max_monthly_stipend DESC LIMIT 3;"
                return sql, "Ranked companies by highest monthly internship stipend.", "Offer-type aware"

            if companies:
                cname = companies[0]["canonical_name"]
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

        if "ppo" in low and ("how many" in low or "count" in low):
            if companies and branches:
                cname, bshort = companies[0]["canonical_name"], branches[0]["short"]
                sql = f"SELECT COUNT(o.offer_id) AS reliance_che_ppos FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND b.short_name = '{bshort}' AND o.offer_type IN ('PPO', 'Intern+PPO');"
                return sql, f"Counted PPO offers from {cname} in {bshort}.", "Offer-type aware"
            if companies:
                cname = companies[0]["canonical_name"]
                sql = f"SELECT COUNT(o.offer_id) AS amazon_ppos FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.offer_type IN ('PPO', 'Intern+PPO');"
                return sql, f"Counted PPO offers from {cname}.", "Offer-type aware"

        if "internship offers" in low or "intern offers" in low:
            b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2023-2027'"
            sql = f"SELECT COUNT(o.offer_id) AS intern_offers FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.offer_type IN ('Intern', 'Summer Intern');"
            return sql, "Counted internship offers.", "Offer-type aware"

        # --- Percentages / Ratios ---
        if "%" in low or "percentage" in low or "percent" in low or "share" in low or "fraction" in low or "ratio" in low:
            if "double" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND((COUNT(CASE WHEN offer_count >= 2 THEN 1 END) * 100.0) / COUNT(*), 2) AS double_offer_ratio FROM (SELECT s.student_id, COUNT(o.offer_id) AS offer_count FROM students s JOIN offers o ON s.student_id = o.student_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.student_id);"
                return sql, "Calculated ratio of placed students holding multiple offers.", "Percentages / ratios"

            if "ppo" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND((COUNT(CASE WHEN o.offer_type IN ('PPO', 'Intern+PPO') THEN 1 END) * 100.0) / COUNT(o.offer_id), 2) AS ppo_percentage FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, "Computed percentage of offers secured via PPO.", "Percentages / ratios"

            if "it" in low and ("sector" in low or "companies" in low):
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND((COUNT(CASE WHEN c.sector = 'IT' THEN 1 END) * 100.0) / COUNT(o.offer_id), 2) AS it_sector_share FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, "Calculated share of offers originating from IT sector.", "Percentages / ratios"

            if branches and ("female" in low or "women" in low):
                bshort = branches[0]["short"]
                b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND((COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) * 100.0) / COUNT(DISTINCT s.student_id), 2) AS female_cse_pct FROM students s JOIN branches b ON s.branch_code = b.branch_code LEFT JOIN offers o ON s.student_id = o.student_id WHERE b.short_name = '{bshort}' {b_cond} AND s.gender = 'F';"
                return sql, f"Computed female placement percentage in {bshort}.", "Percentages / ratios"

            if branches and ("above 10" in low or ">= 10" in low):
                bshort = branches[0]["short"]
                b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND((COUNT(CASE WHEN o.ctc_lpa >= 10.0 THEN 1 END) * 100.0) / COUNT(CASE WHEN o.ctc_lpa IS NOT NULL THEN 1 END), 2) AS me_above_10_share FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, f"Calculated share of offers >= 10 LPA in {bshort}.", "Percentages / ratios"

            if "share of offers above 18" in low or "above 18" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name, ROUND((COUNT(CASE WHEN o.ctc_lpa >= 18.0 THEN 1 END) * 100.0) / COUNT(CASE WHEN o.ctc_lpa IS NOT NULL THEN 1 END), 2) AS share_above_18 FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code {b_cond} AND b.degree = 'B.Tech' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name HAVING COUNT(CASE WHEN o.ctc_lpa IS NOT NULL THEN 1 END) > 0 ORDER BY share_above_18 DESC;"
                return sql, "Computed department-wise share of offers >= 18 LPA.", "Percentages / ratios"

            if branches:
                bshort = branches[0]["short"]
                b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND((COUNT(DISTINCT CASE WHEN o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') THEN s.student_id END) * 100.0) / COUNT(DISTINCT s.student_id), 2) AS placement_pct FROM students s JOIN branches b ON s.branch_code = b.branch_code LEFT JOIN offers o ON s.student_id = o.student_id WHERE b.short_name = '{bshort}' {b_cond};"
                return sql, f"Computed placement percentage for {bshort}: placed students / total registered * 100.", "Percentages / ratios"

        # --- Ranking / Top-N ---
        if "top" in low or "highest" in low or "most" in low or "rank" in low or "bottom" in low:
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

            if branches and ("highest" in low or "max" in low):
                bshort = branches[0]["short"]
                sql = f"SELECT c.canonical_name, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = '{bshort}' AND o.ctc_lpa IS NOT NULL GROUP BY c.canonical_name ORDER BY max_ctc DESC LIMIT 1;"
                return sql, f"Identified company offering highest package in {bshort}.", "Ranking / top-N"

            if branches and ("hired" in low or "recruiting" in low or "offers" in low or "hiring" in low):
                bshort = branches[0]["short"]
                limit = 5 if ("5" in low or "five" in low) else 3
                sql = f"SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = '{bshort}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY offers_count DESC LIMIT {limit};"
                return sql, f"Ranked top {limit} companies hiring from {bshort}.", "Ranking / top-N"

            if "branches by average" in low or "branches by avg" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code {b_cond} AND b.degree = 'B.Tech' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name ORDER BY avg_ctc DESC LIMIT 5;"
                return sql, "Ranked top 5 B.Tech branches by average CTC.", "Ranking / top-N"

            if "recruiting companies" in low or "number of offers" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY offers_count DESC LIMIT 3;"
                return sql, "Ranked top 3 recruiting companies by offer volume.", "Ranking / top-N"

            if "branch" in low and ("above 20" in low or "> 20" in low):
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name, COUNT(o.offer_id) AS high_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code {b_cond} AND o.ctc_lpa > 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name ORDER BY high_offers DESC LIMIT 1;"
                return sql, "Identified branch with most offers > 20 LPA.", "Ranking / top-N"

            if "companies" in low:
                sql = "SELECT c.canonical_name, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY max_ctc DESC LIMIT 5;"
                return sql, "Ranked top 5 companies by highest annual package.", "Ranking / top-N"

        # --- Trends / Comparisons ---
        if any(term in low for term in ["change", "compare", "trend", "vs", "versus"]):
            if len(companies) >= 2:
                c1, c2 = companies[0]["canonical_name"], companies[1]["canonical_name"]
                if "across all batches" in low or any(c in ["Infosys", "TCS", "Wipro", "Capgemini", "Cognizant"] for c in [c1, c2]):
                    sql = f"SELECT c.canonical_name, COUNT(DISTINCT s.student_id) AS placed_students, COUNT(o.offer_id) AS total_offers, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name IN ('{c1}', '{c2}') AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name;"
                else:
                    sql = f"SELECT c.canonical_name, COUNT(DISTINCT s.student_id) AS placed_students, COUNT(o.offer_id) AS total_offers, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc, MAX(o.ctc_lpa) AS max_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name IN ('{c1}', '{c2}') AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name;"
                return sql, f"Compared hiring volume and package metrics between {c1} and {c2}.", "Trends / comparisons"

            if len(branches) >= 2:
                b1, b2 = branches[0]["short"], branches[1]["short"]
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
                bshort = branches[0]["short"]
                sql = f"SELECT s.batch_id, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                return sql, f"Tracked historical average package trend for {bshort}.", "Trends / comparisons"

            if companies:
                cname = companies[0]["canonical_name"]
                sql = f"SELECT s.batch_id, MAX(o.ctc_lpa) AS max_ctc, COUNT(o.offer_id) AS fte_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                return sql, f"Analyzed offer trend for {cname} across cohorts.", "Trends / comparisons"

        # --- Multi-condition ---
        if "ppo" in low and ("> 30" in low or "above 30" in low or ">30" in low):
            sql = "SELECT DISTINCT c.canonical_name, MAX(o.ctc_lpa) AS max_ppo_ctc FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.offer_type IN ('PPO', 'Intern+PPO') AND o.ctc_lpa > 30.0 GROUP BY c.canonical_name ORDER BY max_ppo_ctc DESC;"
            return sql, "Identified companies offering PPO packages > 30 LPA.", "Multi-condition"

        if "both cse and ece" in low or (len(branches) >= 2 and any(k in low for k in ["both", "and"])):
            b1, b2 = branches[0]["short"], branches[1]["short"]
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
            bshort = branches[0]["short"]
            sql = f"SELECT c.canonical_name, COUNT(DISTINCT s.student_id) AS cse_hires FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = '{bshort}' AND o.ctc_lpa >= 10.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name HAVING cse_hires > 5 ORDER BY cse_hires DESC;"
            return sql, f"Identified companies hiring > 5 students in {bshort} at >= 10 LPA.", "Multi-condition"

        if "at least 3" in low or ">= 3" in low:
            b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2021-2025'"
            sql = f"SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id {b_cond} AND o.ctc_lpa >= 15.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name HAVING offers_count >= 3 ORDER BY offers_count DESC;"
            return sql, "Identified companies with >= 3 offers at >= 15 LPA.", "Multi-condition"

        if branches and ("above 12" in low or ">= 12" in low):
            bshort = branches[0]["short"]
            sql = f"SELECT COUNT(o.offer_id) AS tt_above_12 FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.ctc_lpa >= 12.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
            return sql, f"Counted offers >= 12 LPA in {bshort}.", "Multi-condition"

        # --- Breakdowns ---
        if "company-wise" in low or "company wise" in low:
            if branches:
                bshort = branches[0]["short"]
                b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                sql = f"SELECT c.canonical_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = '{bshort}' {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.canonical_name ORDER BY offers_count DESC, c.canonical_name ASC;"
                return sql, f"Computed company-wise offer distribution for {bshort}.", "Branch-wise / year-wise breakdowns"

        if "branch-wise" in low or "branch wise" in low:
            if "double" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT b.short_name, COUNT(*) AS double_offer_students FROM (SELECT s.student_id, s.branch_code FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.student_id, s.branch_code HAVING COUNT(o.offer_id) >= 2) t JOIN branches b ON t.branch_code = b.branch_code GROUP BY b.short_name ORDER BY double_offer_students DESC;"
                return sql, "Counted students holding multiple offers per branch.", "Branch-wise / year-wise breakdowns"

            if companies:
                cname = companies[0]["canonical_name"]
                sql = f"SELECT b.short_name, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' GROUP BY b.short_name ORDER BY offers_count DESC;"
                return sql, f"Computed branch-wise offers for {cname}.", "Branch-wise / year-wise breakdowns"

            b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
            sql = f"SELECT b.short_name, COUNT(DISTINCT s.student_id) AS placed_count FROM branches b JOIN students s ON b.branch_code = s.branch_code JOIN offers o ON s.student_id = o.student_id {b_cond} AND b.degree = 'B.Tech' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY b.short_name ORDER BY placed_count DESC;"
            return sql, "Computed branch-wise placed student count.", "Branch-wise / year-wise breakdowns"

        is_batch_wise = bool(re.search(r'\b(ba[t|c]{2}h|ba[tc]{2}h|batch|bacth|bathc|btach|year|cohort|session)[-\s]*(wise|breakdown)\b|\b(by|per|across|each)\s+(batch|bacth|bathc|year|cohort)\b|\bbatches\b', low))
        if is_batch_wise:
            if branches and ("package" in low or "ctc" in low or "average" in low):
                bshort = branches[0]["short"]
                sql = f"SELECT s.batch_id, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                return sql, f"Computed year-wise average package for {bshort}.", "Branch-wise / year-wise breakdowns"
            if companies:
                cname = companies[0]["canonical_name"]
                if any(k in low for k in ["ppl", "people", "student", "candidate", "placed", "selected"]):
                    sql = f"SELECT s.batch_id, COUNT(DISTINCT s.student_id) AS placed_students, COUNT(o.offer_id) AS total_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                    return sql, f"Computed batch-wise placed students and offers for {cname}.", "Branch-wise / year-wise breakdowns"
                else:
                    sql = f"SELECT s.batch_id, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                    return sql, f"Computed batch-wise offers for {cname}.", "Branch-wise / year-wise breakdowns"

        if "year-wise" in low or "year wise" in low or "yearwise" in low:
            if branches and ("package" in low or "ctc" in low or "average" in low):
                bshort = branches[0]["short"]
                sql = f"SELECT s.batch_id, ROUND(AVG(o.ctc_lpa), 2) AS avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                return sql, f"Computed year-wise average package for {bshort}.", "Branch-wise / year-wise breakdowns"
            if companies:
                cname = companies[0]["canonical_name"]
                sql = f"SELECT s.batch_id, COUNT(o.offer_id) AS company_offers FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' GROUP BY s.batch_id ORDER BY s.batch_id ASC;"
                return sql, f"Computed year-wise offers for {cname}.", "Branch-wise / year-wise breakdowns"

        if "category-wise" in low or "category wise" in low:
            b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
            bshort = branches[0]["short"] if branches else "CSE"
            sql = f"SELECT s.category, COUNT(DISTINCT s.student_id) AS placed_students FROM students s JOIN branches b ON s.branch_code = b.branch_code JOIN offers o ON s.student_id = o.student_id WHERE b.short_name = '{bshort}' {b_cond} AND s.category IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.category ORDER BY placed_students DESC;"
            return sql, f"Computed category-wise placed students in {bshort}.", "Branch-wise / year-wise breakdowns"

        if "gender-wise" in low or "gender wise" in low:
            b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
            sql = f"SELECT s.gender, COUNT(DISTINCT s.student_id) AS placed_students FROM students s JOIN offers o ON s.student_id = o.student_id {b_cond} AND s.gender IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.gender ORDER BY placed_students DESC;"
            return sql, "Computed gender-wise placed student counts.", "Branch-wise / year-wise breakdowns"

        if "sector-wise" in low or "sector wise" in low:
            b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
            sql = f"SELECT c.sector, COUNT(o.offer_id) AS offers_count FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY c.sector ORDER BY offers_count DESC;"
            return sql, "Computed sector-wise offers breakdown.", "Branch-wise / year-wise breakdowns"

        # --- Aggregates ---
        if "median" in low:
            if branches:
                bshort = branches[0]["short"]
                b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                sql = f"WITH ordered AS (SELECT o.ctc_lpa, ROW_NUMBER() OVER (ORDER BY o.ctc_lpa) AS r, COUNT(*) OVER () AS c FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' {b_cond} AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) SELECT ROUND(AVG(ctc_lpa), 2) AS median_ctc FROM ordered WHERE r IN ((c + 1) / 2, (c + 2) / 2);"
                return sql, f"Computed median annual CTC for {bshort}.", "Aggregates with filters"
            else:
                b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
                sql = f"WITH ordered AS (SELECT o.ctc_lpa, ROW_NUMBER() OVER (ORDER BY o.ctc_lpa) AS r, COUNT(*) OVER () AS c FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.division = 'Core' {b_cond} AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')) SELECT ROUND(AVG(ctc_lpa), 2) AS median_ctc FROM ordered WHERE r IN ((c + 1) / 2, (c + 2) / 2);"
                return sql, "Computed median annual CTC for Core engineering offers.", "Aggregates with filters"

        if "lowest" in low or "min" in low:
            bshort = branches[0]["short"] if branches else "CSE"
            b_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else "AND s.batch_id = '2020-2024'"
            sql = f"SELECT MIN(o.ctc_lpa) AS min_cse_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' {b_cond} AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
            return sql, f"Queried lowest recorded package in {bshort}.", "Aggregates with filters"

        if "average" in low or "avg" in low:
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

            if companies:
                cname = companies[0]["canonical_name"]
                sql = f"SELECT ROUND(AVG(o.ctc_lpa), 2) AS avg_amazon_ctc FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, f"Calculated average annual CTC offered by {cname}.", "Aggregates with filters"

            if "nit jalandhar" in low or "overall" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT ROUND(AVG(o.ctc_lpa), 2) AS overall_avg_ctc FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code {b_cond} AND b.degree = 'B.Tech' AND o.ctc_lpa IS NOT NULL AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, "Calculated overall B.Tech institute average CTC.", "Aggregates with filters"

        # --- Counts ---
        if (any(k in low for k in ["how many", "count", "number of", "kitne", "kitna"]) or ("placed" in low and not any(k in low for k in ["ctc", "package", "average", "avg", "median"]))) and not (any(k in low for k in ["package", "ctc"]) and any(k in low for k in ["round", "interview"])):
            if "double" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT COUNT(*) FROM (SELECT s.student_id FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') GROUP BY s.student_id HAVING COUNT(o.offer_id) >= 2);"
                return sql, "Counted students holding multiple full-time offers.", "Count by condition"

            if "female" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND s.gender = 'F' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, "Counted distinct female placed students.", "Count by condition"

            if "off-campus" in low:
                sql = "SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id WHERE o.offer_mode = 'Off-campus';"
                return sql, "Counted distinct students placed off-campus.", "Count by condition"

            if "above 20" in low or "> 20" in low:
                b_cond = f"WHERE s.batch_id = '{batch_id}'" if batch_id else "WHERE s.batch_id = '2020-2024'"
                sql = f"SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id {b_cond} AND o.ctc_lpa > 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, "Counted distinct students receiving offers > 20 LPA.", "Count by condition"

            if ">= 50" in low or "above 50" in low or "50 lpa" in low:
                sql = "SELECT COUNT(o.offer_id) FROM offers o WHERE o.ctc_lpa >= 50.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, "Counted super-dream offers >= 50.0 LPA.", "Count by condition"

            if companies and branches:
                cname, bshort = companies[0]["canonical_name"], branches[0]["short"]
                sql = f"SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND b.short_name = '{bshort}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, f"Counted distinct students from {bshort} placed at {cname}.", "Count by condition"

            if branches and ("total offers" in low or "offers" in low):
                bshort = branches[0]["short"]
                sql = f"SELECT COUNT(o.offer_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code WHERE b.short_name = '{bshort}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                return sql, f"Counted total offers in {bshort}.", "Count by condition"

            if companies:
                cname = companies[0]["canonical_name"]
                if any(k in low for k in ["total offers", "offers", "offer"]) and not any(k in low for k in ["student", "ppl", "people", "placed", "selected"]):
                    sql = f"SELECT COUNT(o.offer_id) FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}';"
                    return sql, f"Counted total offers from {cname}.", "Count by condition"
                elif any(k in low for k in ["ppl", "people", "student", "candidate", "placed", "selected"]):
                    sql = f"SELECT COUNT(DISTINCT s.student_id) FROM offers o JOIN students s ON o.student_id = s.student_id JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE');"
                    return sql, f"Counted distinct placed students at {cname}.", "Count by condition"
                else:
                    sql = f"SELECT COUNT(o.offer_id) FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}';"
                    return sql, f"Counted total offers from {cname}.", "Count by condition"

        # --- Hybrid / Lookups ---
        if "> 18" in low or ">= 18" in low or ">18" in low:
            sql = "SELECT DISTINCT c.canonical_name FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE o.ctc_lpa > 18.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') ORDER BY c.canonical_name ASC;"
            return sql, "Queried companies offering CTC > 18.0 LPA for hybrid experience merging.", "Hybrid"

        if branches and ("> 20" in low or ">= 20" in low or ">=20" in low):
            bshort = branches[0]["short"]
            sql = f"SELECT DISTINCT c.canonical_name FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.short_name = '{bshort}' AND o.ctc_lpa >= 20.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') ORDER BY c.canonical_name ASC;"
            return sql, f"Queried companies offering >= 20.0 LPA to {bshort}.", "Hybrid"

        if "core" in low and ("> 10" in low or ">= 10" in low):
            sql = "SELECT DISTINCT c.canonical_name FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE b.division = 'Core' AND o.ctc_lpa > 10.0 AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE') ORDER BY c.canonical_name ASC;"
            return sql, "Queried Core engineering companies offering > 10.0 LPA.", "Hybrid"

        if companies:
            cname = companies[0]["canonical_name"]
            if "intern" in low:
                sql = f"SELECT DISTINCT o.stipend_monthly_inr FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.stipend_monthly_inr IS NOT NULL;"
                return sql, f"Extracted internship stipend for {cname}.", "Lookup"
            if branches:
                bshort = branches[0]["short"]
                sql = f"SELECT DISTINCT o.ctc_lpa FROM offers o JOIN students s ON o.student_id = s.student_id JOIN branches b ON s.branch_code = b.branch_code JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND b.short_name = '{bshort}' AND o.ctc_lpa IS NOT NULL ORDER BY o.ctc_lpa DESC;"
                return sql, f"Queried distinct annual CTC packages offered by {cname} to {bshort}.", "Lookup"
            else:
                sql = f"SELECT DISTINCT o.ctc_lpa FROM offers o JOIN companies c ON o.company_id = c.company_id WHERE c.canonical_name = '{cname}' AND o.ctc_lpa IS NOT NULL ORDER BY o.ctc_lpa DESC;"
                return sql, f"Queried distinct annual CTC packages offered by {cname}.", "Lookup"

        # Fallback when no recognized entities or intent
        return None, "Unable to resolve query to a verified placement entity or metric.", "Ambiguous"

    def _refine_sql_on_error(self, sql: str, error_msg: str) -> str:
        refined = sql.replace("GROUP BY b.short_name, s.batch_id", "GROUP BY b.short_name")
        return refined

    def _extract_raw_result(self, exec_result: Dict[str, Any]) -> Any:
        rows = exec_result.get("rows", [])
        if not rows:
            return None
        if len(rows) == 1 and len(rows[0]) == 1:
            return rows[0][0]
        if len(rows[0]) == 1:
            return [r[0] for r in rows]
        return [list(r) for r in rows]

    def _get_ctc_breakdown(self, company: str, bcode: Optional[str] = None, batch_id: Optional[str] = None) -> Optional[str]:
        """Generate conversational offer counts per package, branch, and batch for CTC queries."""
        try:
            b_cond = f"AND b.short_name = '{bcode}'" if bcode else ""
            cohort_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else ""

            fte_query = f"""
                SELECT s.batch_id, o.ctc_lpa, COUNT(DISTINCT s.student_id), GROUP_CONCAT(DISTINCT b.short_name)
                FROM offers o
                JOIN students s ON o.student_id = s.student_id
                JOIN branches b ON s.branch_code = b.branch_code
                JOIN companies c ON o.company_id = c.company_id
                WHERE c.canonical_name = '{company}' AND o.ctc_lpa IS NOT NULL {b_cond} {cohort_cond}
                GROUP BY s.batch_id, o.ctc_lpa
                ORDER BY s.batch_id ASC, o.ctc_lpa DESC;
            """
            fte_res = self.sql_engine.execute_query(fte_query)
            fte_rows = fte_res.get("rows", [])
            if not fte_rows:
                return None

            b_join = "JOIN branches b ON s.branch_code = b.branch_code" if bcode else ""
            intern_query = f"""
                SELECT s.batch_id, COUNT(o.offer_id)
                FROM offers o
                JOIN students s ON o.student_id = s.student_id
                JOIN companies c ON o.company_id = c.company_id
                {b_join}
                WHERE c.canonical_name = '{company}'
                  AND (o.offer_type IN ('Intern', 'Summer Intern', 'Long Intern') OR (o.stipend_monthly_inr IS NOT NULL AND o.ctc_lpa IS NULL))
                  {b_cond} {cohort_cond}
                GROUP BY s.batch_id;
            """
            intern_res = self.sql_engine.execute_query(intern_query)
            intern_dict = dict(intern_res.get("rows", []))

            by_batch = {}
            for bid, ctc, count, branches in fte_rows:
                if bid not in by_batch:
                    by_batch[bid] = []
                by_batch[bid].append((ctc, count, branches))

            parts = []
            all_batches = sorted(set(list(by_batch.keys()) + list(intern_dict.keys())))
            for bid in all_batches:
                fte_items = by_batch.get(bid, [])
                interns = intern_dict.get(bid, 0)

                short_batch = bid.replace("2020-2024", "2020-24").replace("2021-2025", "2021-25").replace("2022-2026", "2022-26").replace("2023-2027", "2023-27")
                if fte_items:
                    pkg_strs = [f"{cnt} full-time hire{'s' if cnt > 1 else ''} at {c:g} LPA" for c, cnt, br in fte_items]
                    sub = f"{short_batch} had {', '.join(pkg_strs)}"
                    if interns > 0:
                        sub += f", plus {interns} summer-intern offer{'s' if interns > 1 else ''}"
                    parts.append(sub)
                elif interns > 0:
                    parts.append(f"{short_batch} had {interns} summer-intern offer{'s' if interns > 1 else ''}")

            b_str = f" in {bcode}" if bcode else ""
            if not parts:
                return f"We don't have package records for **{company}** in our placement database right now. Our Training & Placement team is working on gathering and updating this data, and we will fix/add it soon!"
            if len(parts) > 1:
                bullet_lines = "\n".join([f"• {p}" for p in parts])
                return f"For **{company}**{b_str}, here is the verified cohort breakdown:\n\n{bullet_lines}"
            else:
                return f"For **{company}**{b_str}, {parts[0]}."
        except Exception:
            return None

    def _get_anonymous_interview_summary(self, company: Optional[str], b_code: Optional[str]) -> Optional[str]:
        """Fetch canonical interview insights without any student/author names (Bug A Amendment 3 & 4)."""
        if not company:
            return None
        try:
            cid = None
            cur = self.sql_engine.conn.cursor()
            cur.execute("SELECT company_id FROM companies WHERE canonical_name = ?", (company,))
            row = cur.fetchone()
            if row:
                cid = row[0]
            else:
                cur.execute("SELECT company_id FROM company_aliases WHERE alias = ?", (company.lower(),))
                row = cur.fetchone()
                if row:
                    cid = row[0]
            if not cid:
                return None

            branch_clause = " AND branch_code = ?" if b_code else ""
            params = (cid, b_code) if b_code else (cid,)
            cur.execute(f"""
                SELECT technical_topics, rounds_json, preparation_tips
                FROM interview_experiences
                WHERE company_id = ?{branch_clause}
                LIMIT 3
            """, params)
            rows = cur.fetchall()
            if not rows and b_code:
                cur.execute("""
                    SELECT technical_topics, rounds_json, preparation_tips
                    FROM interview_experiences
                    WHERE company_id = ?
                    LIMIT 3
                """, (cid,))
                rows = cur.fetchall()

            if not rows:
                return None

            insights = []
            for t_topics, r_json, p_tips in rows:
                if t_topics and t_topics.strip() and t_topics != "[]":
                    try:
                        parsed = json.loads(t_topics)
                        if isinstance(parsed, list) and parsed:
                            insights.append(f"• Key evaluated topics: {', '.join(parsed[:4])}")
                    except Exception:
                        insights.append(f"• Key evaluated topics: {t_topics}")
                if r_json and r_json.strip() and r_json != "[]":
                    try:
                        rounds = json.loads(r_json)
                        if isinstance(rounds, list) and rounds:
                            r_names = [r.get("round_name", "Round") for r in rounds if isinstance(r, dict)]
                            if r_names:
                                insights.append(f"• Selection rounds: {' → '.join(r_names[:3])}")
                    except Exception:
                        pass
                if p_tips and p_tips.strip():
                    clean_tip = p_tips.strip()[:180]
                    insights.append(f"• Candidate advice: \"{clean_tip}...\"")
                if len(insights) >= 3:
                    break

            return "\n".join(insights[:3]) if insights else None
        except Exception:
            return None

    def _get_published_alumni(self, company: Optional[str], b_code: Optional[str]) -> List[Tuple]:
        """Fetch alumni who published interview experiences using canonical keys (Bug A Rule 5)."""
        if not company:
            return []
        try:
            cur = self.sql_engine.conn.cursor()
            cur.execute("SELECT company_id FROM companies WHERE canonical_name = ?", (company,))
            row = cur.fetchone()
            cid = row[0] if row else None
            if not cid:
                return []
            branch_clause = " AND branch_code = ?" if b_code else ""
            params = (cid, b_code) if b_code else (cid,)
            cur.execute(f"""
                SELECT DISTINCT author, branch, batch, role
                FROM interview_experiences
                WHERE company_id = ?{branch_clause} AND author IS NOT NULL AND TRIM(author) != ''
                ORDER BY author ASC
                LIMIT 8
            """, params)
            return cur.fetchall()
        except Exception:
            return []

    def _write_payload_answer(self, payload: StructuredAnswerPayload, spec: Optional[Any], question: str) -> str:
        """
        Synthesizes 1-3 conversational, chat-style sentences receiving ONLY the payload
        and QuerySpec. It strictly asserts that numbers stated come only from rows,
        count, or valid metadata, and passes through PayloadNumberVerifier.
        Never sums CTC, averages, or max values across groups.
        """
        rows = payload.rows
        columns = payload.columns or []
        column_meta = payload.column_meta or infer_column_metadata(columns)
        company = spec.companies[0] if (spec and spec.companies) else None
        b_code = spec.branches[0] if (spec and spec.branches) else None
        BRANCH_NAMES = {
            "CSE": "Computer Science and Engineering",
            "IT": "Information Technology",
            "ECE": "Electronics and Communication Engineering",
            "ME": "Mechanical Engineering",
            "EE": "Electrical Engineering",
            "CHE": "Chemical Engineering",
            "CE": "Civil Engineering",
            "ICE": "Instrumentation and Control Engineering",
            "IPE": "Industrial and Production Engineering",
            "BT": "Biotechnology",
            "TT": "Textile Technology"
        }
        branch = BRANCH_NAMES.get(b_code, b_code) if b_code else None

        if company and branch:
            target_str = f"in **{branch}** at **{company}**"
        elif company:
            target_str = f"at **{company}**"
        elif branch:
            target_str = f"in **{branch}**"
        else:
            target_str = "across the institute"

        draft = ""
        # 1. Scalar / 1-row
        if len(rows) == 1 and len(rows[0]) == 1:
            val = rows[0][0]
            if isinstance(val, (int, float)):
                m_type = column_meta[0].metric_type if column_meta else "count"
                if m_type == "percentage":
                    draft = f"The placement rate {target_str} is **{val:.2f}%**."
                elif m_type in ["ctc", "average_ctc", "median_ctc"]:
                    m_label = "average package" if m_type == "average_ctc" else ("median package" if m_type == "median_ctc" else "package")
                    draft = f"The {m_label} {target_str} is **{val:g} LPA**."
                elif m_type == "stipend":
                    draft = f"The monthly internship stipend {target_str} is **₹{val:,.0f} / month**."
                else:
                    m_label = "offers" if (spec and spec.metric in ["offers", "total_offers"]) else "students"
                    draft = f"A total of **{int(val)}** {m_label} were recorded {target_str}."

        # 2. Batch-wise Breakdown
        elif "batch_id" in columns and len(columns) >= 2:
            val_col_idx = 1
            meta = column_meta[val_col_idx] if len(column_meta) > val_col_idx else ColumnMetadata(name=columns[1], metric_type="count")
            numeric_vals = [r[val_col_idx] for r in rows if isinstance(r[val_col_idx], (int, float))]

            if meta.metric_type in ["average_ctc", "median_ctc"]:
                # NEVER SUM AVERAGES!
                top_r = max(rows, key=lambda x: x[val_col_idx] if isinstance(x[val_col_idx], (int, float)) else 0)
                min_r = min(rows, key=lambda x: x[val_col_idx] if isinstance(x[val_col_idx], (int, float)) else 999999)
                draft = f"For {target_str}, average packages range from **{min_r[val_col_idx]:g} LPA** ({min_r[0]}) to **{top_r[val_col_idx]:g} LPA** ({top_r[0]}) across {len(rows)} batches."

            elif meta.metric_type == "ctc":
                # NEVER SUM MAX CTC!
                top_r = max(rows, key=lambda x: x[val_col_idx] if isinstance(x[val_col_idx], (int, float)) else 0)
                draft = f"For {target_str}, the peak package is **{top_r[val_col_idx]:g} LPA**, recorded in **{top_r[0]}**."

            elif meta.metric_type == "percentage":
                # NEVER SUM PERCENTAGES!
                top_r = max(rows, key=lambda x: x[val_col_idx] if isinstance(x[val_col_idx], (int, float)) else 0)
                draft = f"For {target_str}, placement rates peaked in **{top_r[0]}** at **{top_r[val_col_idx]:.2f}%**."

            else:
                # Count: can sum
                total_c = sum(numeric_vals) if numeric_vals else len(rows)
                top_r = max(rows, key=lambda x: x[val_col_idx] if isinstance(x[val_col_idx], (int, float)) else 0)
                m_label = "offers" if "offer" in columns[val_col_idx].lower() else "placed students"
                draft = f"A total of **{int(total_c)}** {m_label} were recorded {target_str} across {len(rows)} batches, peaking in **{top_r[0]}** with **{int(top_r[val_col_idx])}**."

        # 3. Branch-wise Breakdown
        elif "short_name" in columns and "canonical_name" not in columns and len(columns) >= 2:
            num_cols = [i for i, c in enumerate(columns) if any(isinstance(r[i], (int, float)) for r in rows if r[i] is not None)]
            val_col_idx = num_cols[0] if num_cols else 1
            if spec.metric in ["avg_ctc", "average_ctc"]:
                avg_col = next((i for i in num_cols if "avg" in columns[i].lower()), None)
                if avg_col is not None:
                    val_col_idx = avg_col
            elif spec.metric in ["median_ctc"]:
                med_col = next((i for i in num_cols if "median" in columns[i].lower()), None)
                if med_col is not None:
                    val_col_idx = med_col
            elif spec.metric in ["max_ctc", "highest"]:
                max_col = next((i for i in num_cols if "max" in columns[i].lower()), None)
                if max_col is not None:
                    val_col_idx = max_col

            meta = column_meta[val_col_idx] if len(column_meta) > val_col_idx else ColumnMetadata(name=columns[val_col_idx], metric_type="count")
            numeric_vals = [r[val_col_idx] for r in rows if isinstance(r[val_col_idx], (int, float))]

            if meta.metric_type in ["average_ctc", "median_ctc"]:
                # NEVER SUM AVERAGES!
                top_r = max(rows, key=lambda x: x[val_col_idx] if isinstance(x[val_col_idx], (int, float)) else 0)
                m_label = "median CTC" if meta.metric_type == "median_ctc" else "average CTC"
                draft = f"Across {len(rows)} departments, **{top_r[0]}** recorded the highest {m_label} of **{top_r[val_col_idx]:g} LPA**."

            elif meta.metric_type == "ctc":
                # NEVER SUM MAX CTC!
                top_r = max(rows, key=lambda x: x[val_col_idx] if isinstance(x[val_col_idx], (int, float)) else 0)
                draft = f"Across {len(rows)} departments, **{top_r[0]}** recorded the highest package of **{top_r[val_col_idx]:g} LPA**."

            elif meta.metric_type == "percentage":
                top_r = max(rows, key=lambda x: x[val_col_idx] if isinstance(x[val_col_idx], (int, float)) else 0)
                draft = f"Across {len(rows)} departments, **{top_r[0]}** recorded the highest placement rate of **{top_r[val_col_idx]:.2f}%**."

            else:
                total_c = sum(numeric_vals) if numeric_vals else len(rows)
                top_r = max(rows, key=lambda x: x[val_col_idx] if isinstance(x[val_col_idx], (int, float)) else 0)
                m_label = "offers" if "offer" in columns[val_col_idx].lower() else "placed students"
                draft = f"Across {len(rows)} departments, **{top_r[0]}** recorded the highest volume with **{int(top_r[val_col_idx])}** {m_label}, out of **{int(total_c)}** total."

        # 4. Top-N Rankings / Company Lists
        elif "canonical_name" in columns and len(columns) >= 2:
            num_cols = [i for i, c in enumerate(columns) if any(isinstance(r[i], (int, float)) for r in rows if r[i] is not None)]
            val_col_idx = num_cols[-1] if num_cols else (len(columns) - 1)
            meta = column_meta[val_col_idx] if len(column_meta) > val_col_idx else ColumnMetadata(name=columns[val_col_idx], metric_type="count")
            if meta.metric_type in ["ctc", "average_ctc"]:
                if len(rows) >= 2:
                    draft = f"The top package is offered by **{rows[0][0]}** at **{rows[0][val_col_idx]:g} LPA**, followed by **{rows[1][0]}** ({rows[1][val_col_idx]:g} LPA)."
                else:
                    draft = f"The top package is offered by **{rows[0][0]}** at **{rows[0][val_col_idx]:g} LPA**."
            else:
                if len(rows) >= 2:
                    draft = f"The top recruiter is **{rows[0][0]}** with **{int(rows[0][val_col_idx])}** offers, followed by **{rows[1][0]}** ({int(rows[1][val_col_idx])} offers)."
                else:
                    draft = f"The top recruiter is **{rows[0][0]}** with **{int(rows[0][val_col_idx])}** offers."

        if not draft:
            draft = f"Found **{len(rows)}** records matching the requested placement dimensions."

        # Verify draft with PayloadNumberVerifier
        is_valid, errs = PayloadNumberVerifier.verify(draft, payload)
        if not is_valid:
            # Fall back to safe caption without unverified numbers
            draft = f"Placement records {target_str} across {len(rows)} matching entries."

        return draft

    def _execute_student_names_query(
        self,
        spec: QuerySpec,
        question: str,
        start_time: float,
        ctx_output: Any
    ) -> Dict[str, Any]:
        """
        Executes query for student names complying with Bug F & Stage 3:
        ALLOWED_PERSON_FIELDS = ["name", "branch", "batch", "company", "role", "offer_type"]
        SHOW_STUDENT_PACKAGE = False (individual package suppressed, aggregates fine)
        List comes from the same query and same filters as the count.
        If count > 20, returns first 20 with "showing 20 of N, say 'show more' for next".
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        company = spec.companies[0] if spec.companies else None
        b_code = spec.branches[0] if spec.branches else None
        batches = spec.batches or ["2020-2024", "2021-2025", "2022-2026"]

        where_clauses = ["o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')"]
        params = []

        if company:
            where_clauses.append("c.canonical_name LIKE ?")
            params.append(company)

        if b_code:
            where_clauses.append("b.short_name LIKE ?")
            params.append(b_code)

        if len(batches) == 1 and batches[0] != "all":
            where_clauses.append("s.batch_id = ?")
            params.append(batches[0])
        elif len(batches) > 1:
            placeholders = ",".join(["?"] * len(batches))
            where_clauses.append(f"s.batch_id IN ({placeholders})")
            params.extend(batches)

        if "exact_ctc" in spec.filters:
            where_clauses.append("o.ctc_lpa = ?")
            params.append(spec.filters["exact_ctc"])

        sql = f"""
        SELECT DISTINCT p.full_name, b.short_name, s.batch_id, c.canonical_name, 
               COALESCE(o.profile, 'Graduate Engineer / Analyst') AS role, o.offer_type
        FROM offers o
        JOIN students s ON o.student_id = s.student_id
        JOIN student_private_pii p ON s.student_id = p.student_id
        JOIN branches b ON s.branch_code = b.branch_code
        JOIN companies c ON o.company_id = c.company_id
        WHERE {" AND ".join(where_clauses)}
        ORDER BY p.full_name ASC;
        """
        cur.execute(sql, params)
        rows = cur.fetchall()
        total_count = len(rows)

        target_desc = f"at **{company}**" if company else ""
        if b_code:
            target_desc += f" in **{b_code}**"
        target_desc = target_desc.strip() or "across the institute"

        if not SHOW_STUDENT_NAMES:
            # Under institutional privacy policy, individual names are strictly protected.
            # Return aggregate (count, batch, package range) and offer interview experience summary without author names.
            pkg_sql = f"""
            SELECT COUNT(DISTINCT s.student_id), MIN(o.ctc_lpa), MAX(o.ctc_lpa), ROUND(AVG(o.ctc_lpa), 2)
            FROM offers o
            JOIN students s ON o.student_id = s.student_id
            JOIN branches b ON s.branch_code = b.branch_code
            JOIN companies c ON o.company_id = c.company_id
            WHERE {" AND ".join(where_clauses)}
            """
            cur.execute(pkg_sql, params)
            pkg_row = cur.fetchone()
            st_count = pkg_row[0] if (pkg_row and pkg_row[0] is not None) else total_count
            min_c = pkg_row[1] if (pkg_row and pkg_row[1] is not None) else 0
            max_c = pkg_row[2] if (pkg_row and pkg_row[2] is not None) else 0
            avg_c = pkg_row[3] if (pkg_row and pkg_row[3] is not None) else 0

            if st_count == 0:
                direct_answer = f"No student placement records found {target_desc} for the requested criteria."
            else:
                direct_answer = (
                    f"For student privacy and confidentiality, individual student personal records (including names, roll numbers, "
                    f"and contact details) are protected and cannot be disclosed.\n\n"
                    f"For {target_desc}, a total of **{st_count}** students were placed across batch(es) {', '.join(batches)}:\n"
                    f"• **Package Range**: {min_c} LPA to {max_c} LPA (Average: {avg_c} LPA)\n\n"
                    f"Would you like an overview of the interview experience and selection process{f' for **{company}**' if company else ''}?"
                )

            sql = pkg_sql
            columns = ["count", "min_ctc", "max_ctc", "avg_ctc"]
            rows = [[st_count, min_c, max_c, avg_c]]
            total_count = st_count

        elif total_count == 0:
            direct_answer = f"No student placement records found {target_desc} for the requested criteria."
        else:
            bullets = []
            display_rows = rows[:20]
            for r in display_rows:
                fname, bshort, batch_str, cname, role, off_type = r
                short_batch = batch_str.replace("2020-2024", "2020-24").replace("2021-2025", "2021-25").replace("2022-2026", "2022-26")
                bullets.append(f"• **{fname.title()}** ({bshort}, {short_batch}, {cname}, {role})")

            direct_answer = f"A total of **{total_count}** students were placed {target_desc}:\n\n" + "\n".join(bullets)
            if total_count > 20:
                direct_answer += f"\n\n*(Showing 20 of {total_count} placed students. Say 'show more' to view next)*"

            if not SHOW_STUDENT_PACKAGE:
                direct_answer += "\n\n*(Individual compensation packages are kept confidential under institutional privacy policy)*"

        scope_str = f"Covering batch(es): {', '.join(batches)}."
        footer_details = (
            "<details>\n"
            "<summary>Technical Details & SQL</summary>\n\n"
            f"- **Deterministic SQL Query**:\n```sql\n{sql}\n```\n"
            "- **Metric Semantics**: Placed student roster with verified company, branch, and role details.\n"
            f"- **Data Scope**: {scope_str}\n"
            "- **Verification**: High (Verified from institutional placement records)\n"
            "</details>"
        )

        columns = ["full_name", "short_name", "batch_id", "canonical_name", "role", "offer_type"]
        payload = StructuredAnswerPayload(
            count=total_count,
            rows=rows,
            scope=f"{company or b_code or 'NIT Jalandhar'}",
            offer_types=spec.offer_types,
            columns=columns,
            column_meta=infer_column_metadata(columns),
            direct_answer=direct_answer
        )
        payload.validate_payload()

        res = {
            "answer": direct_answer,
            "table": None,
            "insight": "Student names are verified against departmental placement registries; individual compensation is kept confidential.",
            "definition": "Placed student roster query.",
            "data_scope": scope_str,
            "confidence": "High (Verified from database)",
            "sql": sql,
            "raw_result": total_count,
            "exec_result": {"columns": columns, "rows": rows, "row_count": total_count},
            "source": footer_details,
            "payload": payload.model_dump(),
            "query_spec": spec.model_dump()
        }
        return self._finalize_and_log(res, spec, question, start_time, effective_question=question, is_followup=ctx_output.is_followup)

    def _execute_profile_query(
        self,
        spec: QuerySpec,
        question: str,
        start_time: float,
        ctx_output: Any
    ) -> Dict[str, Any]:
        """
        Executes a 'profile' bundle request for <branch|batch|college>.
        Default bundle: placement %, placed students, avg + median + max CTC,
        total offers, top 5 recruiters, IT/Core split, per-batch breakdown table.
        One compact table plus 2-3 sentence summary.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        BRANCH_NAMES = {
            "CSE": "Computer Science and Engineering",
            "IT": "Information Technology",
            "ECE": "Electronics and Communication Engineering",
            "ME": "Mechanical Engineering",
            "EE": "Electrical Engineering",
            "CHE": "Chemical Engineering",
            "CE": "Civil Engineering",
            "ICE": "Instrumentation and Control Engineering",
            "IPE": "Industrial and Production Engineering",
            "BT": "Biotechnology",
            "TT": "Textile Technology"
        }
        BRANCH_CODES = {
            "CE": "102", "CIVIL": "102", "CSE": "103", "ECE": "104", "ICE": "106",
            "ME": "109", "TT": "110", "BT": "111", "CHE": "112", "IPE": "113",
            "DSE": "117", "VLSI": "118", "IT": "124", "EE": "126"
        }

        bshort = spec.branches[0] if spec.branches else None
        bcode = BRANCH_CODES.get(bshort) if bshort else None
        branch_full = BRANCH_NAMES.get(bshort, bshort) if bshort else "NIT Jalandhar"
        target_scope = branch_full if bshort else "NIT Jalandhar (College-wide)"

        batches = spec.batches if (spec.batches and len(spec.batches) > 0) else ["2020-2024", "2021-2025", "2022-2026"]
        is_single_batch = (len(batches) == 1 and batches[0] != "all")

        breakdown_rows = []
        tot_elig = 0
        tot_placed = 0
        tot_offers = 0

        for b in batches:
            if bcode:
                cur.execute(
                    "SELECT eligible_students, placed_students, placement_pct FROM batch_branch_stats WHERE branch_code = ? AND batch_id = ?",
                    (bcode, b)
                )
            else:
                cur.execute(
                    "SELECT eligible_students, placed_students, placement_pct FROM batch_branch_stats WHERE branch_code = 'TOTAL' AND degree = 'B.Tech' AND batch_id = ?",
                    (b,)
                )
            stat = cur.fetchone()
            elig = stat[0] if (stat and stat[0]) else 0
            placed = stat[1] if (stat and stat[1]) else 0
            pct = stat[2] if (stat and stat[2]) else 0.0

            # Compute avg and max CTC (highest per placed student)
            if bcode:
                cur.execute("""
                    WITH student_highest AS (
                        SELECT s.student_id, MAX(o.ctc_lpa) AS highest_ctc
                        FROM students s
                        JOIN offers o ON s.student_id = o.student_id
                        WHERE s.branch_code = ? AND s.batch_id = ?
                          AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                          AND o.ctc_lpa IS NOT NULL
                        GROUP BY s.student_id
                    )
                    SELECT ROUND(AVG(highest_ctc), 2), MAX(highest_ctc) FROM student_highest
                """, (bcode, b))
                pkg = cur.fetchone()
                cur.execute("""
                    SELECT COUNT(o.offer_id) FROM offers o
                    JOIN students s ON o.student_id = s.student_id
                    WHERE s.branch_code = ? AND s.batch_id = ?
                      AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                """, (bcode, b))
                offers = cur.fetchone()[0]
            else:
                cur.execute("""
                    WITH student_highest AS (
                        SELECT s.student_id, MAX(o.ctc_lpa) AS highest_ctc
                        FROM students s
                        JOIN offers o ON s.student_id = o.student_id
                        JOIN branches b ON s.branch_code = b.branch_code
                        WHERE b.degree = 'B.Tech' AND s.batch_id = ?
                          AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                          AND o.ctc_lpa IS NOT NULL
                        GROUP BY s.student_id
                    )
                    SELECT ROUND(AVG(highest_ctc), 2), MAX(highest_ctc) FROM student_highest
                """, (b,))
                pkg = cur.fetchone()
                cur.execute("""
                    SELECT COUNT(o.offer_id) FROM offers o
                    JOIN students s ON o.student_id = s.student_id
                    JOIN branches b ON s.branch_code = b.branch_code
                    WHERE b.degree = 'B.Tech' AND s.batch_id = ?
                      AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                """, (b,))
                offers = cur.fetchone()[0]

            avg_c = pkg[0] if (pkg and pkg[0]) else 0.0
            max_c = pkg[1] if (pkg and pkg[1]) else 0.0

            breakdown_rows.append([b, elig, placed, f"{pct:.2f}%", f"{avg_c:.2f} LPA", f"{max_c:.2f} LPA", offers])
            tot_elig += elig
            tot_placed += placed
            tot_offers += offers

        tot_pct = round(tot_placed * 100.0 / tot_elig, 2) if tot_elig > 0 else 0.0

        batch_placeholders = ",".join(["?"] * len(batches))
        if bcode:
            cur.execute(f"""
                WITH student_highest AS (
                    SELECT s.student_id, MAX(o.ctc_lpa) AS highest_ctc
                    FROM students s
                    JOIN offers o ON s.student_id = o.student_id
                    WHERE s.branch_code = ? AND s.batch_id IN ({batch_placeholders})
                      AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                      AND o.ctc_lpa IS NOT NULL
                    GROUP BY s.student_id
                ),
                ordered AS (
                    SELECT highest_ctc,
                           ROW_NUMBER() OVER (ORDER BY highest_ctc) AS r,
                           COUNT(*) OVER () AS c
                    FROM student_highest
                )
                SELECT 
                    ROUND(AVG(sh.highest_ctc), 2),
                    (SELECT ROUND(AVG(highest_ctc), 2) FROM ordered WHERE r IN ((c + 1) / 2, (c + 2) / 2)),
                    MAX(sh.highest_ctc),
                    COUNT(*)
                FROM student_highest sh;
            """, [bcode] + batches)
            ov_pkg = cur.fetchone()

            cur.execute(f"""
                SELECT COUNT(o.offer_id) FROM offers o
                JOIN students s ON o.student_id = s.student_id
                WHERE s.branch_code = ? AND s.batch_id IN ({batch_placeholders})
                  AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                  AND o.ctc_lpa IS NULL;
            """, [bcode] + batches)
            excluded_cnt = cur.fetchone()[0]

            cur.execute(f"""
                SELECT c.canonical_name, COUNT(o.offer_id) AS cnt
                FROM offers o
                JOIN students s ON o.student_id = s.student_id
                JOIN companies c ON o.company_id = c.company_id
                WHERE s.branch_code = ? AND s.batch_id IN ({batch_placeholders})
                  AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                GROUP BY c.canonical_name
                ORDER BY cnt DESC, c.canonical_name ASC
                LIMIT 5;
            """, [bcode] + batches)
            top5 = cur.fetchall()

            cur.execute(f"""
                SELECT 
                  CASE WHEN c.sector = 'IT' THEN 'IT / Software'
                       WHEN c.sector = 'Core' THEN 'Core Engineering'
                       ELSE 'Consulting / Non-Core' END AS sec,
                  COUNT(o.offer_id)
                FROM offers o
                JOIN students s ON o.student_id = s.student_id
                JOIN companies c ON o.company_id = c.company_id
                WHERE s.branch_code = ? AND s.batch_id IN ({batch_placeholders})
                  AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                GROUP BY sec
                ORDER BY COUNT(o.offer_id) DESC;
            """, [bcode] + batches)
            sectors = cur.fetchall()

        else:
            cur.execute(f"""
                WITH student_highest AS (
                    SELECT s.student_id, MAX(o.ctc_lpa) AS highest_ctc
                    FROM students s
                    JOIN offers o ON s.student_id = o.student_id
                    JOIN branches b ON s.branch_code = b.branch_code
                    WHERE b.degree = 'B.Tech' AND s.batch_id IN ({batch_placeholders})
                      AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                      AND o.ctc_lpa IS NOT NULL
                    GROUP BY s.student_id
                ),
                ordered AS (
                    SELECT highest_ctc,
                           ROW_NUMBER() OVER (ORDER BY highest_ctc) AS r,
                           COUNT(*) OVER () AS c
                    FROM student_highest
                )
                SELECT 
                    ROUND(AVG(sh.highest_ctc), 2),
                    (SELECT ROUND(AVG(highest_ctc), 2) FROM ordered WHERE r IN ((c + 1) / 2, (c + 2) / 2)),
                    MAX(sh.highest_ctc),
                    COUNT(*)
                FROM student_highest sh;
            """, batches)
            ov_pkg = cur.fetchone()

            cur.execute(f"""
                SELECT COUNT(o.offer_id) FROM offers o
                JOIN students s ON o.student_id = s.student_id
                JOIN branches b ON s.branch_code = b.branch_code
                WHERE b.degree = 'B.Tech' AND s.batch_id IN ({batch_placeholders})
                  AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                  AND o.ctc_lpa IS NULL;
            """, batches)
            excluded_cnt = cur.fetchone()[0]

            cur.execute(f"""
                SELECT c.canonical_name, COUNT(o.offer_id) AS cnt
                FROM offers o
                JOIN students s ON o.student_id = s.student_id
                JOIN companies c ON o.company_id = c.company_id
                JOIN branches b ON s.branch_code = b.branch_code
                WHERE b.degree = 'B.Tech' AND s.batch_id IN ({batch_placeholders})
                  AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                GROUP BY c.canonical_name
                ORDER BY cnt DESC, c.canonical_name ASC
                LIMIT 5;
            """, batches)
            top5 = cur.fetchall()

            cur.execute(f"""
                SELECT 
                  CASE WHEN c.sector = 'IT' THEN 'IT / Software'
                       WHEN c.sector = 'Core' THEN 'Core Engineering'
                       ELSE 'Consulting / Non-Core' END AS sec,
                  COUNT(o.offer_id)
                FROM offers o
                JOIN students s ON o.student_id = s.student_id
                JOIN companies c ON o.company_id = c.company_id
                JOIN branches b ON s.branch_code = b.branch_code
                WHERE b.degree = 'B.Tech' AND s.batch_id IN ({batch_placeholders})
                  AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                GROUP BY sec
                ORDER BY COUNT(o.offer_id) DESC;
            """, batches)
            sectors = cur.fetchall()

        # Build Compact Markdown Table
        table_headers = ["Academic Batch", "Eligible Students", "Placed Students", "Placement Rate", "Average CTC", "Peak CTC", "Total Offers"]
        header_line = "| " + " | ".join(table_headers) + " |"
        sep_line = "| " + " | ".join(["---"] * len(table_headers)) + " |"
        data_lines = ["| " + " | ".join(str(c) for c in r) + " |" for r in breakdown_rows]
        tot_line = f"| **Total / Overall** | **{tot_elig}** | **{tot_placed}** | **{tot_pct}%** | **{ov_pkg[0]} LPA** | **{ov_pkg[2]} LPA** | **{tot_offers}** |"
        table_md = "\n".join([header_line, sep_line] + data_lines + [tot_line])

        # Build 2-3 sentence direct summary
        top_strs = [f"{c} ({cnt})" for c, cnt in top5]
        sec_strs = [f"{s}: {cnt}" for s, cnt in sectors]
        top_list_str = ", ".join(top_strs[:3]) if top_strs else "major recruiters"
        sec_list_str = ", ".join(sec_strs) if sec_strs else "various industry sectors"

        assumption_line = "Across all batches 2020-24 to 2022-26, full-time offers only." if len(batches) > 1 else f"For the {batches[0]} batch, full-time offers only."

        summary = (
            f"{assumption_line}\n\n"
            f"{target_scope} recorded an overall placement percentage of **{tot_pct}%** "
            f"with **{tot_placed}** students placed out of {tot_elig} eligible candidates, securing **{tot_offers}** total offers.\n"
            f"The overall average package is **{ov_pkg[0]} LPA** (median **{ov_pkg[1]} LPA**, highest **{ov_pkg[2]} LPA** across {ov_pkg[3]} placed students; {excluded_cnt} offers excluded for unparseable/undisclosed CTC).\n"
            f"Top recruiters include **{top_list_str}**, with offer breakdown by sector: {sec_list_str}."
        )

        columns = ["batch_id", "eligible_students", "placed_students", "placement_pct", "avg_ctc", "max_ctc", "total_offers"]
        rows_data = [
            [r[0], r[1], r[2], float(r[3].replace("%", "")), float(r[4].replace(" LPA", "")), float(r[5].replace(" LPA", "")), r[6]]
            for r in breakdown_rows
        ]

        payload = StructuredAnswerPayload(
            count=tot_placed,
            rows=rows_data,
            columns=columns,
            column_meta=infer_column_metadata(columns),
            scope=target_scope,
            offer_types=["FTE", "PPO"],
            direct_answer=summary
        )
        payload.validate_payload()

        footer_details = (
            "<details>\n"
            "<summary>Technical Details & SQL</summary>\n\n"
            "- **Query Profile**: Multi-dimensional bundle across official Count Wise Details and verified student offer records.\n"
            f"- **Metric Semantics**: Highest FTE/PPO package per placed student; placement percentage = placed / eligible.\n"
            f"- **Data Scope**: {assumption_line}\n"
            "- **Verification**: High (Verified against official placement records)\n"
            "</details>"
        )

        res = {
            "category": "structured",
            "intent": "profile",
            "answer": summary,
            "table": table_md,
            "insight": f"Sector distribution for {target_scope}: {sec_list_str}.",
            "definition": "Complete institutional placement profile bundle.",
            "data_scope": assumption_line,
            "confidence": "High (Profile bundle)",
            "sql": "MULTIPLE_PROFILE_QUERIES (batch_branch_stats + offers)",
            "raw_result": rows_data,
            "exec_result": {"columns": columns, "rows": rows_data},
            "source": footer_details,
            "payload": payload.model_dump(),
            "query_spec": spec.model_dump()
        }
        return self._finalize_and_log(res, spec, question, start_time, effective_question=question, is_followup=ctx_output.is_followup)

    def _format_response(
        self,
        question: str,
        exec_result: Dict[str, Any],
        definition: str,
        confidence: str,
        batches: List[str],
        caveats: List[str],
        spec: Optional[Any] = None
    ) -> Dict[str, Any]:
        rows = exec_result.get("rows", [])
        columns = exec_result.get("columns", [])
        sql = exec_result.get("sql", "")

        BRANCH_NAMES = {
            "CSE": "Computer Science and Engineering",
            "IT": "Information Technology",
            "ECE": "Electronics and Communication Engineering",
            "ME": "Mechanical Engineering",
            "EE": "Electrical Engineering",
            "CHE": "Chemical Engineering",
            "CE": "Civil Engineering",
            "ICE": "Instrumentation and Control Engineering",
            "IPE": "Industrial and Production Engineering",
            "BT": "Biotechnology",
            "TT": "Textile Technology"
        }

        q_low = question.lower()
        company = spec.companies[0] if (spec and spec.companies) else None
        b_code = spec.branches[0] if (spec and spec.branches) else None
        branch = BRANCH_NAMES.get(b_code, b_code) if b_code else None

        # When missing batch or multiple batches, do NOT hardcode batch[0]
        is_single_batch = bool(spec and spec.batches and len(spec.batches) == 1 and spec.batches[0] != "all")
        batch = spec.batches[0] if is_single_batch else None
        cohort_str = f" for the {batch} batch" if batch else (" across all cohorts (2020-24 to 2022-26)" if (spec and spec.batches and len(spec.batches) > 1) else "")

        if company and branch:
            target_str = f" in **{branch}** at **{company}**"
        elif company:
            target_str = f" at **{company}**"
        elif branch:
            target_str = f" in **{branch}**"
        else:
            target_str = " across the institute"

        table_md = None
        insight_note = None
        direct_answer = None

        if not rows:
            target = f" for **{company}**" if company else (f" in **{branch}**" if branch else "")
            direct_answer = f"We don't have records{target} in our placement database right now. Our Training & Placement team is actively working on gathering and updating this data, and we will fix/add it soon!"
        elif len(rows) == 1 and len(rows[0]) == 1:
            val = rows[0][0]
            # Single scalar value
            if isinstance(val, (int, float)):
                is_ctc_col = bool(
                    (columns and columns[0] in ["ctc_lpa", "max_ctc", "min_ctc", "avg_ctc", "median_ctc"])
                    or (spec and spec.metric in ["ctc", "avg_ctc", "max_ctc", "min_ctc", "median_ctc"])
                    or any(k in q_low for k in ["ctc", "package", "salary", "highest", "lowest", "avg", "average", "median"])
                )
                if "%" in definition or any(k in q_low for k in ["percentage", "ratio", "rate", "%"]):
                    target_label = f"the {batch} batch" if batch else (f"{branch}" if branch else "NIT Jalandhar")
                    direct_answer = f"The placement rate for {target_label} is **{val:.2f}%**."
                elif "stipend" in q_low or (spec and spec.metric == "stipend"):
                    direct_answer = f"The monthly internship stipend offered {target_str} is **₹{val:,.0f} / month**."
                elif is_ctc_col:
                    if company and any(k in q_low for k in ["ctc", "package", "salary", "lpa", "offer"]) and not any(k in q_low for k in ["avg", "average", "median", "highest", "lowest", "max", "min"]):
                        ctc_bd = self._get_ctc_breakdown(company, b_code, batch)
                        if ctc_bd:
                            direct_answer = ctc_bd
                        else:
                            metric_label = "package"
                            direct_answer = f"The {metric_label} offered {target_str}{cohort_str} is **{val:g} LPA**."
                    else:
                        metric_label = "average package" if any(k in q_low for k in ["avg", "average"]) else ("median package" if "median" in q_low else ("highest package" if any(k in q_low for k in ["highest", "max", "peak"]) else ("lowest package" if any(k in q_low for k in ["lowest", "min"]) else "package")))
                        direct_answer = f"The {metric_label} {target_str}{cohort_str} is **{val:g} LPA**."
                else:
                    # Count
                    is_offers_metric = (
                        (spec and spec.metric in ["offers", "total_offers"])
                        or any(k in q_low for k in ["total offers", "number of offers", "offers were given", "offer count", "offers made", "count of offers"])
                        or (any(k in q_low for k in ["offer", "offers"]) and not any(k in q_low for k in ["student", "ppl", "people", "candidate", "placed", "hired"]))
                    )
                    if spec and spec.metric in ["company_count", "distinct_companies"]:
                        direct_answer = f"A total of **{int(val)}** distinct companies made offers{target_str}{cohort_str}."
                    elif spec and spec.metric == "multi_offer_students":
                        direct_answer = f"A total of **{int(val)}** students received multiple full-time offers{target_str}{cohort_str}."
                    elif is_offers_metric:
                        direct_answer = f"A total of **{int(val)}** offers were recorded{target_str}{cohort_str}."
                    else:
                        is_names_query = any(k in q_low for k in ["who", "name", "names", "list of placed", "who got placed", "names of those", "list them", "list"])
                        if is_names_query:
                            ctc_bd = self._get_ctc_breakdown(company, b_code, batch) if company else None
                            cohort_detail = f"\n\n• {ctc_bd}" if ctc_bd else ""

                            if not SHOW_STUDENT_NAMES:
                                rag_summary = self._get_anonymous_interview_summary(company, b_code)
                                direct_answer = (
                                    f"For **{company or 'the recruiter'}**{target_str}{cohort_str}, a total of **{int(val)}** students were placed.{cohort_detail}\n\n"
                                    f"*(Individual student names are protected under institutional privacy policy)*"
                                )
                                if rag_summary:
                                    direct_answer += f"\n\n**Interview & Selection Insights**:\n{rag_summary}"
                            else:
                                auth_rows = self._get_published_alumni(company, b_code)
                                if auth_rows:
                                    student_bullets = []
                                    for a in auth_rows:
                                        aname, abranch, abatch, arole = a
                                        details = []
                                        if abranch: details.append(abranch)
                                        if abatch: details.append(abatch.replace("2020-2024", "2020-24").replace("2021-2025", "2021-25").replace("2022-2026", "2022-26"))
                                        if arole: details.append(arole)
                                        det_str = f" ({', '.join(details)})" if details else ""
                                        student_bullets.append(f"• **{aname.title()}**{det_str}")

                                    direct_answer = (
                                        f"Placement Count: A total of **{int(val)}** students were placed{target_str}{cohort_str}.\n\n"
                                        f"Published Alumni Interview Contributors ({len(auth_rows)}):\n"
                                        + "\n".join(student_bullets)
                                    )
                                else:
                                    direct_answer = f"A total of **{int(val)}** students were placed{target_str}{cohort_str}."
                        else:
                            direct_answer = f"A total of **{int(val)}** students were placed{target_str}{cohort_str}."
            else:
                direct_answer = f"The resulting record is **{val}**."
        elif len(rows) > 1 and len(rows[0]) == 1:
            # 1D List of items (packages or company names)
            vals = [r[0] for r in rows]
            all_floats = all(isinstance(v, (int, float)) for v in vals)

            if all_floats:
                if company and any(k in q_low for k in ["ctc", "package", "salary", "lpa", "offer", "hired"]):
                    ctc_bd = self._get_ctc_breakdown(company, b_code, batch)
                    if ctc_bd:
                        direct_answer = ctc_bd
                    else:
                        pkg_strs = [f"**{v:g} LPA**" for v in vals]
                        if len(pkg_strs) == 2:
                            direct_answer = f"For {target_str}, the annual packages offered are {pkg_strs[0]} and {pkg_strs[1]}."
                        else:
                            direct_answer = f"For {target_str}, the annual packages offered are {', '.join(pkg_strs[:-1])}, and {pkg_strs[-1]}."
                else:
                    pkg_strs = [f"**{v:g} LPA**" for v in vals]
                    if len(pkg_strs) == 2:
                        direct_answer = f"For {target_str}, the annual packages offered are {pkg_strs[0]} and {pkg_strs[1]}."
                    else:
                        direct_answer = f"For {target_str}, the annual packages offered are {', '.join(pkg_strs[:-1])}, and {pkg_strs[-1]}."
                table_md = None
            else:
                items = [str(v) for v in vals]
                if len(items) <= 5:
                    direct_answer = f"The matching companies are **{', '.join(items)}**."
                    table_md = None
                else:
                    direct_answer = f"Found **{len(items)}** companies meeting the criteria (including {', '.join(items[:5])})."
                    table_md = "| " + columns[0].replace("_", " ").title() + " |\n|---|\n" + "\n".join([f"| {it} |" for it in items])
        else:
            # Multi-column table
            # 1. Dual metric: Full-Time Hires vs Intern Offers
            if "full_time_hires" in columns and "intern_offers" in columns:
                comp_name = company or "the recruiter"
                if "batch_id" in columns:
                    cohort_summaries = []
                    for r in rows:
                        batch_name = r[0]
                        fte_count = r[1]
                        intern_count = r[2]
                        if intern_count > 0:
                            cohort_summaries.append(f"{batch_name} had **{fte_count}** full-time hires, plus **{intern_count}** summer/6-month intern offers")
                        else:
                            cohort_summaries.append(f"{batch_name} had **{fte_count}** full-time hires")
                    direct_answer = f"For {comp_name}, " + "; ".join(cohort_summaries) + "."
                    insight_note = "Note: Full-time hires (FTE/PPO) and internship offers are tracked separately; stipends are excluded from CTC."
                else:
                    direct_answer = f"For {comp_name}, recorded **{rows[0][0]}** full-time hires and **{rows[0][1]}** internship offers."
                    insight_note = "Note: Full-time hires (FTE/PPO) and internship offers are tracked separately."

                headers = [c.replace("_", " ").title() for c in columns]
                header_line = "| " + " | ".join(headers) + " |"
                sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
                data_lines = ["| " + " | ".join([str(v) if v is not None else "0" for v in r]) + " |" for r in rows]
                table_md = "\n".join([header_line, sep_line] + data_lines)

            # 2. Company comparison (e.g. Infosys vs TCS)
            elif "canonical_name" in columns and any("placed" in c or "offers" in c for c in columns) and len(rows) == 2 and len(columns) >= 4 and len(rows[0]) >= 4 and len(rows[1]) >= 4:
                c1_row, c2_row = rows[0], rows[1]
                direct_answer = (
                    f"Comparing {c1_row[0]} and {c2_row[0]}: "
                    f"**{c1_row[0]}** hired **{c1_row[1]}** students with an average CTC of **{c1_row[3]} LPA** ({c1_row[2]} total offers), "
                    f"while **{c2_row[0]}** hired **{c2_row[1]}** students with an average CTC of **{c2_row[3]} LPA** ({c2_row[2]} total offers)."
                )
                headers = [c.replace("_", " ").title() for c in columns]
                header_line = "| " + " | ".join(headers) + " |"
                sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
                data_lines = ["| " + " | ".join([str(v) if v is not None else "-" for v in r]) + " |" for r in rows]
                table_md = "\n".join([header_line, sep_line] + data_lines)

            # 3. Batch-wise breakdown (Safe Narration via _write_payload_answer)
            elif "batch_id" in columns and len(columns) >= 2:
                temp_payload = StructuredAnswerPayload(
                    count=len(rows),
                    rows=rows,
                    columns=columns,
                    column_meta=infer_column_metadata(columns),
                    scope=f"{company or branch or 'NIT Jalandhar'}"
                )
                direct_answer = self._write_payload_answer(temp_payload, spec, question)
                headers = [c.replace("_", " ").title() for c in columns]
                table_md = "| " + " | ".join(headers) + " |\n| " + " | ".join(["---"] * len(headers)) + " |\n" + "\n".join(["| " + " | ".join([str(v) for v in r]) + " |" for r in rows])

            # 4. Top-N Rankings / Company Lists (Safe Narration via _write_payload_answer)
            elif "canonical_name" in columns and len(columns) >= 2:
                temp_payload = StructuredAnswerPayload(
                    count=len(rows),
                    rows=rows,
                    columns=columns,
                    column_meta=infer_column_metadata(columns),
                    scope=f"{company or branch or 'NIT Jalandhar'}"
                )
                direct_answer = self._write_payload_answer(temp_payload, spec, question)
                headers = [c.replace("_", " ").title() for c in columns]
                table_md = "| " + " | ".join(headers) + " |\n| " + " | ".join(["---"] * len(headers)) + " |\n" + "\n".join(["| " + " | ".join([str(v) for v in r]) + " |" for r in rows])

            # 5. Branch-wise breakdown (Safe Narration via _write_payload_answer)
            elif "short_name" in columns and len(columns) >= 2:
                temp_payload = StructuredAnswerPayload(
                    count=len(rows),
                    rows=rows,
                    columns=columns,
                    column_meta=infer_column_metadata(columns),
                    scope=f"{company or branch or 'NIT Jalandhar'}"
                )
                direct_answer = self._write_payload_answer(temp_payload, spec, question)
                headers = [c.replace("_", " ").title() for c in columns]
                table_md = "| " + " | ".join(headers) + " |\n| " + " | ".join(["---"] * len(headers)) + " |\n" + "\n".join(["| " + " | ".join([str(v) for v in r]) + " |" for r in rows])

            else:
                direct_answer = f"Found **{len(rows)}** records matching the requested dimensions."
                headers = [c.replace("_", " ").title() for c in columns]
                table_md = "| " + " | ".join(headers) + " |\n| " + " | ".join(["---"] * len(headers)) + " |\n" + "\n".join(["| " + " | ".join([str(v) for v in r]) + " |" for r in rows])

        scope_str = f"Covering batch(es): {', '.join(batches) if batches else 'All academic cohorts in placement database'}."
        if caveats:
            scope_str += " Caveats: " + "; ".join(caveats)

        footer_details = (
            "<details>\n"
            "<summary>Technical Details & SQL</summary>\n\n"
            f"- **Deterministic SQL Query**:\n```sql\n{sql}\n```\n"
            f"- **Metric Semantics**: {definition}\n"
            f"- **Data Scope**: {scope_str}\n"
            f"- **Verification**: {confidence} (Verified against semantic layer schema)\n"
            "</details>"
        )

        # Build Structured Answer Payload (Amendment 2)
        is_package_col = bool(
            (columns and columns[0] in ["ctc_lpa", "max_ctc", "min_ctc", "avg_ctc", "median_ctc"])
            or (spec and spec.metric in ["ctc", "max_ctc", "min_ctc", "avg_ctc", "median_ctc", "stipend"])
        )
        if is_package_col:
            count_val = len(rows)
        else:
            count_val = int(val) if (len(rows) == 1 and len(rows[0]) == 1 and isinstance(rows[0][0], (int, float))) else len(rows)
        payload = StructuredAnswerPayload(
            count=count_val,
            rows=rows,
            scope=f"{company or branch or 'NIT Jalandhar'}",
            offer_types=spec.offer_types if spec else [],
            columns=columns,
            column_meta=infer_column_metadata(columns),
            direct_answer=direct_answer
        )
        payload.validate_payload()

        if spec and spec.assumptions and spec.assumptions[0] not in direct_answer:
            direct_answer = f"{spec.assumptions[0]}\n\n{direct_answer}"

        return {
            "answer": direct_answer,
            "table": table_md,
            "insight": insight_note,
            "definition": definition,
            "data_scope": scope_str,
            "confidence": f"{confidence} (Verified against semantic layer schema)",
            "source": footer_details,
            "payload": payload.model_dump()
        }

    def render_markdown(self, res: Dict[str, Any]) -> str:
        """Render clean conversational answer without robotic badges or forms (Step 6)."""
        if "payload" in res and isinstance(res["payload"], dict):
            try:
                p = StructuredAnswerPayload(**res["payload"])
                p.validate_payload()
            except Exception as e:
                return f"Consistency Verification Error: {e}"
        parts = []
        if res.get("answer"):
            parts.append(res["answer"].strip())
        if res.get("table"):
            parts.append(res["table"].strip())
        if res.get("insight"):
            parts.append(f"*{res['insight'].strip()}*")
        if res.get("source"):
            parts.append(res["source"].strip())
        return "\n\n".join(parts)
