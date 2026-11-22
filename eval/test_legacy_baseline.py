import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath("."))

from legacy.query_planner import QueryPlanner
from legacy.local_semantic_parser import LocalSemanticParser
from legacy.sql_generator import SafeSQLService, TemplateSQLGenerator
from legacy.contextualizer import QueryContextualizer

print("Successfully imported all legacy modules:")
print(" - legacy.query_planner.QueryPlanner")
print(" - legacy.local_semantic_parser.LocalSemanticParser")
print(" - legacy.sql_generator.SafeSQLService")
print(" - legacy.sql_generator.TemplateSQLGenerator")
print(" - legacy.contextualizer.QueryContextualizer")

# Test instantiation and basic execution
planner = QueryPlanner()
res = planner.plan_and_execute("What is Microsoft's package?")
print("\nTest execution of legacy planner on 'What is Microsoft''s package?':")
print("Answer snippet:", res.get("answer", "")[:120])
assert "Microsoft" in res.get("answer", ""), "Expected Microsoft in answer"
assert res.get("category") in ("lookup", "profile", "success", "structured"), f"Unexpected category: {res.get('category')}"
print("Legacy QueryPlanner executed and asserted successfully!")

# Test parser directly
parser = LocalSemanticParser()
spec = parser.parse("How many students got placed in Amazon?")
print("\nTest LocalSemanticParser on 'How many students got placed in Amazon?':")
print("Parsed intent:", spec.intent, "| companies:", spec.companies)
assert "Amazon" in spec.companies, f"Expected Amazon in companies, got {spec.companies}"
print("LocalSemanticParser executed successfully!")

print("\nALL LEGACY BASELINE VERIFICATIONS PASSED!")
