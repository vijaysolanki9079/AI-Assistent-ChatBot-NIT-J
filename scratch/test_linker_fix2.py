import sys
import os
sys.path.insert(0, os.path.abspath("."))
from src.nlp.fuzzy_linker import FuzzyEntityLinker

linker = FuzzyEntityLinker()
print("link_company('most'):", linker.link_company("most"))
print("link_company('branches'):", linker.link_company("branches"))
print("link_company('b.tech'):", linker.link_company("b.tech"))

