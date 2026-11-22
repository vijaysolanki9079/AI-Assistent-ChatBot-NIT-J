import pandas as pd
import re

df_unsorted = pd.read_csv("NIT-J data/company-experience/_unsorted.csv")
untitled_df = df_unsorted[df_unsorted['title'].str.lower().str.contains("untitled|write title", na=False)]

print(f"Total untitled rows in _unsorted: {len(untitled_df)}")
for i, row in untitled_df.head(10).iterrows():
    print(f"\n[Row {i}] Author: {row['author']} | Date: {row['date']}")
    first_few_lines = "\n".join([line.strip() for line in str(row['body']).split("\n") if line.strip()][:4])
    print(first_few_lines[:300])

