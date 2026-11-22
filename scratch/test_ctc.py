import sqlite3

def get_ctc_breakdown(company, bcode=None, batch_id=None):
    conn = sqlite3.connect('data/nitj_placement.db')
    cur = conn.cursor()

    b_cond = f"AND b.short_name = '{bcode}'" if bcode else ""
    cohort_cond = f"AND s.batch_id = '{batch_id}'" if batch_id else ""
    
    cur.execute(f"""
        SELECT s.batch_id, o.ctc_lpa, COUNT(DISTINCT s.student_id), GROUP_CONCAT(DISTINCT b.short_name)
        FROM offers o
        JOIN students s ON o.student_id = s.student_id
        JOIN branches b ON s.branch_code = b.branch_code
        JOIN companies c ON o.company_id = c.company_id
        WHERE c.canonical_name = '{company}' AND o.ctc_lpa IS NOT NULL {b_cond} {cohort_cond}
        GROUP BY s.batch_id, o.ctc_lpa
        ORDER BY s.batch_id ASC, o.ctc_lpa DESC
    """)
    fte_rows = cur.fetchall()

    b_join = "JOIN branches b ON s.branch_code = b.branch_code" if bcode else ""
    cur.execute(f"""
        SELECT s.batch_id, COUNT(o.offer_id)
        FROM offers o
        JOIN students s ON o.student_id = s.student_id
        JOIN companies c ON o.company_id = c.company_id
        {b_join}
        WHERE c.canonical_name = '{company}'
          AND (o.offer_type IN ('Intern', 'Summer Intern', 'Long Intern') OR (o.stipend_monthly_inr IS NOT NULL AND o.ctc_lpa IS NULL))
          {b_cond} {cohort_cond}
        GROUP BY s.batch_id
    """)
    intern_dict = dict(cur.fetchall())
    
    by_batch = {}
    for bid, ctc, count, branches in fte_rows:
        if bid not in by_batch:
            by_batch[bid] = []
        by_batch[bid].append((ctc, count, branches))

    parts = []
    all_batches = sorted(set(list(by_batch.keys()) + list(intern_dict.keys())))
    for bid in all_batches:
        fte_items = by_batch.get(bid, [])
        interns = intern_dict.get(bid, 0)
        
        # Use short batch format like 2021-25 or 2021-2025
        short_batch = bid.replace("2020-2024", "2020-24").replace("2021-2025", "2021-25").replace("2022-2026", "2022-26").replace("2023-2027", "2023-27")
        if fte_items:
            pkg_strs = [f"{cnt} full-time hire{'s' if cnt > 1 else ''} at {c:g} LPA" for c, cnt, br in fte_items]
            sub = f"{short_batch} had {', '.join(pkg_strs)}"
            if interns > 0:
                sub += f", plus {interns} summer-intern offer{'s' if interns > 1 else ''}"
            parts.append(sub)
        elif interns > 0:
            parts.append(f"{short_batch} had {interns} summer-intern offer{'s' if interns > 1 else ''}")

    conn.close()
    b_str = f" in {bcode}" if bcode else ""
    if not parts:
        return f"For {company}{b_str}, no package details were found."
    return f"For {company}{b_str}, " + ". ".join(parts) + "."

if __name__ == "__main__":
    print("Microsoft:")
    print(get_ctc_breakdown("Microsoft"))
    print("\nMicrosoft (CSE):")
    print(get_ctc_breakdown("Microsoft", "CSE"))
    print("\nGoogle:")
    print(get_ctc_breakdown("Google"))

