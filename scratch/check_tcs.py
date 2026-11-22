import sys
import os
sys.path.insert(0, os.path.abspath("."))
from src.nlp.fuzzy_linker import FuzzyEntityLinker

linker = FuzzyEntityLinker()
q = "Compare Infosys and TCS hiring across all batches"
print("Entities:", linker.link_entities_in_query(q))

