import os
import glob
import pandas as pd

exp_dir = "NIT-J data/company-experience"
csv_files = glob.glob(os.path.join(exp_dir, "*.csv"))

print(f"Total CSV files found: {len(csv_files)}")
total_rows = 0

for f in sorted(csv_files):
    fname = os.path.basename(f)
    try:
        df = pd.read_csv(f)
        total_rows += len(df)
        print(f"{fname:<25} | {len(df):>5} rows | cols: {list(df.columns)}")
    except Exception as e:
        print(f"Error reading {fname}: {e}")

print(f"\nTotal rows across all experience CSVs: {total_rows}")

