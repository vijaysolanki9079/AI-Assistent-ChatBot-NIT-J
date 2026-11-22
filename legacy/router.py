import re
from typing import Dict, Any, Tuple
from legacy.entity_resolver import EntityResolver

class QuestionRouter:
    def __init__(self):
        self.resolver = EntityResolver()

    def route(self, question: str) -> Dict[str, Any]:
        """
        Classifies query into:
        - category: structured | unstructured | hybrid | ambiguous | out_of_scope
        - sub_category / intent: lookup, count, ranking, etc.
        - reason: explanation of classification
        - resolved_entities: companies, branches, years
        """
        q = question.strip()
        low = q.lower()

        # 1. Privacy Checks (Instant Block)
        privacy_patterns = [
            r'\b(names?|details?|list)\s+(and\s+details?\s+)?of\s+(each|them|students?|candidates?|selected|each\s+of\s+one)\b',
            r'\bgive\s+(me\s+)?(their\s+)?names?\b',
            r'\bshow\s+(me\s+)?(their\s+)?names?\b',
            r'\b(names?|details?)\s+of\s+each\s+one\b',
            r'\bwho\s+(are\s+they|got\s+(placed|selected))\b',
            r'\bstudent\s*names?\b',
            r'\broll\s*(no|number|numbers)\b',
            r'\b(phone|mobile|contact)\s*(no|numbers?|details?)?\b',
            r'\b(email|emails|mail)\s*(id|ids|addresses?)?\b',
            r'\bhr\s*(contact|contacts|email|phone|details?)\b'
        ]
        if any(re.search(pat, low) for pat in privacy_patterns):
            return {
                "category": "out_of_scope",
                "intent": "PRIVACY_BLOCKED",
                "reason": "Request asks for confidential student personal information, individual identity, or HR contact details.",
                "clarification": "For privacy and confidentiality reasons, individual student names, roll numbers, personal contact details, and HR contacts are strictly protected. I can provide aggregated statistics, department distributions, and compensation trends."
            }

        # 2. Out of scope metrics (CGPA, 10th/12th, attendance, etc.)
        untracked_metrics = ["cgpa", "gpa", "10th", "12th", "board percentage", "attendance", "hostel", "mess", "cutoff rank", "jee rank"]
        if any(um in low for um in untracked_metrics):
            return {
                "category": "out_of_scope",
                "intent": "OUT_OF_SCOPE",
                "reason": "Requested metric is not tracked in the placement database.",
                "clarification": "The placement database contains offer packages, companies, offer types, batches, and branch placement counts, but does not record academic CGPA, school board marks, or entrance ranks."
            }

        # 3. Relative temporal references without context ("yesterday", "tomorrow")
        if re.search(r'\b(yesterday|tomorrow|last week|today)\b', low):
            return {
                "category": "out_of_scope",
                "intent": "OUT_OF_SCOPE",
                "reason": "Placement records are indexed by academic batch and historical result dates, not dynamic daily logs.",
                "clarification": "Placement data is recorded by academic cohort (e.g. 2020-2024, 2021-2025). Please specify a batch or graduation year."
            }

        # 4. Out of range historical years (e.g., 2018, 2019, 2015)
        hist_years = re.findall(r'\b(19\d{2}|20[01]\d)\b', low)
        if hist_years and not any(f"{y}-" in low for y in hist_years):
            return {
                "category": "out_of_scope",
                "intent": "NO_DATA",
                "reason": f"Historical placement data for year {hist_years[0]} is not present in the database (coverage begins with 2020 admission cohort).",
                "clarification": "Placement records are available for the 2020-2024 through 2023-2027 academic batches. Earlier years are not archived."
            }

        # 4. Resolve entities
        entities = self.resolver.extract_and_resolve_entities(q)

        # 5. Check for unknown companies that never visited NIT Jalandhar
        # E.g., Apple, Netflix, Meta, Tesla, Palantir
        never_visited = ["apple", "netflix", "meta", "tesla", "palantir", "twitter", "spacex"]
        for nv in never_visited:
            if re.search(r'\b' + nv + r'\b', low):
                return {
                    "category": "out_of_scope",
                    "intent": "NO_DATA",
                    "reason": f"Company '{nv.title()}' has no placement or visit record in the NIT Jalandhar database.",
                    "clarification": f"There are no records of {nv.title()} visiting NIT Jalandhar or making offers in the placement database."
                }

        # 6. Check for non-existent engineering branches (e.g. Aeronautical, Aerospace)
        non_existent_branches = ["aeronautical", "aerospace", "marine", "petroleum", "mining"]
        for nb in non_existent_branches:
            if nb in low:
                return {
                    "category": "out_of_scope",
                    "intent": "NO_DATA",
                    "reason": f"Department '{nb.title()}' does not exist at NIT Jalandhar.",
                    "clarification": f"NIT Jalandhar does not offer an academic program in {nb.title()} Engineering."
                }

        # 7. Check for Vague / Ambiguous questions
        vague_patterns = [
            r'^(tell me about placements|how are placements|placement details|placement info|give me stats)\??$',
            r'^(which branch is the best|best branch|best company)\??$'
        ]
        if any(re.match(vp, low) for vp in vague_patterns):
            return {
                "category": "ambiguous",
                "intent": "CLARIFICATION_REQUIRED",
                "reason": "The question is too broad or subjective.",
                "clarification": "Could you please specify which aspect you are interested in? For example: highest package, average CTC, placement percentage, or specific branches/batches?"
            }

        # 8. Check for Hybrid (SQL + RAG interview experience)
        interview_keywords = ["interview", "asked in", "questions", "interview rounds", "technical round", "hr round", "online assessment", "oa", "coding test", "preparation", "prep"]
        has_interview = any(ik in low for ik in interview_keywords)
        has_data = any(dk in low for dk in ["ctc", "package", "hired", "offers", "placed", "stipend", "lpa", ">", "<", "above", "top", "how many", "companies"])

        if has_interview and has_data:
            return {
                "category": "hybrid",
                "intent": "HYBRID",
                "entities": entities,
                "reason": "Requires SQL query for placement metrics and RAG retrieval for interview experiences."
            }
        elif has_interview and not has_data:
            return {
                "category": "unstructured",
                "intent": "RAG_ONLY",
                "entities": entities,
                "reason": "Focuses on alumni interview experience and questions asked."
            }

        # 9. Default to Structured SQL query
        return {
            "category": "structured",
            "intent": "SQL_QUERY",
            "entities": entities,
            "reason": "Query can be answered deterministically via semantic SQL execution."
        }
