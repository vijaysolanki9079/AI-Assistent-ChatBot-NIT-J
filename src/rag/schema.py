from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class InterviewRound(BaseModel):
    round_number: Optional[int] = None
    round_name: str = Field(..., description="E.g., Online Assessment, Technical Round 1, Managerial Round, HR Round")
    round_type: str = Field("Technical", description="OA, Technical, HR, GD, Managerial")
    topics_covered: List[str] = Field(default_factory=list, description="DSA, OS, DBMS, OOP, System Design, Core Subjects")
    questions_asked: List[str] = Field(default_factory=list, description="Specific questions or problem statements mentioned")
    summary: Optional[str] = None

class InterviewExperience(BaseModel):
    experience_id: str
    source_file: str
    company: str = Field(..., description="Canonical company name aligned with placement database")
    role: Optional[str] = None
    batch: Optional[str] = None
    branch: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    title: str
    offer_type: Optional[str] = "FTE" # FTE, PPO, Intern, etc.
    rounds: List[InterviewRound] = Field(default_factory=list)
    technical_topics: List[str] = Field(default_factory=list)
    key_questions: List[str] = Field(default_factory=list)
    preparation_tips: Optional[str] = None
    full_text: str
    word_count: int = 0

