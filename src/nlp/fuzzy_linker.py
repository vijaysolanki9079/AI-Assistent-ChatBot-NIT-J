"""
Fuzzy Entity Linker for NITJ Placement Assistant.
Implements RapidFuzz entity linking over canonical database alias tables
with strict threshold boundaries, 2-letter acronym whitelist,
canonical branch master resolution, and roll-number prefix batch derivation.
"""

import os
import re
import sqlite3
from typing import Dict, List, Optional, Tuple, Any
from rapidfuzz import fuzz, process

DB_PATH = "data/nitj_placement.db"

class FuzzyEntityLinker:
    """
    High-precision entity linker conforming strictly to Step 2 requirements:
    - >= 90: Accept automatically
    - 70 - 89: Ask 'Did you mean X?'
    - < 70: Ask for clarification (rejected)
    - 2-letter acronyms (MS, GS, TI, HP, EY) strictly via alias whitelist, never fuzzy.
    - Canonical branch master table matching.
    - Batch derived from roll-number prefix and standard formats.
    """

    TWO_LETTER_WHITELIST: Dict[str, str] = {
        "ms": "Microsoft",
        "gs": "Goldman Sachs",
        "ti": "Texas Instruments",
        "hp": "HP",
        "ey": "EY"
    }

    DISALLOWED_WORDS = {
        # Common grammar / question / domain words that must never be fuzzy matched to companies
        "what", "which", "how", "many", "students", "were", "was", "got", "given", "placed",
        "branch", "branches", "batch", "batches", "package", "packages", "offers", "offered", "offer",
        "branch-wise", "branchwise", "company-wise", "companywise", "batch-wise", "batchwise",
        "year-wise", "yearwise", "sector-wise", "sectorwise", "gender-wise", "genderwise",
        "category-wise", "categorywise", "wise", "cohort", "cohorts", "most", "bottom", "best",
        "b.tech", "m.tech", "ug", "pg", "placements", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
        "highest", "lowest", "maximum", "minimum", "top", "rank", "ranking", "median",
        "mean", "average", "overall", "total", "number", "count", "between", "difference", "compare",
        "breakdown", "distribution", "unplaced", "all", "each", "every", "more", "less", "above",
        "below", "greater", "least", "stipend", "salary", "ctc", "lpa", "inr", "ratio", "percentage",
        "percent", "share", "rate", "both", "either", "neither", "also", "with", "from", "and", "for",
        "in", "at", "by", "to", "of", "about", "did", "does", "are", "is", "have", "had",
        "get", "make", "made", "tell", "show", "fast", "sun", "yaar", "bhai", "kitna", "kitne",
        "hai", "kya", "tha", "hue", "please", "double", "never", "zero", "female", "male", "boys",
        "girls", "gender", "off-campus", "on-campus", "core", "circuit", "btech", "mtech", "degree",
        "division", "engineering", "technology", "tech", "placement", "internship", "intern", "interns", "institute", "college",
        "school", "department", "dept", "record", "records", "details", "data", "info", "information",
        "round", "rounds", "technical", "hr", "experience", "questions", "campus", "year", "years",
        "annual", "month", "monthly", "job", "jobs", "hired", "hire", "selected", "select", "recruited",
        "recruit", "recruiter", "recruiters", "company", "companies", "like", "same", "tell me",
        "compound", "unpaid", "converted", "confirmation"
    }

    DEGREE_TERMS = {
        "b tech", "m tech", "btech", "mtech", "b.tech", "m.tech", "ug", "pg", "b. tech", "m. tech"
    }

    ROLL_PREFIX_BATCH_MAP = {
        "20": "2020-2024",
        "21": "2021-2025",
        "22": "2022-2026",
        "23": "2023-2027",
        "24": "2024-2028"
    }

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.companies: Dict[str, int] = {}              # Canonical name -> ID
        self.id_to_company: Dict[int, str] = {}           # ID -> Canonical name
        self.company_aliases: Dict[str, str] = {}        # Alias (lower) -> Canonical name
        self.branches: Dict[str, Dict[str, Any]] = {}    # Branch Code -> Metadata
        self.branch_aliases: Dict[str, str] = {}         # Branch alias (lower) -> Branch Code
        self.batches: List[str] = []
        self._load_metadata()

    def _load_metadata(self):
        if not os.path.exists(self.db_path):
            return

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # 1. Canonical Companies & Aliases
        for cid, cname in cur.execute("SELECT company_id, canonical_name FROM companies").fetchall():
            self.companies[cname] = cid
            self.id_to_company[cid] = cname
            self.company_aliases[cname.lower().strip()] = cname

        for alias, cid in cur.execute("SELECT alias, company_id FROM company_aliases").fetchall():
            alias_clean = alias.lower().strip()
            if cid in self.id_to_company:
                self.company_aliases[alias_clean] = self.id_to_company[cid]

        # Explicit 2-letter acronym whitelist
        for short_alias, canon in self.TWO_LETTER_WHITELIST.items():
            self.company_aliases[short_alias] = canon

        # Common distinctive brand token aliases
        brand_tokens = {
            "Goldman Sachs": ["goldman", "gs"],
            "Microsoft": ["ms", "msft", "micro soft", "micorsoft"],
            "Amazon": ["amzn", "amazon india"],
            "Google": ["goog", "googl", "google india"],
            "Infosys": ["infy", "infosys limited", "infosys tech"],
            "Reliance": ["reliance", "ril", "jio"],
            "TCS": ["tcs", "tata consultancy services", "tata consultancy"],
            "Texas Instruments": ["ti"],
            "HP": ["hp", "hewlett packard"],
            "EY Global": ["ey", "ey global"],
            "Maruti Suzuki": ["maruti"],
            "BPCL": ["bpcl", "bharat petroleum"]
        }
        for cname, aliases in brand_tokens.items():
            for a in aliases:
                self.company_aliases[a.lower()] = cname

        # 2. Canonical Branch Master Table
        for bcode, cname, sname, degree, division in cur.execute(
            "SELECT branch_code, canonical_name, short_name, degree, division FROM branches"
        ).fetchall():
            self.branches[bcode] = {
                "branch_code": bcode,
                "canonical_name": cname,
                "short_name": sname,
                "degree": degree,
                "division": division
            }
            self.branch_aliases[sname.lower()] = bcode
            self.branch_aliases[cname.lower()] = bcode

        for alias, bcode in cur.execute("SELECT alias, branch_code FROM branch_aliases").fetchall():
            self.branch_aliases[alias.lower().strip()] = bcode

        # 3. Batches
        for b_row in cur.execute("SELECT batch_id FROM batches").fetchall():
            self.batches.append(b_row[0])

        conn.close()

    def link_company(self, query_token: str) -> Optional[Dict[str, Any]]:
        """
        Link candidate company string to canonical company:
        - Exact alias or canonical match -> 100.0 (Accept)
        - 2-letter tokens -> strictly via TWO_LETTER_WHITELIST, never fuzzy.
        - RapidFuzz match:
            >= 90: Accept
            70 - 89: Suggest ('Did you mean X?')
            < 70: Rejected (None)
        """
        clean = query_token.strip().lower()
        clean = re.sub(r'[\?\.,!]', '', clean).strip()

        if not clean or clean in self.DEGREE_TERMS or clean in self.DISALLOWED_WORDS:
            return None

        # Known branch acronyms must NEVER fuzzy-match to companies (Bug G Fix)
        if clean in self.branch_aliases and clean not in self.TWO_LETTER_WHITELIST:
            return None

        # Rule 1: 2-letter acronym check
        if len(clean) <= 2:
            if clean in self.TWO_LETTER_WHITELIST:
                canon = self.TWO_LETTER_WHITELIST[clean]
                return {
                    "canonical_name": canon,
                    "id": self.companies.get(canon),
                    "status": "ACCEPTED",
                    "score": 100.0,
                    "match_type": "exact_2letter_whitelist"
                }
            # 2-letter strings are NEVER fuzzy matched
            return None

        # Rule 2: Exact alias table check
        if clean in self.company_aliases:
            canon = self.company_aliases[clean]
            return {
                "canonical_name": canon,
                "id": self.companies.get(canon),
                "status": "ACCEPTED",
                "score": 100.0,
                "match_type": "exact_alias"
            }

        # Rule 2b: Suffix stripping (India, Technologies, Solutions, Pvt Ltd, etc.)
        clean_stripped = re.sub(r'\b(india|technologies|technology|solutions|solution|pvt\s*ltd|private\s*limited|limited|ltd|corp|corporation|inc)\b', '', clean).strip()
        if clean_stripped and clean_stripped in self.company_aliases:
            canon = self.company_aliases[clean_stripped]
            return {
                "canonical_name": canon,
                "id": self.companies.get(canon),
                "status": "ACCEPTED",
                "score": 100.0,
                "match_type": "exact_alias_stripped"
            }

        # Rule 3: RapidFuzz matching across alias table (excluding 2-letter acronyms)
        search_space = [k for k in self.company_aliases.keys() if len(k) > 2]
        match = process.extractOne(clean, search_space, scorer=fuzz.ratio)
        if match:
            matched_alias, score, _ = match
            canon = self.company_aliases[matched_alias]
            cid = self.companies.get(canon)

            if score >= 90.0:
                return {
                    "canonical_name": canon,
                    "id": cid,
                    "status": "ACCEPTED",
                    "score": round(score, 1),
                    "match_type": "rapidfuzz_high_confidence",
                    "matched_alias": matched_alias
                }
            elif score >= 82.0 and len(clean) >= 4 and len(matched_alias) >= 4:
                return {
                    "canonical_name": canon,
                    "id": cid,
                    "status": "SUGGESTION",
                    "score": round(score, 1),
                    "match_type": "rapidfuzz_suggestion",
                    "matched_alias": matched_alias,
                    "suggestion": f"Did you mean {canon}?"
                }

        return None

    def link_branch(self, query_token: str, allow_me: bool = False) -> Optional[Dict[str, Any]]:
        """
        Link candidate branch token to canonical branch master table:
        - Exact alias -> 100.0
        - RapidFuzz matching:
            >= 90: Accept
            70 - 89: Suggest ('Did you mean X?')
            < 70: Rejected
        """
        clean = query_token.strip().lower()
        clean = re.sub(r'[\?\.,!]', '', clean).strip()

        if not clean or clean in self.DEGREE_TERMS:
            return None

        if clean == "me" and not allow_me:
            return None

        # Short acronym / exact branch alias check (e.g. cse, it, ece, me, ee, che, ce, bt, tt, textile technology)
        if clean in self.branch_aliases:
            bcode = self.branch_aliases[clean]
            bdata = self.branches.get(bcode, {})
            return {
                "branch_code": bcode,
                "short_name": bdata.get("short_name", bcode),
                "canonical_name": bdata.get("canonical_name", bcode),
                "status": "ACCEPTED",
                "score": 100.0,
                "match_type": "exact_branch_alias"
            }

        if clean in self.DISALLOWED_WORDS:
            return None

        if len(clean) <= 2:
            # 2-letter tokens never fuzzy matched
            return None

        # RapidFuzz branch match
        search_space = [k for k in self.branch_aliases.keys() if len(k) > 2]
        match = process.extractOne(clean, search_space, scorer=fuzz.ratio)
        if match:
            matched_alias, score, _ = match
            bcode = self.branch_aliases[matched_alias]
            bdata = self.branches.get(bcode, {})

            if score >= 90.0:
                return {
                    "branch_code": bcode,
                    "short_name": bdata.get("short_name", bcode),
                    "canonical_name": bdata.get("canonical_name", bcode),
                    "status": "ACCEPTED",
                    "score": round(score, 1),
                    "match_type": "rapidfuzz_high_confidence",
                    "matched_alias": matched_alias
                }
            elif score >= 70.0:
                return {
                    "branch_code": bcode,
                    "short_name": bdata.get("short_name", bcode),
                    "canonical_name": bdata.get("canonical_name", bcode),
                    "status": "SUGGESTION",
                    "score": round(score, 1),
                    "match_type": "rapidfuzz_suggestion",
                    "matched_alias": matched_alias,
                    "suggestion": f"Did you mean {bdata.get('canonical_name', bcode)}?"
                }

        return None

    def derive_batches(self, text: str) -> List[str]:
        """
        Derive all academic cohorts mentioned in text from:
        1. Roll-number prefixes (e.g., '20102001' -> '2020-2024')
        2. Standard batch string formats ('2020-2024', '2020-24', '2024')
        """
        found_batches = []
        # 1. Roll-number prefix derivation
        roll_matches = re.findall(r'\b(20|21|22|23|24)\d{5,6}\b', text)
        for prefix in roll_matches:
            if prefix in self.ROLL_PREFIX_BATCH_MAP:
                b = self.ROLL_PREFIX_BATCH_MAP[prefix]
                if b not in found_batches:
                    found_batches.append(b)

        # 2. Standard 4-digit hyphen range (e.g. 2020-2024)
        for m in re.finditer(r'\b(20\d{2}-20\d{2})\b', text):
            val = m.group(1)
            if val in self.batches and val not in found_batches:
                found_batches.append(val)

        # 3. Short hyphen format (e.g. 2020-24)
        for m in re.finditer(r'\b(20\d{2})-(\d{2})\b', text):
            full = f"{m.group(1)}-20{m.group(2)}"
            if full in self.batches and full not in found_batches:
                found_batches.append(full)

        # 4. Standalone graduation year (e.g. 2024, 2025)
        if not found_batches:
            for m in re.finditer(r'\b(202[4-7])\b', text):
                passout = int(m.group(1))
                admission = passout - 4
                batch_candidate = f"{admission}-{passout}"
                if batch_candidate in self.batches and batch_candidate not in found_batches:
                    found_batches.append(batch_candidate)

        return found_batches

    def derive_batch(self, text: str) -> Optional[str]:
        """Derive single primary batch."""
        res = self.derive_batches(text)
        return res[0] if res else None

    def link_entities_in_query(self, question: str) -> Dict[str, Any]:
        """
        Extract and link all entities (companies, branches, batches) in user question.
        Returns accepted entities, suggestions, and ambiguous flags.
        """
        q = question.strip()
        low = " " + q.lower() + " "

        accepted_companies = []
        suggested_companies = []
        accepted_branches = []
        suggested_branches = []
        batches = self.derive_batches(q)

        # 2. Check 2-letter acronym whitelist first with word boundaries
        for short_alias, canon in self.TWO_LETTER_WHITELIST.items():
            if re.search(r'\b' + re.escape(short_alias) + r'\b', low):
                res = self.link_company(short_alias)
                if res and res["canonical_name"] not in [x["canonical_name"] for x in accepted_companies]:
                    accepted_companies.append(res)

        # 3. Branch code check with word boundaries
        for bcode, binfo in self.branches.items():
            sname = binfo["short_name"].lower()
            # Protect "me" from conversational "tell me" while detecting ME branch (e.g., 'and ME?', 'for ME', 'in ME')
            if sname == "me":
                is_me_branch = (
                    bool(re.search(r'\bME\b', q)) or
                    bool(re.search(r'\b(in me|and me|for me|about me|me\?|me department|me dept|me engineering|me branch)\b', low))
                ) and not bool(re.search(r'\b(tell me|give me|show me|help me|ask me|let me)\b', low))
                if is_me_branch:
                    res = self.link_branch("me", allow_me=True)
                    if res and res["branch_code"] not in [x["branch_code"] for x in accepted_branches]:
                        accepted_branches.append(res)
            else:
                if re.search(r'\b' + re.escape(sname) + r'\b', low):
                    res = self.link_branch(sname)
                    if res and res["branch_code"] not in [x["branch_code"] for x in accepted_branches]:
                        accepted_branches.append(res)

        # 4. Extract word n-grams and tokens for company and branch linking
        words = re.findall(r'[A-Za-z0-9&]+', q)
        # Check 1-gram to 5-gram candidate phrases (longer first to prefer exact multi-word entities)
        stopwords = {"in", "at", "for", "from", "by", "to", "of", "with", "and", "or", "the", "a", "an", "is", "was", "are", "were"}
        candidates = []
        for n in [5, 4, 3, 2, 1]:
            for i in range(len(words) - n + 1):
                chunk = words[i:i+n]
                while chunk and chunk[0].lower() in stopwords and " ".join(chunk).lower() not in self.company_aliases:
                    chunk = chunk[1:]
                while chunk and chunk[-1].lower() in stopwords and " ".join(chunk).lower() not in self.company_aliases:
                    chunk = chunk[:-1]
                if chunk:
                    phrase = " ".join(chunk)
                    if phrase not in candidates:
                        candidates.append(phrase)

        for cand in candidates:
            cand_clean = cand.lower().strip()
            cand_words = cand_clean.split()
            # If candidate is an exact alias in branch or company aliases, NEVER skip it!
            is_exact_alias = (cand_clean in self.branch_aliases) or (cand_clean in self.company_aliases)
            if not is_exact_alias:
                if all(w in self.DISALLOWED_WORDS for w in cand_words) or len(cand_clean) <= 2:
                    continue

            # Skip candidate for company matching if it is a breakdown or grouping indicator
            is_grouping = (
                cand_clean.endswith("wise") or cand_clean.endswith("-wise")
                or any(w in ["wise", "breakdown", "distribution"] for w in cand_words)
            )

            # Link company if no accepted company exists or searching for multi-company comparisons
            if not is_grouping:
                c_link = self.link_company(cand)
                if c_link:
                    if c_link["status"] == "ACCEPTED":
                        if c_link["canonical_name"] not in [x["canonical_name"] for x in accepted_companies]:
                            accepted_companies.append(c_link)
                    elif c_link["status"] == "SUGGESTION" and not accepted_companies:
                        if c_link["canonical_name"] not in [x["canonical_name"] for x in suggested_companies]:
                            suggested_companies.append(c_link)

            # Link branch
            b_link = self.link_branch(cand)
            if b_link:
                # If an accepted branch is already found whose canonical name or alias contains cand, don't add spurious submatches
                already_covered = any(
                    cand_clean in x.get("canonical_name", "").lower()
                    for x in accepted_branches
                )
                if not already_covered:
                    if b_link["status"] == "ACCEPTED":
                        if b_link["branch_code"] not in [x["branch_code"] for x in accepted_branches]:
                            accepted_branches.append(b_link)
                    elif b_link["status"] == "SUGGESTION" and not accepted_branches:
                        if b_link["branch_code"] not in [x["branch_code"] for x in suggested_branches]:
                            suggested_branches.append(b_link)

        if accepted_companies:
            # Drop shorter subsumed company names (e.g. 'Reliance' if 'Reliance Industries' is present)
            deduped_companies = []
            all_cnames = [c["canonical_name"] for c in accepted_companies]
            for c in accepted_companies:
                cname = c["canonical_name"]
                if any(other != cname and cname.lower() in other.lower() for other in all_cnames):
                    continue
                if cname not in [x["canonical_name"] for x in deduped_companies]:
                    deduped_companies.append(c)
            accepted_companies = deduped_companies
            suggested_companies = []
        if accepted_branches:
            suggested_branches = []

        return {
            "companies": accepted_companies,
            "branches": accepted_branches,
            "batches": batches,
            "suggestions": {
                "companies": suggested_companies,
                "branches": suggested_branches
            }
        }
