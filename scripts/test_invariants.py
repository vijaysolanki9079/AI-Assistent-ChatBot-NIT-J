"""
NIT Jalandhar Placement Database Invariant Test Suite
Validates that across all combinations of company x branch x batch,
the count path and the list/aggregate path strictly agree.
"""

import sys
import os
import sqlite3
import json

DB_PATH = "data/nitj_placement.db"

def run_invariant_tests():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=" * 60)
    print("RUNNING INVARIANT TESTS (Count vs List / Aggregate paths)")
    print("=" * 60)

    # 1. Test Invariant 1: For every (company_id, branch_code, batch_id) combination,
    # COUNT(DISTINCT student_id) MUST equal len(DISTINCT student_id) from list/aggregate query.
    cur.execute("""
        SELECT DISTINCT o.company_id, s.branch_code, s.batch_id
        FROM offers o
        JOIN students s ON o.student_id = s.student_id
        WHERE o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
    """)
    combos = cur.fetchall()
    print(f"Checking {len(combos)} distinct (company, branch, batch) tuples...")

    violations_cbb = []
    for cid, bcode, bid in combos:
        cur.execute("""
            SELECT COUNT(DISTINCT s.student_id)
            FROM offers o
            JOIN students s ON o.student_id = s.student_id
            WHERE o.company_id = ? AND s.branch_code = ? AND s.batch_id = ?
              AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
        """, (cid, bcode, bid))
        count_val = cur.fetchone()[0]

        cur.execute("""
            SELECT DISTINCT s.student_id
            FROM offers o
            JOIN students s ON o.student_id = s.student_id
            WHERE o.company_id = ? AND s.branch_code = ? AND s.batch_id = ?
              AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
        """, (cid, bcode, bid))
        list_rows = cur.fetchall()
        list_val = len(list_rows)

        if count_val != list_val:
            violations_cbb.append({
                "company_id": cid,
                "branch_code": bcode,
                "batch_id": bid,
                "count_val": count_val,
                "list_val": list_val
            })

    print(f"Invariant 1 (Company x Branch x Batch): {len(combos) - len(violations_cbb)}/{len(combos)} passed.")
    if violations_cbb:
        print(f"VIOLATIONS FOUND in Invariant 1 ({len(violations_cbb)}):")
        for v in violations_cbb[:10]:
            print(f"  - Company {v['company_id']}, Branch {v['branch_code']}, Batch {v['batch_id']}: Count={v['count_val']} vs List={v['list_val']}")
    else:
        print("-> 100% agreement: Count path == List path for every (company, branch, batch) tuple.")

    # 2. Test Invariant 2: For every company, total placed count == sum of branch breakdown counts
    cur.execute("""
        SELECT DISTINCT company_id FROM offers
        WHERE offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
    """)
    companies = [r[0] for r in cur.fetchall()]
    print(f"\nChecking Invariant 2 (Company total vs Sum of branch breakdowns) across {len(companies)} companies...")

    violations_comp = []
    for cid in companies:
        cur.execute("""
            SELECT COUNT(DISTINCT s.student_id)
            FROM offers o
            JOIN students s ON o.student_id = s.student_id
            WHERE o.company_id = ?
              AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
        """, (cid,))
        tot_count = cur.fetchone()[0]

        cur.execute("""
            SELECT s.branch_code, COUNT(DISTINCT s.student_id)
            FROM offers o
            JOIN students s ON o.student_id = s.student_id
            WHERE o.company_id = ?
              AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
            GROUP BY s.branch_code
        """, (cid,))
        breakdown_rows = cur.fetchall()
        sum_breakdown = sum(r[1] for r in breakdown_rows)

        # Note: In SQLite, student has exactly 1 branch_code, so sum(branch_breakdown) == total_distinct_students
        if tot_count != sum_breakdown:
            violations_comp.append({
                "company_id": cid,
                "total_count": tot_count,
                "sum_breakdown": sum_breakdown
            })

    print(f"Invariant 2 (Company breakdown sum): {len(companies) - len(violations_comp)}/{len(companies)} passed.")
    if violations_comp:
        print(f"VIOLATIONS FOUND in Invariant 2 ({len(violations_comp)}):")
        for v in violations_comp[:10]:
            print(f"  - Company {v['company_id']}: Total={v['total_count']} vs Sum={v['sum_breakdown']}")
    else:
        print("-> 100% agreement: Total company placed == Sum of branch breakdown counts.")

    # 3. Test Invariant 3: For every branch, total placed count == sum of batch breakdown counts
    cur.execute("SELECT branch_code FROM branches")
    branches = [r[0] for r in cur.fetchall()]
    print(f"\nChecking Invariant 3 (Branch total vs Sum of batch breakdowns) across {len(branches)} branches...")

    violations_branch = []
    for bcode in branches:
        cur.execute("""
            SELECT COUNT(DISTINCT s.student_id)
            FROM offers o
            JOIN students s ON o.student_id = s.student_id
            WHERE s.branch_code = ?
              AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
        """, (bcode,))
        tot_count = cur.fetchone()[0]

        cur.execute("""
            SELECT s.batch_id, COUNT(DISTINCT s.student_id)
            FROM offers o
            JOIN students s ON o.student_id = s.student_id
            WHERE s.branch_code = ?
              AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
            GROUP BY s.batch_id
        """, (bcode,))
        breakdown_rows = cur.fetchall()
        sum_breakdown = sum(r[1] for r in breakdown_rows)

        if tot_count != sum_breakdown:
            violations_branch.append({
                "branch_code": bcode,
                "total_count": tot_count,
                "sum_breakdown": sum_breakdown
            })

    print(f"Invariant 3 (Branch breakdown sum): {len(branches) - len(violations_branch)}/{len(branches)} passed.")
    if violations_branch:
        print(f"VIOLATIONS FOUND in Invariant 3 ({len(violations_branch)}):")
        for v in violations_branch[:10]:
            print(f"  - Branch {v['branch_code']}: Total={v['total_count']} vs Sum={v['sum_breakdown']}")
    else:
        print("-> 100% agreement: Total branch placed == Sum of batch breakdown counts.")

    conn.close()

    total_violations = len(violations_cbb) + len(violations_comp) + len(violations_branch)
    print("\n" + "=" * 60)
    print(f"INVARIANT AUDIT RESULT: {total_violations} TOTAL VIOLATIONS")
    print("=" * 60)
    return total_violations == 0

if __name__ == "__main__":
    success = run_invariant_tests()
    sys.exit(0 if success else 1)

