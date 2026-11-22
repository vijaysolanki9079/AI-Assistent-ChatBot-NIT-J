"""
LLM Privacy Classifier with Conversational History Context.
Classifies user questions (and follow-ups referencing chat history) for PII/privacy violations
using a local LLM with schema constraints, backed by a semantic linguistic fallback.
"""

import json
import logging
import re
import urllib.request
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PrivacyClassificationResult(BaseModel):
    is_privacy_violation: bool
    confidence: float
    violation_type: Optional[str] = None  # hr_contact, contact_info, roll_number, parent_details, address_info, followup_pii
    explanation: Optional[str] = None
    response_message: str = (
        "For student privacy and institutional confidentiality, roll numbers, phone numbers, "
        "personal emails, residential addresses, parent details, and HR/recruiter contact information "
        "are strictly protected and cannot be shared. I can provide student placement lists by company, "
        "branch statistics, compensation packages, and alumni interview experiences."
    )


class LLMPrivacyClassifier:
    """
    Evaluates whether a user prompt seeks confidential student PII (roll numbers, phone,
    personal emails, addresses, parents) or confidential institutional HR recruiter contacts.
    Student names and placed companies (honor rolls / placement records) are permitted.
    """

    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL_NAME = "llama3.2:latest"

    SYSTEM_PROMPT = """You are a strict Data Privacy & Compliance Guard for the NIT Jalandhar Placement System.
Your job is to determine if the user query is seeking confidential personal PII or restricted institutional recruiter records.

Strictly Forbidden (Privacy Violations):
1. Roll numbers / registration numbers / student IDs (e.g., 'what is their roll no', 'roll number of 52 LPA candidate')
2. Personal contact details (phone numbers, mobile numbers, personal emails, residential addresses, parents' names / contacts)
3. HR & Recruiter contact details (HR name, HR email, HR phone, campus recruiter POC, coordinator contacts). Under NO circumstances should HR details ever be shared.
4. Follow-ups seeking confidential details of students (e.g., 'give me their phone numbers', 'what is their roll number', 'share their emails')

Permitted (Safe Information):
- Student names and placed company / branch / cohort (honor roll / placement lists, e.g. 'who got placed in Google', 'give me names of students placed in Microsoft')
- Placement counts, package distributions, averages, medians, branch distributions, company hiring stats, alumni interview reviews.

Output ONLY a JSON object:
{
  "is_privacy_violation": true/false,
  "violation_type": "hr_contact" | "contact_info" | "roll_number" | "parent_details" | "address_info" | "followup_pii" | "none",
  "confidence": 0.0 - 1.0,
  "explanation": "short rationale"
}
"""

    def __init__(self, ollama_url: str = OLLAMA_URL, model: str = MODEL_NAME):
        self.ollama_url = ollama_url
        self.model = model

    def classify(
        self, question: str, history: Optional[List[Dict[str, str]]] = None
    ) -> PrivacyClassificationResult:
        """
        Classify query + chat history.
        First tries local LLM; falls back to linguistic semantic classifier.
        """
        # Try LLM via Ollama
        llm_result = self._classify_via_llm(question, history)
        if llm_result is not None:
            return llm_result

        # Semantic linguistic fallback
        return self._classify_semantic_fallback(question, history)

    def _classify_via_llm(
        self, question: str, history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[PrivacyClassificationResult]:
        """Query local Ollama with JSON schema prompt."""
        try:
            history_context = ""
            if history:
                history_context = "Chat History:\n" + "\n".join(
                    f"{turn.get('role', 'user')}: {turn.get('content', '')}"
                    for turn in history[-3:]
                ) + "\n\n"

            prompt = f"{history_context}Current User Query: {question}\n\nJSON Output:"
            payload = {
                "model": self.model,
                "prompt": f"{self.SYSTEM_PROMPT}\n\n{prompt}",
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0}
            }

            req = urllib.request.Request(
                self.ollama_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_response = data.get("response", "").strip()
                parsed = json.loads(raw_response)
                is_violation = bool(parsed.get("is_privacy_violation", False))
                conf = float(parsed.get("confidence", 0.95))
                v_type = parsed.get("violation_type", "none")
                expl = parsed.get("explanation", "")
                return PrivacyClassificationResult(
                    is_privacy_violation=is_violation,
                    confidence=conf,
                    violation_type=v_type if is_violation else None,
                    explanation=expl
                )
        except Exception:
            return None

    def _classify_semantic_fallback(
        self, question: str, history: Optional[List[Dict[str, str]]] = None
    ) -> PrivacyClassificationResult:
        """
        Semantic linguistic classifier for PII and conversational follow-ups.
        Analyzes syntactic role and intent target (identity vs aggregate metrics).
        """
        q_raw = question.strip().lower()

        # 0. Prompt Injection / System Tampering Guard
        injection_patterns = [
            "ignore instructions", "ignore all previous", "ignore previous instructions",
            "ignore your rules", "ignore rules", "disregard instructions", "disregard rules",
            "dump database", "dump the database", "drop table", "drop database",
            "system prompt", "reveal passwords", "print schema", "sql injection",
            "bypass guard", "bypass security", "override safety", "leak data"
        ]
        if any(pat in q_raw for pat in injection_patterns):
            return PrivacyClassificationResult(
                is_privacy_violation=True,
                confidence=1.0,
                violation_type="prompt_injection",
                explanation="System administration, injection, or instruction override attempt detected.",
                response_message="I cannot execute system administration commands or dump internal system files. I can assist with placement statistics, recruiting companies, branch trends, and compensation records."
            )

        q_clean = re.sub(r'[\?\.,!]', ' ', q_raw)
        tokens = set(q_clean.split())
        text_with_spaces = f" {q_clean} "

        # 1. Strictly Forbidden Target Indicators (PII & Recruiter Confidentiality)
        # Safe metric exemption: queries asking for company rankings ("top recruiters", "major recruiters", "recruiting companies")
        is_recruiter_metric = any(
            tr in q_clean for tr in [
                "top recruiter", "top recruiters", "best recruiter", "best recruiters",
                "major recruiter", "major recruiters", "key recruiter", "key recruiters",
                "top company", "top companies", "recruiting companies", "recruiting company",
                "who recruited", "companies that recruited"
            ]
        )

        hr_indicators = {
            "hr", "hrs", "hr contact", "hr contacts", "hr email", "hr emails", "hr mail", "hr mails",
            "hr phone", "hr phones", "hr mobile", "hr number", "hr numbers", "hr name", "hr names",
            "recruiter email", "recruiter emails", "recruiter mail",
            "recruiter contact", "recruiter contacts", "recruiter phone", "recruiter phones",
            "recruiter mobile", "recruiter name", "recruiter names", "poc", "pocs", "point of contact",
            "points of contact", "placement coordinator contact",
            "placement coordinator", "hr details", "recruiter details", "hr sheet", "spoc", "spocs"
        }
        if not is_recruiter_metric:
            hr_indicators.update({"campus recruiter contact", "recruiter person"})
        roll_indicators = {
            "roll", "rolls", "roll no", "roll nos", "roll number", "roll numbers",
            "registration", "reg no", "registration no", "registration number", "registration numbers",
            "student id", "student ids", "student_id"
        }
        contact_indicators = {
            "phone", "phones", "mobile", "mobiles", "whatsapp", "phone number", "phone numbers",
            "mobile number", "mobile numbers", "contact number", "contact numbers", "personal phone", "call"
        }
        email_indicators = {
            "email", "emails", "mail", "mails", "mail id", "mail ids", "email id", "email ids",
            "personal email", "personal emails", "gmail"
        }
        parent_indicators = {
            "parent", "parents", "father", "fathers", "father name", "father's name",
            "mother", "mothers", "mother name", "mother's name", "family", "guardian", "guardians"
        }
        address_indicators = {
            "address", "addresses", "residential address", "residential addresses",
            "home address", "home addresses", "permanent address", "pincode", "pincodes", "pin code", "pin codes"
        }

        # 2. Check forbidden target matches
        # A. HR / Recruiter Details (Hard Red Line - Never Leaked)
        if any(rec in q_clean for rec in ["recruiter", "hr", "company poc", "campus recruiter"]) and any(em in q_clean for em in ["email", "mail", "contact", "phone", "number"]):
            return PrivacyClassificationResult(
                is_privacy_violation=True,
                confidence=1.0,
                violation_type="hr_contact",
                explanation="Query requests confidential institutional HR / recruiter contact records.",
                response_message="HR contact and recruiter information is strictly confidential and not shared."
            )

        for pat in hr_indicators:
            if f" {pat} " in text_with_spaces or pat in q_clean:
                return PrivacyClassificationResult(
                    is_privacy_violation=True,
                    confidence=1.0,
                    violation_type="hr_contact",
                    explanation=f"Query requests confidential institutional HR / recruiter contact records ('{pat}').",
                    response_message="HR contact information is strictly confidential and not shared."
                )

        # B. Institutional Roll / Registration Numbers
        for pat in roll_indicators:
            if f" {pat} " in text_with_spaces:
                return PrivacyClassificationResult(
                    is_privacy_violation=True,
                    confidence=1.0,
                    violation_type="roll_number",
                    explanation=f"Query requests institutional roll/registration numbers ('{pat}').",
                    response_message="Student roll numbers and personal identification details are strictly confidential."
                )

        # C. Personal Contact & Email Records
        for pat in contact_indicators:
            if f" {pat} " in text_with_spaces:
                return PrivacyClassificationResult(
                    is_privacy_violation=True,
                    confidence=1.0,
                    violation_type="contact_info",
                    explanation=f"Query requests confidential student phone/contact numbers ('{pat}').",
                    response_message="Student phone numbers and contact details are strictly confidential and protected under institutional privacy policy."
                )

        for pat in email_indicators:
            if f" {pat} " in text_with_spaces:
                return PrivacyClassificationResult(
                    is_privacy_violation=True,
                    confidence=1.0,
                    violation_type="contact_info",
                    explanation=f"Query requests confidential student email addresses ('{pat}').",
                    response_message="Personal contact and email details are strictly confidential."
                )

        # D. Parent / Family Records
        for pat in parent_indicators:
            if f" {pat} " in text_with_spaces:
                return PrivacyClassificationResult(
                    is_privacy_violation=True,
                    confidence=1.0,
                    violation_type="parent_details",
                    explanation=f"Query requests confidential parent / guardian records ('{pat}').",
                    response_message="Parent and family details are strictly confidential."
                )

        # E. Personal Residential Addresses
        for pat in address_indicators:
            if f" {pat} " in text_with_spaces:
                return PrivacyClassificationResult(
                    is_privacy_violation=True,
                    confidence=1.0,
                    violation_type="address_info",
                    explanation=f"Query requests confidential student residential addresses ('{pat}').",
                    response_message="Personal residential addresses are strictly confidential."
                )

        # 3. Conversational Follow-Up Analysis with History
        # e.g., History: '40 students placed in Microsoft' -> Follow-up: 'give me their phone numbers', 'what are their roll numbers'
        if history:
            referential_pronouns = ["their", "them", "these students", "those students", "each of one", "each one"]
            has_pronoun = any(p in q_clean for p in referential_pronouns)

            if has_pronoun:
                if any(w in q_clean for w in ["roll", "phone", "mobile", "contact", "email", "address", "parent", "father", "mother", "hr", "recruiter", "whatsapp"]):
                    return PrivacyClassificationResult(
                        is_privacy_violation=True,
                        confidence=1.0,
                        violation_type="followup_pii",
                        explanation="Follow-up query requests confidential student records (roll no, contact, or HR details) of individuals discussed in previous turn."
                    )

        # Safe Query (Aggregate or Non-PII)
        return PrivacyClassificationResult(
            is_privacy_violation=False,
            confidence=0.98,
            violation_type=None,
            explanation="Query requests aggregate placement metrics without personal identification."
        )

