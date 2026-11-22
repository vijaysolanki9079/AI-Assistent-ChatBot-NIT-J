import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from eval.oracle import PlacementOracle

oracle = PlacementOracle()
df = oracle.df_offers
df_21 = df[df["batch"] == "2021-2025"]
print("Oracle 2021-2025 branch breakdown:")
print(df_21["branch"].value_counts())
print("Total:", len(df_21))
