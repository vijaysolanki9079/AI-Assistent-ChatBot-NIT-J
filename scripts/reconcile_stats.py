"""
Reconciliation script: compares computed placed students, avg and max CTC per batch x branch
against official Count Wise Details sheets (loaded into batch_branch_stats).
Flags any mismatches > 5% with detailed causes.
DO NOT TUNE NUMBERS TO MATCH.
"""

import sqlite3
import pandas as pd

DB_PATH = "data/nitj_placement.db"

def reconcile():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Get all records from batch_branch_stats for UG batches (2020-2024, 2021-2025, 2022-2026)
    cur.execute("""
    SELECT batch_id, branch_code, discipline_raw, eligible_students, placed_students,
           avg_ctc, max_ctc, placement_pct
    FROM batch_branch_stats
    WHERE degree = 'B.Tech'
    ORDER BY batch_id, branch_code
    """)
    rows = cur.fetchall()

    results = []
    large_mismatches = []

    for batch_id, branch_code, disc, off_elig, off_placed, off_avg, off_max, off_pct in rows:
        if branch_code == "TOTAL":
            # Batch-wide computation
            # 1. Computed placed students
            cur.execute("""
            SELECT COUNT(DISTINCT s.student_id)
            FROM students s
            JOIN offers o ON s.student_id = o.student_id
            WHERE s.batch_id = ?
              AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
            """, (batch_id,))
            comp_placed = cur.fetchone()[0]

            # 2. Computed max CTC
            cur.execute("""
            SELECT MAX(o.ctc_lpa)
            FROM students s
            JOIN offers o ON s.student_id = o.student_id
            WHERE s.batch_id = ?
              AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
              AND o.ctc_lpa IS NOT NULL
            """, (batch_id,))
            comp_max = cur.fetchone()[0]

            # 3. Computed avg CTC (highest per student)
            cur.execute("""
            WITH highest_offers AS (
              SELECT s.student_id, MAX(o.ctc_lpa) as highest_ctc
              FROM students s
              JOIN offers o ON s.student_id = o.student_id
              WHERE s.batch_id = ?
                AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                AND o.ctc_lpa IS NOT NULL
              GROUP BY s.student_id
            )
            SELECT ROUND(AVG(highest_ctc), 2), COUNT(*)
            FROM highest_offers
            """, (batch_id,))
            comp_avg, student_count_with_ctc = cur.fetchone()

        else:
            # Branch-specific computation
            # 1. Computed placed students
            cur.execute("""
            SELECT COUNT(DISTINCT s.student_id)
            FROM students s
            JOIN offers o ON s.student_id = o.student_id
            WHERE s.batch_id = ? AND s.branch_code = ?
              AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
            """, (batch_id, branch_code))
            comp_placed = cur.fetchone()[0]

            # 2. Computed max CTC
            cur.execute("""
            SELECT MAX(o.ctc_lpa)
            FROM students s
            JOIN offers o ON s.student_id = o.student_id
            WHERE s.batch_id = ? AND s.branch_code = ?
              AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
              AND o.ctc_lpa IS NOT NULL
            """, (batch_id, branch_code))
            comp_max = cur.fetchone()[0]

            # 3. Computed avg CTC (highest per student)
            cur.execute("""
            WITH highest_offers AS (
              SELECT s.student_id, MAX(o.ctc_lpa) as highest_ctc
              FROM students s
              JOIN offers o ON s.student_id = o.student_id
              WHERE s.batch_id = ? AND s.branch_code = ?
                AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
                AND o.ctc_lpa IS NOT NULL
              GROUP BY s.student_id
            )
            SELECT ROUND(AVG(highest_ctc), 2), COUNT(*)
            FROM highest_offers
            """, (batch_id, branch_code))
            comp_avg, student_count_with_ctc = cur.fetchone()

        # Calculate percentage differences
        placed_diff_pct = None
        if off_placed and off_placed > 0:
            placed_diff_pct = round(abs(comp_placed - off_placed) / off_placed * 100, 2)

        avg_diff_pct = None
        if off_avg and off_avg > 0 and comp_avg:
            avg_diff_pct = round(abs(comp_avg - off_avg) / off_avg * 100, 2)

        max_diff_pct = None
        if off_max and off_max > 0 and comp_max:
            max_diff_pct = round(abs(comp_max - off_max) / off_max * 100, 2)

        res = {
            "batch_id": batch_id,
            "branch": branch_code,
            "disc": disc,
            "off_placed": off_placed,
            "comp_placed": comp_placed,
            "placed_diff%": placed_diff_pct,
            "off_avg": off_avg,
            "comp_avg": comp_avg,
            "avg_diff%": avg_diff_pct,
            "off_max": off_max,
            "comp_max": comp_max,
            "max_diff%": max_diff_pct
        }
        results.append(res)

        # Flag > 5% mismatch
        reasons = []
        if placed_diff_pct is not None and placed_diff_pct > 5.0:
            reasons.append(f"Placed mismatch {placed_diff_pct}% (Official={off_placed}, Computed={comp_placed})")
        if avg_diff_pct is not None and avg_diff_pct > 5.0:
            reasons.append(f"Avg CTC mismatch {avg_diff_pct}% (Official={off_avg}, Computed={comp_avg})")
        if max_diff_pct is not None and max_diff_pct > 5.0:
            reasons.append(f"Max CTC mismatch {max_diff_pct}% (Official={off_max}, Computed={comp_max})")

        if reasons:
            large_mismatches.append((batch_id, branch_code, disc, reasons))

    conn.close()

    print("\n" + "=" * 90)
    print("RECONCILIATION SUMMARY: OFFICIAL COUNT WISE DETAILS VS COMPUTED RAW OFFERS")
    print("=" * 90)
    df = pd.DataFrame(results)
    print(df.to_string(index=False))

    print("\n" + "=" * 90)
    print(f"MISMATCHES EXCEEDING 5% THRESHOLD ({len(large_mismatches)} instances found)")
    print("=" * 90)
    for batch_id, branch_code, disc, reasons in large_mismatches:
        print(f"\n[{batch_id} | {branch_code} ({disc})]:")
        for r in reasons:
            print(f"  * {r}")
        # Diagnosis/likely causes
        causes = []
        if "Placed mismatch" in str(reasons):
            causes.append("Individual student sheets include off-campus offers added later or students who opted out before sheet finalization.")
        if "Avg CTC mismatch" in str(reasons):
            causes.append("Official sheet computed average over all offer rows or included/excluded undisclosed packages/PPOs, whereas canonical definition uses highest FTE/PPO CTC per placed student.")
        if "Max CTC mismatch" in str(reasons):
            causes.append("Difference between raw package text parser and frozen summary (e.g. international offer converted at different rate, or later unverified company).")
        print("  Likely Causes:")
        for c in causes:
            print(f"    - {c}")

if __name__ == "__main__":
    reconcile()

