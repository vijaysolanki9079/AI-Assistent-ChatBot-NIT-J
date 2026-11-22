import sqlite3

def run_profile_test():
    con = sqlite3.connect('data/nitj_placement.db')
    cur = con.cursor()
    bcode = '103'
    batches = ['2020-2024', '2021-2025', '2022-2026']
    
    rows = []
    tot_elig = 0
    tot_placed = 0
    tot_offers = 0
    
    for b in batches:
        cur.execute('SELECT eligible_students, placed_students, placement_pct FROM batch_branch_stats WHERE branch_code = ? AND batch_id = ?', (bcode, b))
        stat = cur.fetchone()
        elig = stat[0] if stat else 0
        placed = stat[1] if stat else 0
        pct = stat[2] if stat else 0.0
        
        cur.execute('''
        WITH student_highest AS (
            SELECT s.student_id, MAX(o.ctc_lpa) AS highest_ctc
            FROM students s
            JOIN offers o ON s.student_id = o.student_id
            WHERE s.branch_code = ? AND s.batch_id = ?
              AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
              AND o.ctc_lpa IS NOT NULL
            GROUP BY s.student_id
        )
        SELECT ROUND(AVG(highest_ctc), 2), MAX(highest_ctc) FROM student_highest
        ''', (bcode, b))
        pkg = cur.fetchone()
        avg_c = pkg[0] if pkg and pkg[0] else 0.0
        max_c = pkg[1] if pkg and pkg[1] else 0.0
        
        cur.execute('''
        SELECT COUNT(o.offer_id) FROM offers o
        JOIN students s ON o.student_id = s.student_id
        WHERE s.branch_code = ? AND s.batch_id = ?
          AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
        ''', (bcode, b))
        offers = cur.fetchone()[0]
        
        rows.append([b, elig, placed, f"{pct:.2f}%", f"{avg_c:.2f} LPA", f"{max_c:.2f} LPA", offers])
        tot_elig += elig
        tot_placed += placed
        tot_offers += offers

    tot_pct = round(tot_placed * 100.0 / tot_elig, 2) if tot_elig > 0 else 0.0
    
    # Overall pkg
    cur.execute('''
    WITH student_highest AS (
        SELECT s.student_id, MAX(o.ctc_lpa) AS highest_ctc
        FROM students s
        JOIN offers o ON s.student_id = o.student_id
        WHERE s.branch_code = ? AND s.batch_id IN ('2020-2024', '2021-2025', '2022-2026')
          AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
          AND o.ctc_lpa IS NOT NULL
        GROUP BY s.student_id
    ),
    ordered AS (
        SELECT highest_ctc,
               ROW_NUMBER() OVER (ORDER BY highest_ctc) AS r,
               COUNT(*) OVER () AS c
        FROM student_highest
    )
    SELECT 
        ROUND(AVG(sh.highest_ctc), 2),
        (SELECT ROUND(AVG(highest_ctc), 2) FROM ordered WHERE r IN ((c + 1) / 2, (c + 2) / 2)),
        MAX(sh.highest_ctc),
        COUNT(*)
    FROM student_highest sh
    ''', (bcode,))
    ov_pkg = cur.fetchone()
    
    # Excluded
    cur.execute('''
    SELECT COUNT(o.offer_id) FROM offers o
    JOIN students s ON o.student_id = s.student_id
    WHERE s.branch_code = ? AND s.batch_id IN ('2020-2024', '2021-2025', '2022-2026')
      AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
      AND o.ctc_lpa IS NULL
    ''', (bcode,))
    excluded_cnt = cur.fetchone()[0]
    
    # Top 5 recruiters
    cur.execute('''
    SELECT c.canonical_name, COUNT(o.offer_id) AS cnt
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN companies c ON o.company_id = c.company_id
    WHERE s.branch_code = ? AND s.batch_id IN ('2020-2024', '2021-2025', '2022-2026')
      AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
    GROUP BY c.canonical_name
    ORDER BY cnt DESC, c.canonical_name ASC
    LIMIT 5
    ''', (bcode,))
    top5 = cur.fetchall()
    
    # Sector split
    cur.execute('''
    SELECT 
      CASE WHEN c.sector = 'IT' THEN 'IT / Software'
           WHEN c.sector = 'Core' THEN 'Core Engineering'
           ELSE 'Consulting / Non-Core' END AS sec,
      COUNT(o.offer_id)
    FROM offers o
    JOIN students s ON o.student_id = s.student_id
    JOIN companies c ON o.company_id = c.company_id
    WHERE s.branch_code = ? AND s.batch_id IN ('2020-2024', '2021-2025', '2022-2026')
      AND o.offer_type IN ('FTE', 'PPO', 'Intern+PPO', 'Intern+FTE')
    GROUP BY sec
    ORDER BY COUNT(o.offer_id) DESC
    ''', (bcode,))
    sectors = cur.fetchall()
    
    con.close()
    
    # Build markdown table
    header = '| Academic Batch | Eligible Students | Placed Students | Placement Rate | Average CTC | Peak CTC | Total Offers |'
    sep = '|---|---|---|---|---|---|---|'
    data_lines = ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    tot_line = f'| **Total / Overall** | **{tot_elig}** | **{tot_placed}** | **{tot_pct}%** | **{ov_pkg[0]} LPA** | **{ov_pkg[2]} LPA** | **{tot_offers}** |'
    table_md = '\n'.join([header, sep] + data_lines + [tot_line])
    
    top_strs = [f"{c} ({cnt})" for c, cnt in top5]
    sec_strs = [f"{s}: {cnt}" for s, cnt in sectors]
    top_list_str = ", ".join(top_strs[:3])
    sec_list_str = ", ".join(sec_strs)
    
    summary = (
        f"Across all batches 2020-24 to 2022-26, full-time offers only.\n\n"
        f"Computer Science & Engineering recorded an overall placement percentage of **{tot_pct}%** "
        f"with **{tot_placed}** students placed out of {tot_elig} eligible candidates, securing **{tot_offers}** total offers.\n"
        f"The overall average package is **{ov_pkg[0]} LPA** (median **{ov_pkg[1]} LPA**, highest **{ov_pkg[2]} LPA** across {ov_pkg[3]} placed students; {excluded_cnt} offers excluded for unparseable/undisclosed CTC).\n"
        f"Top recruiters include **{top_list_str}**, with offer breakdown by sector: {sec_list_str}."
    )
    
    print('SUMMARY:\n', summary)
    print('\nTABLE:\n', table_md)

if __name__ == '__main__':
    run_profile_test()

