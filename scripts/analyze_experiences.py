import os
import re
import glob
import pandas as pd
from collections import Counter

exp_dir = "NIT-J data/company-experience"
company_files = [f for f in glob.glob(os.path.join(exp_dir, "*.csv")) if not f.endswith("_unsorted.csv")]

print("=== COMPANY-SPECIFIC CSVS ===")
company_csv_counts = {}
for f in company_files:
    cname = os.path.splitext(os.path.basename(f))[0]
    df = pd.read_csv(f)
    company_csv_counts[cname] = len(df)
print(f"Total company files: {len(company_files)}, Total rows: {sum(company_csv_counts.values())}")
for c, cnt in sorted(company_csv_counts.items(), key=lambda x: -x[1]):
    print(f"  {c:<20}: {cnt} reviews")

print("\n=== UNSORTED CSV ===")
df_unsorted = pd.read_csv(os.path.join(exp_dir, "_unsorted.csv"))
print(f"Total rows in _unsorted: {len(df_unsorted)}")

# Let's inspect titles in _unsorted
titles = df_unsorted['title'].dropna().tolist()
print("\nSample titles from _unsorted:")
for t in titles[:20]:
    print(" -", t)

