import pandas as pd
import json

df_amz = pd.read_csv("NIT-J data/company-experience/amazon.csv")
print("=== AMAZON SAMPLE ===")
for i, row in df_amz.head(2).iterrows():
    print(f"Title: {row['title']}")
    print(f"Date: {row['date']}, Author: {row['author']}")
    print(f"Body snippet (first 300 chars):\n{row['body'][:300]}")
    print("-" * 50)

df_unsorted = pd.read_csv("NIT-J data/company-experience/_unsorted.csv")
print("\n=== UNSORTED SAMPLE ===")
print("Company names in _unsorted:", df_unsorted['company_name'].value_counts().head(10))
for i, row in df_unsorted.head(2).iterrows():
    print(f"Company: {row['company_name']}")
    print(f"Title: {row['title']}")
    print(f"Body snippet:\n{row['body'][:300]}")
    print("-" * 50)

