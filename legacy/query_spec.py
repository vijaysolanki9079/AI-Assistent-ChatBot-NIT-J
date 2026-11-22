"""
QuerySpec Schema for NITJ Placement Assistant.
Defines the Pydantic data structure for LLM intent parsing and semantic query representation.
Redesigned as compositional: metrics[] x filters{company, branch, batch, offer_type, sector, gender, category} x group_by[].
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, model_validator

IntentType = Literal[
    "lookup",
    "count",
    "breakdown",
    "ranking",
    "compare",
    "trend",
    "hybrid",
    "clarify",
    "out_of_scope",
    "privacy",
    "profile"
]

SUPPORTED_METRICS = {
    "placed_students",
    "total_offers",
    "placement_pct",
    "avg_ctc",
    "median_ctc",
    "max_ctc",
    "min_ctc",
    "company_count",
    "intern_count",
    "top_recruiters"
}

class QuerySpec(BaseModel):
    """
    Structured semantic representation of user question and context.
    Compositional formula: metrics[] x filters{} x group_by[]
    """
    intent: IntentType = Field(
        ...,
        description="Core intent: lookup, count, breakdown, ranking, compare, trend, hybrid, clarify, out_of_scope, privacy, profile"
    )
    metrics: List[str] = Field(
        default_factory=list,
        description="Target metrics: placed_students, total_offers, placement_pct, avg_ctc, median_ctc, max_ctc, min_ctc, company_count, intern_count, top_recruiters"
    )
    metric: Optional[str] = Field(
        default=None,
        description="Primary target metric (synced with metrics[0] for backward compatibility)"
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Compositional filters: company, branch, batch, offer_type, sector, gender, category, etc."
    )
    group_by: List[str] = Field(
        default_factory=list,
        description="Grouping dimensions: branch, batch, company, offer_type, sector"
    )
    companies: List[str] = Field(
        default_factory=list,
        description="Extracted company names (synced with filters['company'])"
    )
    branches: List[str] = Field(
        default_factory=list,
        description="Extracted branch codes (synced with filters['branch'])"
    )
    batches: List[str] = Field(
        default_factory=list,
        description="Extracted academic batches (synced with filters['batch'])"
    )
    offer_types: List[str] = Field(
        default_factory=list,
        description="Extracted offer types (synced with filters['offer_type'])"
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions made when defaulting missing slots (e.g. 'Across all batches 2020-24 to 2022-26, full-time offers only')"
    )
    needs_clarification: bool = Field(
        default=False,
        description="Whether query requires user clarification due to genuine ambiguity"
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Specific clarifying question naming exactly what is missing"
    )
    privacy_flag: bool = Field(
        default=False,
        description="True if query requests confidential PII"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0"
    )

    @model_validator(mode="after")
    def sync_fields(self):
        # 1. Sync metric <-> metrics
        if self.metrics:
            if not self.metric:
                self.metric = self.metrics[0]
        elif self.metric:
            self.metrics = [self.metric]

        # 2. Sync filters <-> convenience fields
        if self.companies and "company" not in self.filters:
            self.filters["company"] = self.companies
        elif "company" in self.filters and not self.companies:
            comp = self.filters["company"]
            self.companies = comp if isinstance(comp, list) else [comp]

        if self.branches and "branch" not in self.filters:
            self.filters["branch"] = self.branches
        elif "branch" in self.filters and not self.branches:
            br = self.filters["branch"]
            self.branches = br if isinstance(br, list) else [br]

        if self.batches and "batch" not in self.filters:
            self.filters["batch"] = self.batches
        elif "batch" in self.filters and not self.batches:
            bt = self.filters["batch"]
            self.batches = bt if isinstance(bt, list) else [bt]

        if self.offer_types and "offer_type" not in self.filters:
            self.filters["offer_type"] = self.offer_types
        elif "offer_type" in self.filters and not self.offer_types:
            ot = self.filters["offer_type"]
            self.offer_types = ot if isinstance(ot, list) else [ot]

        return self

    class Config:
        extra = "ignore"
