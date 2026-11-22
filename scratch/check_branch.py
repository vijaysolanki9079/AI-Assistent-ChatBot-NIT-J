import sys
import os
sys.path.insert(0, os.path.abspath("."))
from src.nlp.fuzzy_linker import FuzzyEntityLinker

linker = FuzzyEntityLinker()
print("Companies with 'branc':", [(c, a) for a, c in linker.company_aliases.items() if 'branc' in a.lower()])
res = linker.link_company("branch")
print("link_company('branch'):", res)
res2 = linker.link_company("branch-wise")
print("link_company('branch-wise'):", res2)

