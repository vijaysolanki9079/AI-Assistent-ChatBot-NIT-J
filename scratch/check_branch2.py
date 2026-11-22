import sys
import os
sys.path.insert(0, os.path.abspath("."))
from src.nlp.fuzzy_linker import FuzzyEntityLinker
from src.nlp.entity_resolver import EntityResolver

resolver = EntityResolver()
text = "Year-wise average package for Computer Science and Engineering"
res = resolver.extract_and_resolve_entities(text)
print("Entities for:", text)
print(res)

