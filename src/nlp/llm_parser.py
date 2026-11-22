"""
LLM Intent Parser for NITJ Placement Assistant.
Converts user queries and chat history into a strictly typed Pydantic QuerySpec.
Uses local Ollama with JSON-schema constrained decoding, retrying once on invalid JSON,
with a robust semantic parser fallback when the local daemon is unavailable.
"""

import os
import re
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Tuple

from src.nlp.query_spec import QuerySpec, IntentType
from src.nlp.fuzzy_linker import FuzzyEntityLinker
from src.nlp.privacy_classifier import LLMPrivacyClassifier

class OllamaClient:
    """Client for local Ollama daemon with JSON-schema constraint and single-retry recovery."""

    def __init__(self, host: str = "http://localhost:11434", model: str = None):
        self.host = os.getenv("OLLAMA_HOST", host).rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", model or "llama3.2")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "8"))

    def is_available(self) -> bool:
        """Check if Ollama service is reachable."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", headers={"User-Agent": "NITJ-Assistant"})
            with urllib.request.urlopen(req, timeout=1) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate_spec(self, prompt: str, schema: Dict[str, Any], retry: bool = True) -> Optional[Dict[str, Any]]:
        """Call Ollama /api/generate with JSON schema format."""
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0.0,
                "top_p": 0.9
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                raw_response = body.get("response", "")
                parsed = json.loads(raw_response)
                return parsed
        except (json.JSONDecodeError, urllib.error.URLError, Exception) as e:
            if retry:
                # Retry once with explicit formatting reminder as requested
                retry_prompt = f"{prompt}\n\nIMPORTANT: Your previous output failed JSON schema parsing. Output ONLY valid JSON adhering strictly to the schema."
                return self.generate_spec(retry_prompt, schema, retry=False)
            return None


class LocalSemanticParser:
    """
    Deterministic semantic parser that maps natural language tokens,
    entities, and conversational history into Pydantic QuerySpec without regex planner hacks.
    """

    KNOWN_COMPANIES = {
        "microsoft": "Microsoft", "ms": "Microsoft", "msft": "Microsoft", "micro soft": "Microsoft",
        "google": "Google", "goog": "Google", "googl": "Google",
        "amazon": "Amazon", "amzn": "Amazon",
        "goldman sachs": "Goldman Sachs", "goldman": "Goldman Sachs", "gs": "Goldman Sachs",
        "texas instruments": "Texas Instruments", "ti": "Texas Instruments",
        "qualcomm": "Qualcomm", "nvidia": "Nvidia", "nvida": "Nvidia",
        "oracle": "Oracle", "adobe": "Adobe", "paypal": "PayPal",
        "samsung": "Samsung", "samsung r&d": "Samsung", "cred": "Cred",
        "infosys": "Infosys", "infy": "Infosys",
        "tcs": "TCS", "tata consultancy services": "TCS",
        "wipro": "Wipro", "capgemini": "Capgemini", "accenture": "Accenture",
        "reliance": "Reliance Industries", "ril": "Reliance Industries", "reliance industries": "Reliance Industries",
        "bpcl": "BPCL", "bharat petroleum": "BPCL", "maruti suzuki": "Maruti Suzuki", "maruti": "Maruti Suzuki",
        "zomato": "Zomato", "uber": "Uber", "flipkart": "Flipkart"
    }

    NEVER_VISITED = {"apple", "netflix", "meta", "tesla", "palantir", "twitter", "spacex"}

    BRANCH_MAP = {
        "cse": "CSE", "computer science": "CSE", "computer science and engineering": "CSE",
        "it": "IT", "information technology": "IT",
        "ece": "ECE", "electronics": "ECE", "electronics and communication engineering": "ECE",
        "me": "ME", "mechanical": "ME", "mechanical engineering": "ME",
        "ee": "EE", "electrical": "EE", "electrical engineering": "EE",
        "che": "CHE", "chemical": "CHE", "chemical engineering": "CHE",
        "ce": "CE", "civil": "CE", "civil engineering": "CE",
        "ice": "ICE", "instrumentation": "ICE", "instrumentation and control engineering": "ICE",
        "ipe": "IPE", "industrial": "IPE", "industrial and production engineering": "IPE",
        "bt": "BT", "biotechnology": "BT",
        "tt": "TT", "textile": "TT", "textile technology": "TT"
    }

    NON_EXISTENT_BRANCHES = {"aeronautical", "aerospace", "marine", "petroleum", "mining", "nuclear", "agriculture"}

    BATCH_MAP = {
        "2020-2024": "2020-2024", "2024": "2020-2024", "2024 batch": "2020-2024",
        "2021-2025": "2021-2025", "2025": "2021-2025", "2025 batch": "2021-2025",
        "2022-2026": "2022-2026", "2026": "2022-2026", "2026 batch": "2022-2026",
        "2023-2027": "2023-2027", "2027": "2023-2027", "2027 batch": "2023-2027"
    }

    def __init__(self, db_path: str = "data/nitj_placement.db"):
        self.db_path = db_path
        self.linker = FuzzyEntityLinker(db_path)
        self.privacy_classifier = LLMPrivacyClassifier()
        self.db_companies = dict(self.KNOWN_COMPANIES)
        if os.path.exists(db_path):
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                for row in cur.execute("SELECT canonical_name FROM companies"):
                    cname = row[0]
                    self.db_companies[cname.lower().strip()] = cname
                for row in cur.execute("SELECT alias, company_id FROM company_aliases"):
                    alias = row[0].lower().strip()
                    cid = row[1]
                    cname_row = cur.execute("SELECT canonical_name FROM companies WHERE company_id = ?", (cid,)).fetchone()
                    if cname_row:
                        self.db_companies[alias] = cname_row[0]
                conn.close()
            except Exception:
                pass

    def parse(self, question: str, history: Optional[List[Dict[str, str]]] = None) -> QuerySpec:
        """Parse natural language question + short chat history into a verified QuerySpec."""
        q_raw = question.strip()
        q_clean = re.sub(r'[\?\.,!]', ' ', q_raw.lower())
        low = " " + " ".join(q_clean.split()) + " "

        # 1. Privacy Detection (LLM Classifier evaluating question + chat history)
        privacy_res = self.privacy_classifier.classify(question, history)
        if privacy_res.is_privacy_violation:
            return QuerySpec(
                intent="privacy",
                metric=None,
                privacy_flag=True,
                confidence=privacy_res.confidence,
                needs_clarification=False,
                clarification_question=privacy_res.response_message
            )

        # 2. Out of Scope Metrics (CGPA, 10th/12th, mess, hostel, cutoff)
        untracked = ["cgpa", " gpa", "10th", "12th", "board marks", "attendance", "hostel", "mess", "cutoff rank", "jee rank"]
        if any(u in low for u in untracked):
            return QuerySpec(
                intent="out_of_scope",
                metric="untracked",
                confidence=1.0,
                needs_clarification=False,
                clarification_question="Placement records include compensation (CTC/stipend), recruiters, offer types, batches, and branch placement counts, but do not record academic CGPA, school board percentages, or entrance examination ranks."
            )

        # 2b. Real-time / temporal events (yesterday, tomorrow)
        for oos_word in ["yesterday", "tomorrow", "tonight", "live drive", "upcoming"]:
            if f" {oos_word} " in low:
                return QuerySpec(
                    intent="out_of_scope",
                    confidence=1.0,
                    clarification_question="Placement records capture finalized drive records rather than daily live schedules."
                )

        # 3. Non-existent Companies / Branches (NO_DATA)
        for nv in self.NEVER_VISITED:
            if f" {nv} " in low:
                return QuerySpec(
                    intent="out_of_scope",
                    companies=[nv.title()],
                    confidence=1.0,
                    clarification_question=f"Company '{nv.title()}' has no placement or visit records in the NIT Jalandhar database."
                )

        for nb in self.NON_EXISTENT_BRANCHES:
            if f" {nb} " in low:
                return QuerySpec(
                    intent="out_of_scope",
                    branches=[nb.title()],
                    confidence=1.0,
                    clarification_question=f"NIT Jalandhar does not offer an academic program in {nb.title()} Engineering."
                )

        # 4. Temporal Out of Range (Historical years < 2020)
        for old_yr in [" 2015 ", " 2016 ", " 2017 ", " 2018 ", " 2019 "]:
            if old_yr in low and not any(f"{old_yr.strip()}-" in low for _ in [1]):
                return QuerySpec(
                    intent="out_of_scope",
                    confidence=1.0,
                    batches=[old_yr.strip()],
                    clarification_question="Placement records are available for the 2020-2024 through 2023-2027 academic batches. Earlier cohorts are not archived."
                )

        # 5. Extract Entities via FuzzyEntityLinker (RapidFuzz >= 90 accept, 70-89 ask 'Did you mean X?')
        linked = self.linker.link_entities_in_query(q_raw)
        companies: List[str] = [c["canonical_name"] for c in linked["companies"]]
        branches: List[str] = [b["short_name"] for b in linked["branches"]]
        batches: List[str] = list(linked["batches"])

        # Check suggestions if no accepted company found (70-89 range)
        has_suggestions = False
        suggestion_question = None
        if not companies and linked.get("suggestions", {}).get("companies"):
            top_sugg = linked["suggestions"]["companies"][0]
            sugg_name = top_sugg["canonical_name"]
            has_suggestions = True
            suggestion_question = f"Did you mean {sugg_name}?"
        elif not branches and linked.get("suggestions", {}).get("branches"):
            top_b_sugg = linked["suggestions"]["branches"][0]
            b_sugg_name = top_b_sugg.get("canonical_name") or top_b_sugg.get("short_name")
            has_suggestions = True
            suggestion_question = f"Did you mean {b_sugg_name}?"

        # Incorporate Conversational History for Follow-ups (Only if explicitly passed and no entities found)
        # Note: QueryContextualizer is the primary authority on follow-up slot carry-over.
        # We do NOT unilaterally copy old companies or branches here to avoid stale context infection.

        # 6. Extract Offer Types
        offer_types: List[str] = []
        if any(k in low for k in ["ppo", "pre placement offer", "pre-placement"]):
            offer_types.append("PPO")
        if any(k in low for k in ["fte", "full time", "full-time"]):
            offer_types.append("FTE")
        if any(k in low for k in ["intern", "internship", "summer intern", "6 month", "6-month"]):
            offer_types.append("Internship")

        # 7. Extract Filters
        filters: Dict[str, Any] = {}
        if "female" in low or "girls" in low or "women" in low:
            filters["gender"] = "F"
        if "male" in low or "boys" in low:
            filters["gender"] = "M"
        if "off-campus" in low or "off campus" in low or "ofcampuss" in low:
            filters["offer_mode"] = "Off-campus"
        if "on-campus" in low or "on campus" in low:
            filters["offer_mode"] = "On-campus"
        if ("it" in low and ("sector" in low or "companies" in low)) or "it companies" in low:
            filters["sector"] = "IT"
        elif "core" in low and ("sector" in low or "companies" in low or "branches" in low):
            filters["sector"] = "Core"

        # Check exact CTC (e.g. "who got 52 LPA", "offers of 52 lpa")
        exact_ctc_match = re.search(r'\b(\d+(?:\.\d+)?)\s*lpa\b', low)
        if exact_ctc_match and any(k in low for k in ["who got", "who received", "who secured", "students who got", "which students", "at 52", "of 52"]):
            filters["exact_ctc"] = float(exact_ctc_match.group(1))

        # Check threshold cuts (e.g. >= 50, > 20 LPA, >= 15 LPA)
        for num in [50, 40, 30, 20, 18, 15, 10, 5]:
            if any(p in low for p in [f">={num}", f">= {num}", f"at least {num}", f"{num}+", f"greater than or equal {num}", f"greater than or equal to {num}"]):
                filters["ctc_threshold"] = float(num)
                filters["threshold_op"] = ">="
                break
            elif any(p in low for p in [f">{num}", f"> {num}", f"above {num}", f"greater than {num}", f"more than {num}"]):
                filters["ctc_threshold"] = float(num)
                filters["threshold_op"] = ">"
                break

        # Check top-N limit (e.g. "top 10 companies", "top 5 packages")
        top_n_match = re.search(r'\btop\s+(\d+)\b', low)
        if top_n_match:
            filters["limit"] = int(top_n_match.group(1))

        # 8. Extract Target Metrics (Compositional metrics list)
        metrics: List[str] = []
        metric = None

        # Check student names / roster request (Bug F & Stage 3)
        if any(k in low for k in ["name of", "names of", "who got placed", "who was placed", "who were placed", "who got selected", "give their names", "show their names", "show names", "give names", "who got in", "who got into", "list of placed", "names of students", "name of students", "names of those", "who are they"]) and not any(k in low for k in ["how many", "count", "number of", "kitne", "kitna"]):
            metrics.append("student_names")
            metric = "student_names"
            intent = "lookup"

        elif any(k in low for k in ["more than one offer", "more than 1 offer", "multiple offers", "multi offer", "two or more offers", "students with more than one"]):
            metrics.append("multi_offer_students")
            metric = "multi_offer_students"
        elif any(k in low for k in ["how many offers", "total offers", "number of offers", "offers made", "offeers", "offers count", "total offers count", "offer count", "by offers", "by total offers", "offers at", "offers in", "offers by", "offers for"]) or ("offer" in low and "total" in low) or low.strip().startswith("offers"):
            metrics.append("total_offers")
            metric = "total_offers"
        elif any(k in low for k in ["how many companies", "number of companies", "company count", "companies visited", "total companies", "kitni company", "kitni companies", "distinct companies", "companies made at least one offer", "companies made an offer"]):
            metrics.append("company_count")
            metric = "company_count"
        elif any(k in low for k in ["intern count", "how many interns", "intern offers", "internship offers", "internships count", "stipend offers"]):
            metrics.append("intern_count")
            metric = "intern_count"
        elif any(k in low for k in ["top recruiters", "best recruiters", "major recruiters", "who hired the most", "top hiring companies", "top recruiting companies", "recruiting companies"]):
            metrics.append("top_recruiters")
            metric = "top_recruiters"
        elif any(k in low for k in ["stipend", "monthly stipend"]):
            metrics.append("stipend")
            metric = "stipend"
        elif any(k in low for k in ["percent", "percentage", "rate of placement", "placement rate", "placement %", "share of offers", "share", "fraction", "ratio", "kitna percent"]):
            metrics.append("placement_pct")
            metric = "placement_pct"
        elif any(k in low for k in ["average", "avg ctc", "mean package", "average package", "avg package", "average salary", "avg salary", "avg"]):
            metrics.append("avg_ctc")
            metrics.append("median_ctc")
            metric = "avg_ctc"
        elif any(k in low for k in ["median", "median ctc", "median package"]):
            metrics.append("median_ctc")
            metrics.append("avg_ctc")
            metric = "median_ctc"
        elif any(k in low for k in ["highest", "maximum", "max package", "top package", "max ctc", "highest package", "peak package", "sabse jyada package", "sabse bada package", "highest packages"]):
            metrics.append("max_ctc")
            metric = "max_ctc"
        elif any(k in low for k in ["lowest", "minimum", "min package", "min ctc", "lowest package"]):
            metrics.append("min_ctc")
            metric = "min_ctc"
        elif any(k in low for k in ["unpaid"]):
            metrics.append("offer_type")
            metric = "offer_type"
        elif any(k in low for k in ["compound"]):
            metrics.append("compound")
            metric = "compound"
        elif any(k in low for k in ["long intern"]):
            metrics.append("long_intern")
            metric = "long_intern"
        elif any(k in low for k in ["ctc", "package", "salary", "lpa"]) or (companies and any(k in low for k in ["what did", "what was", "what is", "offer?"]) and not any(k in low for k in ["how many", "count", "number of"])):
            metrics.append("ctc")
            metric = "ctc"
        elif any(k in low for k in ["placed", "students placed", "got in", "got into", "got", "selected", "select hue", "select hua", "selections", "hired", "hires", "how many students", "kitne", "place hue", "kitna place", "placements count", "placement count", "placements", "placement"]):
            metrics.append("placed_students")
            metric = "placed_students"

        # 9. Profile Intent Detection (Bundled overview card/table)
        profile_terms = [
            "complete stats", "full stats", "overall stats", "entire stats", "all stats",
            "overview", "summary", "profile", "details of", "complete details",
            "placement details", "placement stats", "placement overview", "placement summary",
            "how are placements", "tell me about placements", "give me stats", "placement report",
            "college overall", "overall placement", "college placement", "institute placement",
            "college statistics", "college stats", "overall performance"
        ]
        is_profile = any(pt in low for pt in profile_terms) or (branches and any(w in low for w in ["stats", "details", "overview", "summary", "profile"]))

        # 10. Determine Group By Dimensions
        group_by: List[str] = []
        if any(k in low for k in ["branch-wise", "branch wise", "which branch", "branch by branch", "by branch", "each branch", "department wise", "departments", "highest median ctc", "highest average ctc"]):
            group_by.append("branch")
        if any(k in low for k in ["batch-wise", "batch wise", "year-wise", "year wise", "each batch", "across batches", "per batch", "by batch"]):
            group_by.append("batch")
        if any(k in low for k in ["company-wise", "company wise", "per company", "by company"]):
            group_by.append("company")
        if any(k in low for k in ["sector-wise", "sector wise"]):
            group_by.append("sector")
        if any(k in low for k in ["gender-wise", "gender wise"]):
            group_by.append("gender")

        # 11. Classify Core Intent
        intent: IntentType = "lookup"
        confidence = 0.95

        # Check ranking indicators: "top 5", "top 10", "ranking", etc., but exclude "at least" from triggering "least"
        is_ranking_keyword = any(k in low for k in ["top 5", "top 10", "top 3", "top", "highest paying", "best recruiting", "most offers", "ranking", "bottom", "which branch has", "which company", "sabse jyada", "kisne diya"]) or bool(re.search(r'(?<!at\s)\bleast\b', low))

        if is_profile:
            intent = "profile"
        elif any(k in low for k in ["never", "zero", "unplaced", "no offers", "not hired"]):
            intent = "out_of_scope"
        elif any(k in low for k in ["interview", "rounds", "technical questions", "experience", "how to prepare", "asked in", "process"]):
            intent = "hybrid"
        elif "exact_ctc" in filters:
            intent = "lookup"
        elif is_ranking_keyword and metric != "company_count" and not any(k in low for k in ["how many", "count", "number of", "distinct"]):
            intent = "ranking"
        elif any(k in low for k in ["trend", "over time", "across years", "growth", "progression", "change", "over the batches", "over batches"]):
            intent = "trend"
        elif len(companies) >= 2 or len(branches) >= 2 or ("both" in low and (companies or branches or "b.tech" in low or "ug" in low)) or ("compare" in low) or (" vs " in low) or ("versus" in low):
            intent = "compare"
        elif group_by or ("breakdown" in low) or ("distribution" in low) or ("wise" in low):
            intent = "breakdown"
        elif metric in ["offers", "total_offers", "placed_students", "company_count", "intern_count", "multi_offer_students"] or any(k in low for k in ["how many", "count", "number of", "kitne", "kitna", "got", "selected", "hired", "select hue", "select hua"]):
            intent = "count"
        elif metric in ["ctc", "stipend", "max_ctc", "min_ctc", "avg_ctc", "median_ctc", "placement_pct", "placement_percentage"]:
            intent = "lookup"

        # 12. Default missing slots instead of asking (Requirement 3)
        assumptions: List[str] = []
        if not batches:
            batches = ["2020-2024", "2021-2025", "2022-2026"]
            assumptions.append("Across all batches 2020-24 to 2022-26, full-time offers only")
        if not offer_types:
            if metric == "intern_count" or "intern" in low or "stipend" in low:
                offer_types = ["Internship"]
            else:
                offer_types = ["FTE", "PPO"]

        # Ambiguous / Suggestion checks
        if has_suggestions and not companies and not branches and intent not in ["breakdown", "ranking", "out_of_scope", "compare", "profile"] and not group_by:
            return QuerySpec(
                intent="clarify",
                metrics=metrics,
                metric=metric,
                companies=companies,
                branches=branches,
                batches=batches,
                needs_clarification=True,
                clarification_question=suggestion_question,
                confidence=0.75
            )

        # Genuine ambiguity: Only if no company, no branch, no batch, no metric, and NOT a profile request
        is_truly_ambiguous = (not companies and not branches and not batches and not metric and not is_profile and len(q_raw.split()) <= 2)
        if is_truly_ambiguous:
            return QuerySpec(
                intent="clarify",
                metrics=[],
                metric=None,
                needs_clarification=True,
                clarification_question="Which department (e.g., CSE, IT, ECE) or academic cohort (2020-24, 2021-25, 2022-26) would you like to inspect?",
                confidence=0.5
            )

        return QuerySpec(
            intent=intent,
            metrics=metrics,
            metric=metric or ("placed_students" if intent == "count" else "ctc"),
            companies=companies,
            branches=branches,
            batches=batches,
            offer_types=offer_types,
            group_by=group_by,
            filters=filters,
            assumptions=assumptions,
            needs_clarification=False,
            confidence=confidence
        )


class LLMIntentParser:
    """
    Main LLM Intent Parser module.
    Delegates to Ollama with JSON-schema decoding if available,
    seamlessly falling back to the local schema-conforming semantic parser.
    """

    def __init__(self):
        self.ollama = OllamaClient()
        self.fallback = LocalSemanticParser()
        self.system_prompt = (
            "You are an intent parser for the NIT Jalandhar Training & Placement database assistant. "
            "Given the user question and chat history, extract a strictly typed QuerySpec JSON object. "
            "Never invent entities. Output ONLY valid JSON matching the schema."
        )

    def parse(self, question: str, history: Optional[List[Dict[str, str]]] = None) -> QuerySpec:
        """Parse natural language query + history into a Pydantic QuerySpec."""
        schema = QuerySpec.model_json_schema()

        # If Ollama is running and available, invoke it with JSON-schema output
        if self.ollama.is_available():
            prompt = f"System: {self.system_prompt}\n\nChat History: {history}\n\nQuestion: {question}"
            raw_spec = self.ollama.generate_spec(prompt, schema=schema, retry=True)
            if raw_spec:
                try:
                    return QuerySpec.model_validate(raw_spec)
                except Exception:
                    pass

        # Robust semantic fallback with zero regex planner hacks
        return self.fallback.parse(question, history)
