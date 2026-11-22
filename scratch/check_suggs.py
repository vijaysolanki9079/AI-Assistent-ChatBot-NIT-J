import sys
import os
sys.path.insert(0, os.path.abspath("."))
from src.nlp.fuzzy_linker import FuzzyEntityLinker

linker = FuzzyEntityLinker()
print("Suggestions for B.Tech/M.Tech:", linker.link_entities_in_query("Which companies hired both B.Tech and M.Tech students?")["suggestions"])
print("Suggestions for long intern:", linker.link_entities_in_query("How many long intern offers were converted with full-time confirmation?")["suggestions"])
print("Suggestions for compound:", linker.link_entities_in_query("How many offers had compound packages with both stipend and CTC?")["suggestions"])

