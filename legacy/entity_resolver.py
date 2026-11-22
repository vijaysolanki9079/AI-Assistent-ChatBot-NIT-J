import sqlite3
import re
from typing import Dict, List, Optional, Tuple, Any
from src.core.semantic_loader import SemanticLayer
from legacy.fuzzy_linker import FuzzyEntityLinker

DB_PATH = "data/nitj_placement.db"

class EntityResolver:
    """
    Entity Resolver powered by FuzzyEntityLinker:
    - RapidFuzz matching over database alias tables.
    - >= 90 accept automatically.
    - 70-89 ask 'Did you mean X?'.
    - < 70 ask for clarification.
    - 2-letter acronym whitelist (MS, GS, TI, HP, EY) never fuzzy matched.
    - Canonical branch master table matching.
    - Batch derivation from roll-number prefix.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.semantic = SemanticLayer.get_instance()
        self.linker = FuzzyEntityLinker(db_path)
        self.companies = self.linker.companies
        self.id_to_company = self.linker.id_to_company
        self.company_aliases = self.linker.company_aliases
        self.branches = self.linker.branches
        self.branch_aliases = self.linker.branch_aliases
        self.batches = self.linker.batches

    def resolve_company(self, text: str) -> Optional[Dict[str, Any]]:
        """Resolve company using FuzzyEntityLinker."""
        res = self.linker.link_company(text)
        if not res:
            return None
        return {
            "id": res.get("id"),
            "canonical_name": res.get("canonical_name"),
            "match_type": res.get("match_type"),
            "confidence": res.get("score", 100.0) / 100.0,
            "status": res.get("status"),
            "suggestion": res.get("suggestion")
        }

    def resolve_branch(self, text: str) -> Optional[Dict[str, Any]]:
        """Resolve branch using FuzzyEntityLinker."""
        res = self.linker.link_branch(text)
        if not res:
            return None
        return {
            "code": res.get("branch_code"),
            "short": res.get("short_name"),
            "canonical": res.get("canonical_name"),
            "match_type": res.get("match_type"),
            "confidence": res.get("score", 100.0) / 100.0,
            "status": res.get("status"),
            "suggestion": res.get("suggestion")
        }

    def resolve_batch(self, text: str) -> Optional[str]:
        """Resolve batch / graduation year or roll-number prefix."""
        return self.linker.derive_batch(text)

    def extract_and_resolve_entities(self, question: str, enable_fuzzy: bool = True) -> Dict[str, Any]:
        """Extract all resolved companies, branches, batches and suggestions."""
        linked = self.linker.link_entities_in_query(question)
        return {
            "companies": linked["companies"],
            "branches": linked["branches"],
            "batches": linked["batches"],
            "suggestions": linked.get("suggestions", {}),
            "is_ambiguous": len(linked["companies"]) == 0 and len(linked["branches"]) == 0 and len(linked["batches"]) == 0
        }
