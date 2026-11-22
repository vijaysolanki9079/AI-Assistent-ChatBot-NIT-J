import sys, os
sys.path.insert(0, os.path.abspath("."))
import re
import glob
import pandas as pd
from src.nlp.entity_resolver import EntityResolver

resolver = EntityResolver()

files = glob.glob("NIT-J data/company-experience/*.csv")
records = []

for f in files:
    fname = os.path.basename(f)
    c_file = os.path.splitext(fname)[0]
    df = pd.read_csv(f)
    
    for _, row in df.iterrows():
        body = str(row['body']) if pd.notna(row['body']) else ""
        title = str(row['title']) if pd.notna(row['title']) else ""
        author = str(row['author']) if pd.notna(row['author']) else ""
        date = str(row['date']) if pd.notna(row['date']) else ""
        entry_id = str(row['entry_id']) if pd.notna(row['entry_id']) else ""
        
        # Skip pure placeholders
        if len(body.strip()) < 40 or body.strip() in ["Start sharing your experience...", "nan", "Good", "Experience"]:
            continue
            
        # Determine company
        resolved_company = None
        if c_file != "_unsorted":
            c_res = resolver.resolve_company(c_file)
            if c_res:
                resolved_company = c_res['canonical_name']
            else:
                resolved_company = c_file.title()
        else:
            # Try to resolve from title first
            c_res = resolver.extract_and_resolve_entities(title)
            if c_res['companies']:
                resolved_company = c_res['companies'][0]['canonical_name']
            else:
                # Try from first 2 lines of body
                first_lines = " ".join([l.strip() for l in body.split("\n") if l.strip()][:2])
                c_res = resolver.extract_and_resolve_entities(first_lines)
                if c_res['companies']:
                    resolved_company = c_res['companies'][0]['canonical_name']
                else:
                    # Fallback to title clean
                    cleaned_title = re.sub(r'interview|experience|placement|test|recruitment|–|-|:', ' ', title, flags=re.I).strip()
                    if cleaned_title and len(cleaned_title) > 2 and cleaned_title.lower() not in ["untitled", "write title here..."]:
                        resolved_company = cleaned_title.split()[0].title()
                    else:
                        resolved_company = "General / Unknown"

        records.append({
            "entry_id": entry_id,
            "source_file": fname,
            "company": resolved_company,
            "title": title,
            "author": author,
            "date": date,
            "body_len": len(body),
            "snippet": body[:120].replace("\n", " ")
        })

print(f"Total extracted substantive records: {len(records)} / 609")
comp_counts = pd.Series([r['company'] for r in records]).value_counts()
print("\nTop 25 companies by interview experiences:")
print(comp_counts.head(25))
