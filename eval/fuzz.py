"""
Fuzz Testing Suite for NITJ Placement Assistant.
Auto-generates robust variants of every test question across 6 perturbation strategies:
1. Typos: Swapped, dropped, and duplicated letters in key words.
2. Abbreviations: Tech company (MS, MSFT, GS, AMZN, GOOG, TI) and branch acronyms.
3. Casing: ALL-CAPS, lowercase, and random mixed casing.
4. Hinglish filler: Colloquial prefixes/suffixes ('bhai', 'yaar', 'ka package kya tha', 'kitne place hue').
5. Missing words: Telegraphic/keyword-only search style ('ctc microsoft cse', 'amazon it placed count').
6. Follow-up style: Conversational follow-up phrasing ('and for IT?', 'what about ECE?', 'same for Google').

Reports accuracy on standard, fuzzed, and held-out test sets separately.
Strict constraint: Never tune prompts/rules on heldout questions.
"""

import json
import os
import sys
import re
import random
from typing import Dict, List, Any, Tuple
from collections import defaultdict

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("."))

from src.nlp.query_planner import QueryPlanner

QUESTIONS_FILE = "eval/questions.json"
FUZZED_QUESTIONS_FILE = "eval/fuzzed_questions.json"
HELDOUT_QUESTIONS_FILE = "eval/heldout.json"
FUZZ_REPORT_OUTPUT = "eval/fuzz_eval_report.md"

# Random seed for deterministic fuzz generation
random.seed(42)

# Abbreviation replacement dictionaries
COMPANY_ABBREVS = {
    r"\bMicrosoft\b": ["MS", "MSFT", "Micro soft"],
    r"\bAmazon\b": ["AMZN", "Amazon India"],
    r"\bGoogle\b": ["GOOG", "GOOGL"],
    r"\bGoldman Sachs\b": ["GS", "Goldman"],
    r"\bTexas Instruments\b": ["TI"],
    r"\bInfosys\b": ["Infy", "Infosys Technologies"],
    r"\bTata Consultancy Services\b": ["TCS"],
    r"\bReliance Industries\b": ["RIL", "Reliance"],
}

BRANCH_ABBREVS = {
    r"\bComputer Science and Engineering\b": "CSE",
    r"\bComputer Science\b": "CSE",
    r"\bInformation Technology\b": "IT",
    r"\bElectronics and Communication Engineering\b": "ECE",
    r"\bElectronics\b": "ECE",
    r"\bMechanical Engineering\b": "ME",
    r"\bElectrical Engineering\b": "EE",
    r"\bChemical Engineering\b": "CHE",
    r"\bCivil Engineering\b": "CE",
    r"\bInstrumentation and Control Engineering\b": "ICE",
    r"\bIndustrial and Production Engineering\b": "IPE",
    r"\bBiotechnology\b": "BT",
    r"\bTextile Technology\b": "TT",
}

STOPWORDS = {
    "what", "is", "the", "of", "for", "how", "many", "students", "were", 
    "was", "got", "did", "given", "to", "in", "a", "an", "are", "from",
    "by", "which", "with", "at", "and"
}

def swap_letters(word: str) -> str:
    """Swap two adjacent letters in a word with length >= 4."""
    if len(word) < 4:
        return word
    idx = random.randint(1, len(word) - 2)
    chars = list(word)
    chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
    return "".join(chars)

def drop_letter(word: str) -> str:
    """Drop a non-initial letter from a word with length >= 5."""
    if len(word) < 5:
        return word
    idx = random.randint(1, len(word) - 2)
    return word[:idx] + word[idx + 1:]

def duplicate_letter(word: str) -> str:
    """Duplicate a letter in a word."""
    if len(word) < 4:
        return word
    idx = random.randint(1, len(word) - 2)
    return word[:idx] + word[idx] + word[idx:]

class FuzzGenerator:
    """Generates 6 distinct categories of perturbations for every question."""

    @staticmethod
    def generate_typo(q: str) -> Tuple[str, str]:
        """Apply spelling typos to key entities or nouns."""
        words = q.split()
        target_indices = [
            i for i, w in enumerate(words) 
            if len(re.sub(r'\W', '', w)) >= 5 and re.sub(r'\W', '', w).lower() not in {"which", "where", "about"}
        ]
        if not target_indices:
            return q, "none"
        
        chosen_idx = random.choice(target_indices)
        orig_word = words[chosen_idx]
        clean_word = re.sub(r'\W', '', orig_word)
        trailing = orig_word[len(clean_word):]

        mutation_choice = random.choice(["swap", "drop", "dup"])
        if mutation_choice == "swap":
            mutated = swap_letters(clean_word) + trailing
            rule = f"Swapped adjacent letters in '{clean_word}'"
        elif mutation_choice == "drop":
            mutated = drop_letter(clean_word) + trailing
            rule = f"Dropped letter in '{clean_word}'"
        else:
            mutated = duplicate_letter(clean_word) + trailing
            rule = f"Duplicated letter in '{clean_word}'"

        words[chosen_idx] = mutated
        return " ".join(words), rule

    @staticmethod
    def generate_abbrev(q: str) -> Tuple[str, str]:
        """Replace companies and branches with their standard short abbreviations."""
        modified = q
        applied = []
        for pattern, abbrevs in COMPANY_ABBREVS.items():
            if re.search(pattern, modified, re.IGNORECASE):
                replacement = random.choice(abbrevs)
                modified = re.sub(pattern, replacement, modified, flags=re.IGNORECASE)
                applied.append(f"Company -> {replacement}")
                break

        for pattern, abbrev in BRANCH_ABBREVS.items():
            if re.search(pattern, modified, re.IGNORECASE):
                modified = re.sub(pattern, abbrev, modified, flags=re.IGNORECASE)
                applied.append(f"Branch -> {abbrev}")
                break

        if not applied:
            # If no company/branch found, check for batch abbreviation e.g. 2020-2024 -> 2020-24
            m_batch = re.search(r'\b(20\d{2})-20(\d{2})\b', modified)
            if m_batch:
                modified = re.sub(r'\b(20\d{2})-20(\d{2})\b', r'\1-\2', modified)
                applied.append("Batch -> YY-YY")

        rule = ", ".join(applied) if applied else "No abbreviation target found"
        return modified, rule

    @staticmethod
    def generate_casing(q: str) -> Tuple[str, str]:
        """Apply casing perturbations (ALL-CAPS, lowercase, or mixed)."""
        mode = random.choice(["upper", "lower", "title"])
        if mode == "upper":
            return q.upper(), "ALL-CAPS"
        elif mode == "lower":
            return q.lower(), "all-lowercase"
        else:
            return q.title(), "Title-Case"

    @staticmethod
    def generate_hinglish(q: str) -> Tuple[str, str]:
        """Wrap or inject Indian college campus Hinglish phrasing."""
        low = q.lower()
        # Prefix/suffix fillers
        prefixes = ["bhai ", "yaar ", "arre sun na ", "sun bhai "]
        suffixes = [" yaar", " bhai", " batao na", " please", " tell me fast"]

        # Check for count questions
        if "how many" in low or "count" in low:
            res = re.sub(r'\bhow many students\b', 'kitne students', q, flags=re.IGNORECASE)
            res = re.sub(r'\bhow many\b', 'kitne log', res, flags=re.IGNORECASE)
            res = re.sub(r'\bgot placed\b', 'place hue', res, flags=re.IGNORECASE)
            return f"{random.choice(prefixes)}{res}{random.choice(suffixes)}", "Hinglish count syntax"

        # Check for CTC / package questions
        if "ctc" in low or "package" in low:
            res = re.sub(r'\bwhat is the ctc of\b', 'ctc kitna hai', q, flags=re.IGNORECASE)
            res = re.sub(r'\bwhat package did\b', 'package kya tha', res, flags=re.IGNORECASE)
            return f"{random.choice(prefixes)}{res}{random.choice(suffixes)}", "Hinglish compensation syntax"

        # General Hinglish wrapper
        return f"{random.choice(prefixes)}{q}{random.choice(suffixes)}", "Colloquial Hinglish wrapper"

    @staticmethod
    def generate_missing_words(q: str) -> Tuple[str, str]:
        """Strip filler words to create telegraphic / keyword search queries."""
        clean = re.sub(r'[\?\.,!]', '', q)
        tokens = clean.split()
        keywords = [w for w in tokens if w.lower() not in STOPWORDS]
        if len(keywords) < 2:
            return q, "none"
        return " ".join(keywords), f"Dropped {len(tokens) - len(keywords)} stop words (Telegraphic)"

    @staticmethod
    def generate_followup(q: str) -> Tuple[str, str]:
        """Convert into a conversational follow-up query."""
        low = q.lower()
        if "cse" in low:
            return re.sub(r'\bcse\b', 'and what about IT?', q, flags=re.IGNORECASE), "Follow-up substitution (IT)"
        if "microsoft" in low:
            return re.sub(r'\bmicrosoft\b', 'same question for Amazon', q, flags=re.IGNORECASE), "Follow-up substitution (Amazon)"
        if "2020-2024" in low:
            return re.sub(r'\b2020-2024\b', 'and in 2021-2025 batch?', q), "Follow-up cohort substitution"
        
        # General conversational follow-up prefix
        return f"And {q.lower()}", "Conversational follow-up prefix"


def build_fuzzed_dataset(output_path: str = FUZZED_QUESTIONS_FILE) -> List[Dict[str, Any]]:
    """Build comprehensive fuzzed question suite across all 6 strategies."""
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        base_questions = json.load(f)

    fuzzed_suite = []

    for item in base_questions:
        q_id = item["id"]
        base_text = item["question"]
        gold_ans = item.get("gold_answer")
        ans_type = item.get("answer_type", "scalar")
        type_name = item.get("type_name", "Lookup")
        sql = item.get("sql")

        # 1. Typo variant
        typo_text, typo_rule = FuzzGenerator.generate_typo(base_text)
        if typo_text != base_text:
            fuzzed_suite.append({
                "id": f"{q_id}_TYPO",
                "original_id": q_id,
                "type_name": type_name,
                "fuzz_strategy": "typos",
                "fuzz_rule": typo_rule,
                "question": typo_text,
                "answer_type": ans_type,
                "gold_answer": gold_ans,
                "sql": sql
            })

        # 2. Abbreviation variant
        abbrev_text, abbrev_rule = FuzzGenerator.generate_abbrev(base_text)
        if abbrev_text != base_text and abbrev_rule != "No abbreviation target found":
            fuzzed_suite.append({
                "id": f"{q_id}_ABBREV",
                "original_id": q_id,
                "type_name": type_name,
                "fuzz_strategy": "abbreviations",
                "fuzz_rule": abbrev_rule,
                "question": abbrev_text,
                "answer_type": ans_type,
                "gold_answer": gold_ans,
                "sql": sql
            })

        # 3. Casing variant
        casing_text, casing_rule = FuzzGenerator.generate_casing(base_text)
        fuzzed_suite.append({
            "id": f"{q_id}_CASING",
            "original_id": q_id,
            "type_name": type_name,
            "fuzz_strategy": "casing",
            "fuzz_rule": casing_rule,
            "question": casing_text,
            "answer_type": ans_type,
            "gold_answer": gold_ans,
            "sql": sql
        })

        # 4. Hinglish variant
        hinglish_text, hinglish_rule = FuzzGenerator.generate_hinglish(base_text)
        fuzzed_suite.append({
            "id": f"{q_id}_HINGLISH",
            "original_id": q_id,
            "type_name": type_name,
            "fuzz_strategy": "hinglish",
            "fuzz_rule": hinglish_rule,
            "question": hinglish_text,
            "answer_type": ans_type,
            "gold_answer": gold_ans,
            "sql": sql
        })

        # 5. Missing words (Telegraphic) variant
        kw_text, kw_rule = FuzzGenerator.generate_missing_words(base_text)
        if kw_text != base_text and kw_rule != "none":
            fuzzed_suite.append({
                "id": f"{q_id}_KEYWORD",
                "original_id": q_id,
                "type_name": type_name,
                "fuzz_strategy": "missing_words",
                "fuzz_rule": kw_rule,
                "question": kw_text,
                "answer_type": ans_type,
                "gold_answer": gold_ans,
                "sql": sql
            })

        # 6. Follow-up style variant (only for subset where semantics remain identical)
        if any(w in base_text.lower() for w in ["what is the", "how many", "which"]):
            follow_text, follow_rule = FuzzGenerator.generate_followup(base_text)
            if follow_rule.startswith("Conversational follow-up"):
                fuzzed_suite.append({
                    "id": f"{q_id}_FOLLOWUP",
                    "original_id": q_id,
                    "type_name": type_name,
                    "fuzz_strategy": "followup",
                    "fuzz_rule": follow_rule,
                    "question": follow_text,
                    "answer_type": ans_type,
                    "gold_answer": gold_ans,
                    "sql": sql
                })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(fuzzed_suite, f, indent=2)

    print(f"Generated {len(fuzzed_suite)} fuzzed test questions saved to {output_path}")
    return fuzzed_suite


def normalize_val(val: Any) -> Any:
    """Normalize numeric, list, or string values for comparison."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    if isinstance(val, str):
        try:
            return round(float(val), 2)
        except ValueError:
            return val.strip().lower()
    if isinstance(val, list):
        return [normalize_val(x) for x in val]
    return val

def compare_results(candidate: Any, gold: Any, answer_type: str) -> bool:
    """Compare candidate query output against gold answer."""
    if gold in ["NO_DATA", "OUT_OF_SCOPE", "CLARIFICATION_REQUIRED", "PRIVACY_BLOCKED", "UNANSWERABLE"]:
        if isinstance(candidate, str):
            return candidate.upper() == gold
        return False

    if candidate is None and gold is None:
        return True
    if candidate is None or gold is None:
        return False

    if answer_type == "scalar":
        cand_norm = normalize_val(candidate)
        gold_norm = normalize_val(gold)
        if isinstance(cand_norm, (int, float)) and isinstance(gold_norm, (int, float)):
            return abs(cand_norm - gold_norm) < 0.05
        return cand_norm == gold_norm

    elif answer_type in ["number_list", "list"]:
        if not isinstance(candidate, (list, tuple)) or not isinstance(gold, (list, tuple)):
            return False
        cand_norm = sorted([normalize_val(x) for x in candidate])
        gold_norm = sorted([normalize_val(x) for x in gold])
        return cand_norm == gold_norm

    elif answer_type in ["table", "hybrid"]:
        if not isinstance(candidate, (list, tuple)) or not isinstance(gold, (list, tuple)):
            return False
        if len(candidate) != len(gold):
            return False
        cand_norm = [tuple(normalize_val(x) for x in row) if isinstance(row, (list, tuple)) else (normalize_val(row),) for row in candidate]
        gold_norm = [tuple(normalize_val(x) for x in row) if isinstance(row, (list, tuple)) else (normalize_val(row),) for row in gold]
        return sorted(cand_norm) == sorted(gold_norm)

    return candidate == gold


def evaluate_fuzzed_suite(fuzzed_path: str = FUZZED_QUESTIONS_FILE) -> Dict[str, Any]:
    """Run full evaluation on the fuzzed test suite and break down results by strategy."""
    if not os.path.exists(fuzzed_path):
        print(f"Fuzzed questions file {fuzzed_path} not found. Generating now...")
        build_fuzzed_dataset(fuzzed_path)

    with open(fuzzed_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    planner = QueryPlanner()

    total = len(questions)
    passed = 0
    strategy_stats = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
    type_stats = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
    failures = []

    print(f"\n=======================================================")
    print(f"RUNNING EVALUATION ON FUZZED TEST SUITE ({total} QUESTIONS)")
    print(f"=======================================================\n")

    for idx, q in enumerate(questions, 1):
        q_id = q["id"]
        q_text = q["question"]
        strategy = q.get("fuzz_strategy", "general")
        q_type = q.get("type_name", "General")
        gold_ans = q.get("gold_answer")
        ans_type = q.get("answer_type", "scalar")

        strategy_stats[strategy]["total"] += 1
        type_stats[q_type]["total"] += 1

        cand_result = None
        cand_sql = None
        error_msg = None

        try:
            res = planner.plan_and_execute(q_text)
            cand_sql = res.get("sql")
            if res.get("category") in ["out_of_scope", "ambiguous"]:
                cand_result = res.get("intent")
            else:
                exec_res = res.get("exec_result", {})
                rows = exec_res.get("rows", [])
                if ans_type == "scalar":
                    cand_result = rows[0][0] if rows and rows[0] else None
                elif ans_type in ["number_list", "list"]:
                    cand_result = [r[0] for r in rows]
                elif ans_type in ["table", "hybrid"]:
                    cand_result = [list(r) for r in rows]
                else:
                    cand_result = res.get("raw_result")
        except Exception as e:
            error_msg = str(e)

        is_pass = False
        if error_msg is None:
            is_pass = compare_results(cand_result, gold_ans, ans_type)

        if is_pass:
            passed += 1
            strategy_stats[strategy]["passed"] += 1
            type_stats[q_type]["passed"] += 1
        else:
            strategy_stats[strategy]["failed"] += 1
            type_stats[q_type]["failed"] += 1
            failures.append({
                "id": q_id,
                "strategy": strategy,
                "type": q_type,
                "question": q_text,
                "rule": q.get("fuzz_rule"),
                "gold": gold_ans,
                "candidate": cand_result,
                "sql": cand_sql,
                "error": error_msg
            })

    accuracy = (passed / total) * 100.0 if total > 0 else 0.0

    # Save failures for detailed inspection and tracking
    with open("eval/fuzz_failures.json", "w", encoding="utf-8") as f:
        json.dump(failures, f, indent=2)

    print(f"{'Fuzz Strategy':<25} | {'Total':<6} | {'Passed':<6} | {'Failed':<6} | {'Accuracy':<8}")
    print("-" * 60)
    for strat, st in sorted(strategy_stats.items()):
        acc = (st["passed"] / st["total"]) * 100.0 if st["total"] > 0 else 0.0
        print(f"{strat:<25} | {st['total']:<6} | {st['passed']:<6} | {st['failed']:<6} | {acc:>6.1f}%")
    print("-" * 60)
    print(f"{'OVERALL FUZZ ACCURACY':<25} | {total:<6} | {passed:<6} | {total - passed:<6} | {accuracy:>6.1f}%\n")

    return {
        "total": total,
        "passed": passed,
        "accuracy": accuracy,
        "strategy_stats": dict(strategy_stats),
        "type_stats": dict(type_stats),
        "failures": failures
    }


def evaluate_heldout_suite(heldout_path: str = HELDOUT_QUESTIONS_FILE) -> Dict[str, Any]:
    """
    Run evaluation on the held-out test suite.
    STRICT CONSTRAINT: Never tune prompts/rules on heldout questions.
    """
    if not os.path.exists(heldout_path):
        print(f"Heldout questions file {heldout_path} not found.")
        return {"total": 0, "status": "FILE_NOT_FOUND"}

    with open(heldout_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    if not questions:
        print(f"\n=======================================================")
        print(f"HELDOUT TEST SET EVALUATION: (0 Questions - Empty)")
        print(f"=======================================================")
        print(f"File {heldout_path} is currently empty. Populate it with your test cases to run.")
        print(f"Strict rule enforced: System prompts and rules are never tuned on heldout questions.\n")
        return {"total": 0, "passed": 0, "accuracy": 0.0, "status": "EMPTY"}

    planner = QueryPlanner()
    total = len(questions)
    passed = 0
    failures = []

    print(f"\n=======================================================")
    print(f"RUNNING EVALUATION ON HELDOUT TEST SUITE ({total} QUESTIONS)")
    print(f"=======================================================\n")

    for q in questions:
        q_id = q.get("id", "HELDOUT")
        q_text = q.get("question", "")
        gold_ans = q.get("gold_answer")
        ans_type = q.get("answer_type", "scalar")

        cand_result = None
        error_msg = None

        try:
            res = planner.plan_and_execute(q_text)
            if res.get("category") in ["out_of_scope", "ambiguous"]:
                cand_result = res.get("intent")
            else:
                exec_res = res.get("exec_result", {})
                rows = exec_res.get("rows", [])
                if ans_type == "scalar":
                    cand_result = rows[0][0] if rows and rows[0] else None
                elif ans_type in ["number_list", "list"]:
                    cand_result = [r[0] for r in rows]
                elif ans_type in ["table", "hybrid"]:
                    cand_result = [list(r) for r in rows]
                else:
                    cand_result = res.get("raw_result")
        except Exception as e:
            error_msg = str(e)

        is_pass = False
        if error_msg is None:
            is_pass = compare_results(cand_result, gold_ans, ans_type)

        if is_pass:
            passed += 1
        else:
            failures.append({
                "id": q_id,
                "question": q_text,
                "gold": gold_ans,
                "candidate": cand_result,
                "error": error_msg
            })

    accuracy = (passed / total) * 100.0 if total > 0 else 0.0

    print(f"Heldout Total: {total} | Passed: {passed} | Failed: {total - passed} | Accuracy: {accuracy:.1f}%\n")

    return {
        "total": total,
        "passed": passed,
        "accuracy": accuracy,
        "failures": failures
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NITJ Placement Assistant Fuzz & Heldout Suite")
    parser.add_argument("--generate", action="store_true", help="Generate fuzzed dataset")
    parser.add_argument("--eval", action="store_true", help="Run evaluation on fuzzed dataset")
    parser.add_argument("--heldout", action="store_true", help="Run evaluation on heldout dataset")
    parser.add_argument("--all", action="store_true", help="Run both fuzzed and heldout evaluations")

    args = parser.parse_args()

    if args.generate or not os.path.exists(FUZZED_QUESTIONS_FILE):
        build_fuzzed_dataset()

    if args.heldout:
        evaluate_heldout_suite()
    elif args.eval:
        evaluate_fuzzed_suite()
    elif args.all:
        evaluate_fuzzed_suite()
        evaluate_heldout_suite()
    else:
        # Default behavior: run fuzz evaluation and report heldout status
        evaluate_fuzzed_suite()
        evaluate_heldout_suite()

