import os
import yaml
from typing import Dict, List, Any, Optional

SEMANTIC_LAYER_PATH = "semantic_layer.yaml"

class SemanticLayer:
    _instance = None

    def __init__(self, path: str = SEMANTIC_LAYER_PATH):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Semantic layer specification not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

        self.dialect = self.data.get("dialect", "sqlite")
        self.metrics = self.data.get("metrics", {})
        self.branches = self.data.get("branches", {})
        self.divisions = self.data.get("divisions", {})
        self.companies = self.data.get("companies", {})
        self.batch_conventions = self.data.get("batch_conventions", {})
        self.offer_types = self.data.get("offer_types", {})
        self.safety_rules = self.data.get("safety_and_verification", {})

    @classmethod
    def get_instance(cls, path: str = SEMANTIC_LAYER_PATH):
        if cls._instance is None:
            cls._instance = cls(path)
        return cls._instance

    def get_metric(self, name: str) -> Optional[Dict[str, Any]]:
        return self.metrics.get(name)

    def get_branch_info(self, short_or_code: str) -> Optional[Dict[str, Any]]:
        for k, v in self.branches.items():
            if k.lower() == short_or_code.lower() or v.get("code") == short_or_code:
                return v
        return None

    def get_company_info(self, name: str) -> Optional[Dict[str, Any]]:
        for k, v in self.companies.items():
            if k.lower() == name.lower() or v.get("canonical", "").lower() == name.lower():
                return v
        return None

