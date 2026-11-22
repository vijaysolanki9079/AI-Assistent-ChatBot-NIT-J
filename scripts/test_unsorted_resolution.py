import sys, os
sys.path.insert(0, os.path.abspath("."))
import pandas as pd
from src.nlp.entity_resolver import EntityResolver

resolver = EntityResolver()
df_unsorted = pd.read_csv("NIT-J data/company-experience/_unsorted.csv")

resolved_count = 0
unresolved_titles = []

for i, row in df_unsorted.iterrows():
    title = str(row['title'])
    body_snippet = str(row['body'])[:200]
    # Check title first, then body snippet
    res = resolver.extract_and_resolve_entities(title)
    if not res['companies']:
        res = resolver.extract_and_resolve_entities(title + " " + body_snippet)
    
    if res['companies']:
        resolved_count += 1
    else:
        unresolved_titles.append(title)

print(f"Total unsorted: {len(df_unsorted)}")
print(f"Resolved to DB companies: {resolved_count} ({resolved_count/len(df_unsorted)*100:.1f}%)")
print(f"Unresolved sample (first 15):")
for t in unresolved_titles[:15]:
    print(" -", t)
