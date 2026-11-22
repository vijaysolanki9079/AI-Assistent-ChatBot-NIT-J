import os
import shutil
import re

SRC_NLP = "src/nlp"
LEGACY_DIR = "legacy"

os.makedirs(LEGACY_DIR, exist_ok=True)

files_to_copy = [
    "query_planner.py",
    "contextualizer.py",
    "llm_parser.py",
    "sql_generator.py",
    "query_spec.py",
    "fuzzy_linker.py",
    "router.py",
    "verifier.py",
    "privacy_classifier.py",
    "privacy_output_guard.py",
    "audit_logger.py",
    "entity_resolver.py"
]

print("Copying NLP files to legacy/...")
for fname in files_to_copy:
    src_path = os.path.join(SRC_NLP, fname)
    dst_path = os.path.join(LEGACY_DIR, fname)
    if os.path.exists(src_path):
        with open(src_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Update internal imports from src.nlp to legacy
        content_mod = content.replace("from src.nlp.", "from legacy.").replace("import src.nlp.", "import legacy.")
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(content_mod)
        print(f"  Copied {src_path} -> {dst_path}")

# Create legacy/local_semantic_parser.py forwarding to / aliasing llm_parser
lsp_content = """# Local Semantic Parser - Legacy Baseline
from legacy.llm_parser import LocalSemanticParser, LLMParser, OllamaClient, get_parser

__all__ = ["LocalSemanticParser", "LLMParser", "OllamaClient", "get_parser"]
"""
with open(os.path.join(LEGACY_DIR, "local_semantic_parser.py"), "w", encoding="utf-8") as f:
    f.write(lsp_content)
print("  Created legacy/local_semantic_parser.py")

# Create legacy/__init__.py
init_content = """# Legacy Rule-Based Pipeline Baseline
from legacy.query_planner import QueryPlanner
from legacy.query_spec import QuerySpec
from legacy.sql_generator import SQLGenerator
from legacy.contextualizer import QueryContextualizer
from legacy.local_semantic_parser import LocalSemanticParser

__all__ = [
    "QueryPlanner",
    "QuerySpec",
    "SQLGenerator",
    "QueryContextualizer",
    "LocalSemanticParser"
]
"""
with open(os.path.join(LEGACY_DIR, "__init__.py"), "w", encoding="utf-8") as f:
    f.write(init_content)
print("  Created legacy/__init__.py")

print("\nLegacy setup complete!")

