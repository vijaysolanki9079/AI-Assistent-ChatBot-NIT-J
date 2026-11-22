"""
LLM and Semantic Contextualizer for Multi-Turn Dialogs.
Transforms follow-up questions and conversational turns into fully self-contained standalone questions
using structured slot carry-over and LLM schema output.
"""

import os
import re
import json
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field

from src.nlp.fuzzy_linker import FuzzyEntityLinker


class ContextualizedOutput(BaseModel):
    standalone_question: str
    is_followup: bool
    carried_slots: Dict[str, Any] = Field(default_factory=dict)
    resolved_clarification: bool = False


class QueryContextualizer:
    """
    Contextualizes multi-turn conversations:
    1. Uses local Ollama with JSON-schema constraint when available.
    2. Fallbacks to deterministic semantic slot carry-over engine without regex hacks.
    """

    BRANCH_DISPLAY = {
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

    def __init__(self, db_path: str = "data/nitj_placement.db"):
        self.linker = FuzzyEntityLinker(db_path)
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "6"))

    def contextualize(
        self,
        new_message: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        session_state: Optional[Dict[str, Any]] = None
    ) -> ContextualizedOutput:
        """
        Produce a self-contained standalone question and carried slots.
        Cap history sent to the LLM at the last 6 turns.
        """
        trimmed_history = (chat_history or [])[-6:]
        state = session_state or {}

        # 1. Try Ollama LLM with JSON Schema
        llm_output = self._call_ollama_contextualizer(new_message, trimmed_history, state)
        if llm_output:
            return llm_output

        # 2. Deterministic Semantic Contextualizer Engine
        return self._semantic_contextualize(new_message, trimmed_history, state)

    def _call_ollama_contextualizer(
        self,
        new_message: str,
        history: List[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> Optional[ContextualizedOutput]:
        """Call Ollama /api/generate with schema constraint."""
        try:
            schema = {
                "type": "object",
                "properties": {
                    "standalone_question": {"type": "string"},
                    "is_followup": {"type": "boolean"},
                    "carried_slots": {
                        "type": "object",
                        "properties": {
                            "company": {"type": ["string", "null"]},
                            "branch": {"type": ["string", "null"]},
                            "batch": {"type": ["string", "null"]},
                            "offer_type": {"type": ["string", "null"]},
                            "metric": {"type": ["string", "null"]}
                        }
                    },
                    "resolved_clarification": {"type": "boolean"}
                },
                "required": ["standalone_question", "is_followup", "carried_slots", "resolved_clarification"]
            }

            hist_text = "\n".join([f"{h.get('role', 'user')}: {h.get('content', '')}" for h in history])
            prompt = (
                "You are an expert conversational dialog manager for university placement data.\n"
                f"Conversation History (last 6 turns):\n{hist_text}\n\n"
                f"Pending Clarification: {state.get('pending_clarification')}\n"
                f"Last Query Spec: {json.dumps(state.get('last_query_spec') or {})}\n\n"
                f"User's New Message: \"{new_message}\"\n\n"
                "Task: Rewrite the user's new message into a self-contained standalone question. "
                "Resolve any pronouns (them, those, their, that company) to their antecedent entities from history. "
                "If the message is a follow-up specifying a branch, batch, or company, carry over all unchanged slots. "
                "Output strictly adhering to the JSON schema."
            )

            url = f"{self.ollama_host}/api/generate"
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": schema,
                "options": {"temperature": 0.0}
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.ollama_timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                res_obj = json.loads(body.get("response", ""))
                return ContextualizedOutput(
                    standalone_question=res_obj.get("standalone_question", new_message),
                    is_followup=bool(res_obj.get("is_followup", False)),
                    carried_slots=res_obj.get("carried_slots", {}),
                    resolved_clarification=bool(res_obj.get("resolved_clarification", False))
                )
        except Exception:
            return None

    def _semantic_contextualize(
        self,
        new_message: str,
        history: List[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> ContextualizedOutput:
        """
        Deterministic slot carry-over and standalone question generator.
        Implements all slot carry-over rules:
        - pending_clarification handling first
        - single slot updates previous QuerySpec
        - new company resets company-specific slots
        - pronoun resolution ("those", "them", "their", "that company")
        """
        msg_clean = new_message.strip()
        low = msg_clean.lower()
        last_spec = state.get("last_query_spec") or {}
        pending_clarification = state.get("pending_clarification")

        # Extract entities in new message
        linked = self.linker.link_entities_in_query(new_message)
        new_companies = [c["canonical_name"] for c in linked.get("companies", [])]
        new_branches = [b["short_name"] for b in linked.get("branches", [])]
        new_batches = list(linked.get("batches", []))

        # Check pronoun references
        has_pronoun = any(
            p in low for p in [
                "they", "did they", "they ask", "those", "them", "their", "that company", "the company", "these students", "these",
                "of them", "about them", "for them", "who got placed", "names of those"
            ]
        )

        # -------------------------------------------------------------
        # Rule 1: Pending Clarification Handling
        # -------------------------------------------------------------
        if pending_clarification and last_spec:
            # Check if user answered a branch clarification
            if new_branches or any(b in low for b in ["cse", "it", "ece", "me", "ee", "che", "ce", "ice", "ipe", "bt", "tt"]):
                target_b = new_branches[0] if new_branches else low.upper()
                carried = dict(last_spec)
                carried["branches"] = [target_b]
                comp_str = f" at {carried['companies'][0]}" if carried.get("companies") else ""
                batch_str = f" for {carried['batches'][0]}" if carried.get("batches") else ""
                metric = carried.get("metric", "placement")
                standalone = f"What is the {metric} in {target_b}{comp_str}{batch_str}?"
                return ContextualizedOutput(
                    standalone_question=standalone,
                    is_followup=True,
                    carried_slots=carried,
                    resolved_clarification=True
                )

        # Check affirmation / standalone 'all' follow-up even if pending_clarification wasn't explicitly flagged
        if last_spec:
            comp_str = f" for {last_spec['companies'][0]}" if last_spec.get("companies") else ""
            branch_str = f" in {last_spec['branches'][0]}" if last_spec.get("branches") else ""

            if any(low == w for w in ["yes", "yeah", "yep", "sure", "correct", "right", "ok", "okay"]):
                carried = dict(last_spec)
                standalone = f"Placement details{comp_str}{branch_str}"
                return ContextualizedOutput(
                    standalone_question=standalone,
                    is_followup=True,
                    carried_slots=carried,
                    resolved_clarification=True
                )

            if any(low == w for w in ["all", "all batches", "all cohorts", "both", "every batch"]):
                carried = dict(last_spec)
                carried["batches"] = []
                standalone = f"placements{comp_str}{branch_str} across all batches"
                return ContextualizedOutput(
                    standalone_question=standalone,
                    is_followup=True,
                    carried_slots=carried,
                    resolved_clarification=True
                )

        # -------------------------------------------------------------
        # Rule 2: Follow-up checks when last_query_spec exists
        # -------------------------------------------------------------
        if last_spec:
            prev_companies = last_spec.get("companies", [])
            prev_branches = last_spec.get("branches", [])
            prev_batches = last_spec.get("batches", [])
            prev_metric = last_spec.get("metric", "placed_students")
            prev_offer_types = last_spec.get("offer_types", [])

            # Check explicit continuation indicators
            starts_continuation = any(
                low.startswith(p) for p in [
                    "and ", "and for ", "what about ", "how about ", "also for ",
                    "also in ", "also ", "same for ", "what of "
                ]
            )

            # Anaphoric pronouns referring to previous turn's entities
            pronoun_patterns = [
                r"\bthey\b", r"\bdid they\b", r"\bthose\b", r"\bthem\b", r"\btheir\b",
                r"\bthat company\b", r"\bthe company\b", r"\bthese students\b",
                r"\bthose students\b", r"\bof them\b", r"\babout them\b", r"\bfor them\b",
                r"\bwho got placed\b"
            ]
            has_pronoun = any(re.search(p, low) for p in pronoun_patterns)

            # Explicit list / names continuation
            is_list_continuation = any(
                p in low for p in [
                    "give their names", "show their names", "who are they", "list them",
                    "show more", "names of those", "who got placed", "name of students",
                    "names of students", "show names", "give names", "their names"
                ]
            )

            # Check if this is a complete standalone question with its own subject/verb
            is_full_question = any(
                low.startswith(p) for p in [
                    "what is ", "what are ", "what was ", "what were ", "what did ", "what does ", "what do ",
                    "which ", "who ", "how many ", "how much ", "tell me ", "show me ", "give me ", "list ", "can you "
                ]
            )

            # Dimension / group-by continuation (e.g. "branch wise", "batch wise")
            is_dim_followup = any(k in low for k in ["branch wise", "branch-wise", "batch wise", "batch-wise", "company wise", "group by", "breakdown", "distribution"])

            # Metric-only follow-up (e.g. "total offers count", "average package", "highest ctc")
            words = msg_clean.split()
            clean_words = [w.rstrip("?.,") for w in low.split()]
            is_metric_followup = (
                all(w in ["total", "offers", "offer", "count", "placed", "student", "students", "average", "avg", "mean", "package", "packages", "ctc", "salary", "salaries", "highest", "max", "peak", "lowest", "min", "median", "stipend", "intern", "internship", "percentage", "rate"] for w in clean_words)
                or (len(words) <= 3 and any(k in low for k in ["total offers", "average package", "highest package", "lowest package", "placed students", "median package"]))
            )

            # Ultra-short single slot follow-up (e.g. "IT", "in CSE", "2021-25", "for 2022-26", "branch wise", "what stipend?")
            is_ultra_short = (
                len(words) <= 2
                or (len(words) <= 3 and low.startswith(("in ", "for ", "only ", "what ")))
            ) and (
                bool(new_branches)
                or (bool(new_companies) and starts_continuation)
                or bool(new_batches)
                or is_dim_followup
                or any(k in low for k in ["package", "packages", "ctc", "salary", "salaries", "stipend", "intern", "internship", "average", "avg", "median", "highest", "lowest", "offers", "how many", "count", "fte", "ppo", "wise", "breakdown", "distribution"])
            )

            is_continuation = starts_continuation or has_pronoun or is_list_continuation or is_ultra_short or is_dim_followup or is_metric_followup

            # If it's a full grammatical question without pronouns or names continuation, it is a new independent topic!
            if is_full_question and not has_pronoun and not is_list_continuation and not starts_continuation:
                is_continuation = False

            # If user introduces a new company without explicit continuation words ("and", "what about"), it is a new company topic!
            if new_companies and not starts_continuation and not has_pronoun:
                is_continuation = False

            # If NOT an explicit continuation, this is a topic switch / new question!
            # Do NOT carry over previous slots of other types!
            if not is_continuation:
                return ContextualizedOutput(
                    standalone_question=new_message,
                    is_followup=False,
                    carried_slots={},
                    resolved_clarification=False
                )

            # ---------------------------------------------------------
            # Handle Explicit Continuations
            # ---------------------------------------------------------
            comp_str = f" at {prev_companies[0]}" if prev_companies else ""
            branch_str = f" in {prev_branches[0]}" if prev_branches else ""
            batch_str = f" for {prev_batches[0]}" if len(prev_batches) == 1 else ""

            # Case A: Names / List continuation or Privacy follow-up
            if is_list_continuation or (has_pronoun and any(k in low for k in ["name", "names", "who", "ppl", "people"])):
                carried = dict(last_spec)
                carried["metric"] = "student_names"
                standalone = f"name of students placed{comp_str}{branch_str}{batch_str}"
                return ContextualizedOutput(
                    standalone_question=standalone,
                    is_followup=True,
                    carried_slots=carried,
                    resolved_clarification=False
                )

            # Privacy keyword follow-up with pronoun (e.g. "show their phone numbers", "roll numbers")
            if has_pronoun and any(k in low for k in ["roll", "phone", "contact", "email", "mobile", "address"]):
                carried = dict(last_spec)
                privacy_kw = "roll numbers" if "roll" in low else ("phone numbers" if "phone" in low else "contact details")
                standalone = f"{privacy_kw} of students placed{comp_str}{branch_str}{batch_str}"
                return ContextualizedOutput(
                    standalone_question=standalone,
                    is_followup=True,
                    carried_slots=carried,
                    resolved_clarification=False
                )

            # Pronoun count follow-up (e.g. "how many students did they hire?", "how many got placed?")
            # NEVER rewrite to "name of students"!
            if has_pronoun and any(k in low for k in ["how many", "count", "number of", "kitne", "kitna"]):
                carried = dict(last_spec)
                carried["metric"] = "placed_students"
                standalone = f"how many students placed{comp_str}{branch_str}{batch_str}"
                return ContextualizedOutput(
                    standalone_question=standalone,
                    is_followup=True,
                    carried_slots=carried,
                    resolved_clarification=False
                )

            # Pronoun interview question follow-up
            if has_pronoun and any(k in low for k in ["question", "questions", "interview", "rounds", "asked"]):
                standalone = f"interview questions asked{comp_str}{branch_str}"
                return ContextualizedOutput(
                    standalone_question=standalone,
                    is_followup=True,
                    carried_slots=dict(last_spec),
                    resolved_clarification=False
                )

            # Case B: Continuation specifying Branch (e.g. "and for IT?", "in CSE", "IT?")
            if new_branches and not new_companies:
                carried = dict(last_spec)
                carried["branches"] = list(new_branches)
                if prev_metric in ["ctc", "avg_ctc", "max_ctc", "min_ctc", "median_ctc"]:
                    standalone = f"What is the {prev_metric.replace('_', ' ')} in {new_branches[0]}{comp_str}{batch_str}?"
                elif prev_metric in ["offers", "total_offers"]:
                    standalone = f"How many offers in {new_branches[0]}{comp_str}{batch_str}?"
                elif prev_metric in ["stipend"]:
                    standalone = f"What stipend in {new_branches[0]}{comp_str}{batch_str}?"
                elif prev_metric in ["placement_pct", "placement_percentage"]:
                    standalone = f"What is the placement percentage in {new_branches[0]}{comp_str}{batch_str}?"
                else:
                    standalone = f"How many students placed in {new_branches[0]}{comp_str}{batch_str}?"

                return ContextualizedOutput(
                    standalone_question=standalone,
                    is_followup=True,
                    carried_slots=carried,
                    resolved_clarification=False
                )

            # Case C: Continuation specifying Batch (e.g. "what about 2021-25?", "only 2022-26")
            if new_batches and not new_companies and not new_branches:
                carried = dict(last_spec)
                carried["batches"] = list(new_batches)
                metric_str = prev_metric.replace('_', ' ') if prev_metric else "placements"
                standalone = f"{metric_str}{comp_str}{branch_str} for {new_batches[0]} batch"
                return ContextualizedOutput(
                    standalone_question=standalone,
                    is_followup=True,
                    carried_slots=carried,
                    resolved_clarification=False
                )

            # Case D: Continuation specifying Company (e.g. "and Microsoft?", "what about Amazon?")
            if new_companies:
                carried = {
                    "companies": [new_companies[0]],
                    "branches": list(prev_branches),
                    "batches": list(prev_batches),
                    "metric": prev_metric or "placed_students",
                    "offer_types": list(prev_offer_types)
                }
                metric_str = prev_metric.replace('_', ' ') if prev_metric else "placements"
                standalone = f"What is the {metric_str} for {new_companies[0]}{branch_str}{batch_str}?"
                return ContextualizedOutput(
                    standalone_question=standalone,
                    is_followup=True,
                    carried_slots=carried,
                    resolved_clarification=False
                )

            # Case E: Continuation specifying Metric or Dimension (e.g. "and average?", "branch wise")
            metric_keywords = {
                "package": "ctc", "packages": "ctc", "ctc": "ctc", "salary": "ctc",
                "average": "avg_ctc", "avg": "avg_ctc", "mean": "avg_ctc",
                "highest": "max_ctc", "max": "max_ctc", "peak": "max_ctc", "top": "max_ctc",
                "lowest": "min_ctc", "min": "min_ctc",
                "median": "median_ctc",
                "stipend": "stipend",
                "how many": "placed_students", "count": "placed_students", "offers": "offers",
                "placement percentage": "placement_percentage", "rate": "placement_percentage"
            }
            has_metric_change = any(k in low for k in metric_keywords)
            has_dim_change = any(k in low for k in ["branch wise", "branch-wise", "batch wise", "batch-wise", "company wise"])

            if (has_metric_change or has_dim_change) and not new_companies and not new_branches and not new_batches:
                carried = dict(last_spec)
                if has_dim_change:
                    if "branch" in low:
                        carried["group_by"] = ["branch"]
                        standalone = f"{prev_companies[0] if prev_companies else 'placements'} {prev_metric or 'package'} branch wise{batch_str}"
                    elif "batch" in low:
                        carried["group_by"] = ["batch"]
                        standalone = f"{prev_companies[0] if prev_companies else 'placements'} {prev_metric or 'package'} batch wise{branch_str}"
                elif has_metric_change:
                    new_metric = prev_metric
                    if any(k in low for k in ["how many offers", "total offers", "number of offers", "offers count", "total offers count", "offers"]):
                        new_metric = "total_offers"
                    elif any(k in low for k in ["highest", "maximum", "max", "top", "peak"]):
                        new_metric = "max_ctc"
                    elif any(k in low for k in ["lowest", "minimum", "min"]):
                        new_metric = "min_ctc"
                    elif any(k in low for k in ["average", "avg", "mean"]):
                        new_metric = "avg_ctc"
                    else:
                        for kw, mval in metric_keywords.items():
                            if kw in low:
                                new_metric = mval
                                break
                    carried["metric"] = new_metric
                    standalone = f"{new_metric.replace('_', ' ')}{comp_str}{branch_str}{batch_str}"
                else:
                    standalone = f"{new_message}{comp_str}{branch_str}{batch_str}"

                return ContextualizedOutput(
                    standalone_question=standalone,
                    is_followup=True,
                    carried_slots=carried,
                    resolved_clarification=False
                )

        # -------------------------------------------------------------
        # Rule 3: Standalone independent question
        # -------------------------------------------------------------
        return ContextualizedOutput(
            standalone_question=new_message,
            is_followup=False,
            carried_slots={},
            resolved_clarification=False
        )
