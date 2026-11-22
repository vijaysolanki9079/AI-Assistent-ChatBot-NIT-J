import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from eval.oracle import PlacementOracle
import sqlite3

oracle = PlacementOracle()
df_22 = oracle.df_offers[oracle.df_offers["batch"] == "2022-2026"]
print("Oracle 2022-2026 offers:", len(df_22))

conn = sqlite3.connect("data/nitj_placement.db")
db_22 = conn.execute("""
    SELECT COUNT(*) 
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    WHERE s.batch_id = '2022-2026'
""").fetchone()[0]
print("DB 2022-2026 offers:", db_22)
