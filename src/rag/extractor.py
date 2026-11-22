import os
import re
import glob
import json
import pandas as pd
from typing import List, Dict, Any, Optional
from src.rag.schema import InterviewExperience, InterviewRound
from src.nlp.entity_resolver import EntityResolver

COMMON_TOPICS = {
    "DSA": ["dsa", "data structures", "algorithms", "dynamic programming", "dp", "trees", "graphs", "binary tree", "trie", "linked list", "recursion", "greedy", "sorting", "stack", "queue"],
    "DBMS": ["dbms", "database", "sql", "normalization", "acid", "indexing", "joins", "transactions"],
    "Operating Systems": ["os", "operating system", "threads", "deadlock", "process", "paging", "virtual memory", "concurrency"],
    "OOPs": ["oops", "object oriented", "polymorphism", "inheritance", "encapsulation", "abstraction", "virtual functions"],
    "System Design": ["system design", "hld", "lld", "load balancer", "microservices", "caching", "scalability"],
    "Computer Networks": ["computer networks", "cn", "tcp/ip", "osi", "dns", "http", "socket"],
    "Core Electronics": ["vlsi", "microprocessor", "microcontroller", "digital electronics", "embedded", "signal processing", "verilog"],
    "Core Mechanical": ["thermodynamics", "fluid mechanics", "heat transfer", "som", "strength of materials", "ic engine", "cad"],
    "Core Chemical": ["mass transfer", "chemical engineering", "distillation", "reactor design", "fluid flow"]
}

ROUND_PATTERNS = [
    (r'(online assessment|online test|oa|coding round|aptitude round|round 1[:\s\-\(]+coding)', "OA", "Online Assessment"),
    (r'(technical round\s*1|round\s*1[:\s\-\(]+technical|first round|technical interview 1)', "Technical", "Technical Round 1"),
    (r'(technical round\s*2|round\s*2[:\s\-\(]+technical|second round|technical interview 2)', "Technical", "Technical Round 2"),
    (r'(technical round\s*3|round\s*3[:\s\-\(]+technical|third round|technical interview 3)', "Technical", "Technical Round 3"),
    (r'(managerial round|techno-managerial|managerial interview|leadership principles)', "Managerial", "Managerial Round"),
    (r'(hr round|hr interview|behavioral round|culture fit)', "HR", "HR Round"),
    (r'(group discussion|gd round|group task)', "GD", "Group Discussion")
]

class ExperienceExtractor:
    def __init__(self, exp_dir: str = "NIT-J data/company-experience"):
        self.exp_dir = exp_dir
        self.resolver = EntityResolver()

    def extract_all(self, output_json: str = "data/interview_experiences_structured.json") -> List[InterviewExperience]:
        csv_files = glob.glob(os.path.join(self.exp_dir, "*.csv"))
        extracted: List[InterviewExperience] = []

        for fpath in sorted(csv_files):
            fname = os.path.basename(fpath)
            c_file = os.path.splitext(fname)[0]
            try:
                df = pd.read_csv(fpath)
            except Exception as e:
                print(f"Error reading {fpath}: {e}")
                continue

            for _, row in df.iterrows():
                body = str(row['body']) if pd.notna(row['body']) else ""
                title = str(row['title']) if pd.notna(row['title']) else ""
                author = str(row['author']) if pd.notna(row['author']) else ""
                date = str(row['date']) if pd.notna(row['date']) else ""
                entry_id = str(row['entry_id']) if pd.notna(row['entry_id']) else ""

                clean_body = body.strip()
                if (
                    len(clean_body) < 80 
                    or len(clean_body.split()) < 25 
                    or clean_body.lower().startswith("start sharing your")
                    or clean_body.lower() in [
                        "start sharing your experience...", "nan", "good", "experience",
                        "placement team is very supportive", "stay focused and consistent.",
                        "well it was good"
                    ]
                ):
                    continue

                # 1. Resolve Company
                company_name = self._resolve_company(c_file, title, body)
                
                # 2. Extract Role & Offer Type
                role = self._extract_role(title, body)
                offer_type = self._extract_offer_type(title, body)
                branch = self._extract_branch(title, body)
                batch = self._extract_batch(title, body, date)

                # 3. Extract Technical Topics
                topics = self._extract_topics(body)

                # 4. Extract Rounds
                rounds = self._extract_rounds(body)

                # 5. Extract Questions
                questions = self._extract_questions(body)

                # 6. Extract Tips
                tips = self._extract_tips(body)

                exp = InterviewExperience(
                    experience_id=entry_id if entry_id else f"exp_{len(extracted)+1}",
                    source_file=fname,
                    company=company_name,
                    role=role,
                    batch=batch,
                    branch=branch,
                    author=author if author and author.upper() != "NAN" else None,
                    date=date if date and date.upper() != "NAN" else None,
                    title=title if title and title.lower() not in ["untitled", "write title here..."] else f"{company_name} Interview Experience",
                    offer_type=offer_type,
                    rounds=rounds,
                    technical_topics=topics,
                    key_questions=questions[:6], # top questions
                    preparation_tips=tips,
                    full_text=clean_body,
                    word_count=len(clean_body.split())
                )
                extracted.append(exp)

        # Save to JSON
        os.makedirs(os.path.dirname(output_json), exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as out:
            json.dump([e.model_dump() for e in extracted], out, indent=2, ensure_ascii=False)

        print(f"Extracted {len(extracted)} structured experiences. Saved to {output_json}")
        return extracted

    def _resolve_company(self, c_file: str, title: str, body: str) -> str:
        if c_file != "_unsorted":
            c_res = self.resolver.resolve_company(c_file)
            if c_res:
                return c_res['canonical_name']
            return c_file.replace("_", " ").title()

        # From title
        t_res = self.resolver.extract_and_resolve_entities(title, enable_fuzzy=False)
        if t_res['companies']:
            return t_res['companies'][0]['canonical_name']

        # From first 3 lines of body
        first_lines = " ".join([l.strip() for l in body.split("\n") if l.strip()][:3])
        b_res = self.resolver.extract_and_resolve_entities(first_lines, enable_fuzzy=False)
        if b_res['companies']:
            return b_res['companies'][0]['canonical_name']

        # Regex heuristics on title
        cleaned = re.sub(r'interview|experience|placement|test|recruitment|–|-|:|at|for|my|journey|selected', ' ', title, flags=re.I).strip()
        words = cleaned.split()
        if words and words[0].lower() not in ["untitled", "write", "how", "what", "prep", "sharing"]:
            return words[0].title()

        return "General"

    def _extract_role(self, title: str, body: str) -> Optional[str]:
        text = title + " " + body[:300]
        roles = [
            ("SDE", r'\b(sde[- ]?[1i]|software development engineer|software engineer)\b'),
            ("Graduate Engineer Trainee", r'\b(get|graduate engineer trainee|trainee engineer)\b'),
            ("Operations Manager", r'\b(operations manager|operations)\b'),
            ("Associate Consultant", r'\b(associate consultant|consultant|analyst)\b'),
            ("Data Engineer", r'\b(data engineer|data analyst|data scientist)\b'),
            ("Hardware Engineer", r'\b(hardware engineer|vlsi engineer|embedded engineer)\b'),
            ("System Engineer", r'\b(system engineer|systems engineer)\b')
        ]
        for role_name, pat in roles:
            if re.search(pat, text, re.I):
                return role_name
        return None

    def _extract_offer_type(self, title: str, body: str) -> str:
        text = (title + " " + body[:300]).lower()
        if "ppo" in text:
            return "PPO"
        if "intern" in text:
            return "Intern"
        return "FTE"

    def _extract_branch(self, title: str, body: str) -> Optional[str]:
        text = title + " " + body[:400]
        b_res = self.resolver.extract_and_resolve_entities(text, enable_fuzzy=False)
        if b_res['branches']:
            return b_res['branches'][0]['short']
        return None

    def _extract_batch(self, title: str, body: str, date: str) -> Optional[str]:
        text = title + " " + body[:300] + " " + date
        m = re.search(r'\b(20\d{2}-20\d{2}|20\d{2}-\d{2})\b', text)
        if m:
            return m.group(1)
        # Check date year e.g. 2026 -> 2022-2026 or 2021-2025
        m_yr = re.search(r'\b(202[4-6])\b', text)
        if m_yr:
            yr = int(m_yr.group(1))
            return f"{yr-4}-{yr}"
        return None

    def _extract_topics(self, body: str) -> List[str]:
        low = body.lower()
        found = []
        for cat, kw_list in COMMON_TOPICS.items():
            if any(re.search(r'\b' + re.escape(kw) + r'\b', low) for kw in kw_list):
                found.append(cat)
        return found

    def _extract_rounds(self, body: str) -> List[InterviewRound]:
        rounds: List[InterviewRound] = []
        lines = body.split("\n")
        
        for idx, (pat, rtype, rname) in enumerate(ROUND_PATTERNS, 1):
            if re.search(pat, body, re.I):
                # find description block if possible
                summary = None
                for i, line in enumerate(lines):
                    if re.search(pat, line, re.I):
                        following = [l.strip() for l in lines[i+1:i+6] if l.strip()]
                        summary = " ".join(following)[:200] if following else None
                        break
                rounds.append(InterviewRound(
                    round_number=len(rounds) + 1,
                    round_name=rname,
                    round_type=rtype,
                    summary=summary
                ))
        return rounds

    def _extract_questions(self, body: str) -> List[str]:
        questions = []
        lines = body.split("\n")
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            # Look for bullet points or numbered lists or question marks
            if line_str.endswith("?") or re.match(r'^(?:[0-9]+[\.\)]|[-•*])\s+[A-Z]', line_str):
                clean_q = re.sub(r'^(?:[0-9]+[\.\)]|[-•*])\s*', '', line_str).strip()
                if 20 <= len(clean_q) <= 250:
                    questions.append(clean_q)
        return questions

    def _extract_tips(self, body: str) -> Optional[str]:
        lines = body.split("\n")
        for i, line in enumerate(lines):
            if re.search(r'\b(preparation tips|advice for juniors|tips|suggestions|key takeaway)\b', line, re.I):
                following = [l.strip() for l in lines[i+1:i+8] if l.strip()]
                if following:
                    return " ".join(following)[:350]
        return None

if __name__ == "__main__":
    extractor = ExperienceExtractor()
    experiences = extractor.extract_all()
