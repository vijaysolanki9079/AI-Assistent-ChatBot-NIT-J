import sys, os
sys.path.insert(0, os.path.abspath("."))
from src.nlp.fuzzy_linker import FuzzyEntityLinker

el = FuzzyEntityLinker()
q = "Count of offers above 12 LPA in Textile Technology across all batches"
STOPWORDS = {"in", "at", "for", "from", "by", "to", "of", "with", "and", "or", "the", "a", "an", "is", "was", "are", "were"}

import re
words = re.findall(r'[A-Za-z0-9&]+', q)
candidates = []
for n in [5, 4, 3, 2, 1]:
    for i in range(len(words) - n + 1):
        chunk = words[i:i+n]
        while chunk and chunk[0].lower() in STOPWORDS and " ".join(chunk).lower() not in el.company_aliases:
            chunk = chunk[1:]
        while chunk and chunk[-1].lower() in STOPWORDS and " ".join(chunk).lower() not in el.company_aliases:
            chunk = chunk[:-1]
        if chunk:
            phrase = " ".join(chunk)
            if phrase not in candidates:
                candidates.append(phrase)

print("Cleaned candidates:", candidates)
for cand in candidates:
    c_link = el.link_company(cand)
    if c_link:
        print(f"Cand '{cand}' -> Company: {c_link}")
