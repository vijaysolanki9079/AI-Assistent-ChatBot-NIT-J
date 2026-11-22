import sys
import os
sys.path.insert(0, os.path.abspath("."))
from src.nlp.fuzzy_linker import FuzzyEntityLinker

linker = FuzzyEntityLinker()
q = "Which companies hired zero students from Information Technology?"
print("Entities:", linker.link_entities_in_query(q))
print("link_branch('information technology'):", linker.link_branch("information technology"))

