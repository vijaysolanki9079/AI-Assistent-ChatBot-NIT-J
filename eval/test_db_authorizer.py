import sqlite3
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data.db_authorizer import get_readonly_connection

def test_readonly_and_privacy():
    conn = get_readonly_connection("data/nitj_placement.db")
    
    # 1. Standard analytical read must succeed
    cur = conn.cursor()
    cur.execute("SELECT company, ctc_lpa FROM v_offers_flat LIMIT 5")
    rows = cur.fetchall()
    assert len(rows) == 5, "Expected 5 rows from v_offers_flat"
    print("Test 1 Passed: v_offers_flat query succeeded")
    
    # 2. Public view read must succeed
    cur.execute("SELECT student_name, branch, batch, company FROM v_selected_students_public LIMIT 5")
    rows = cur.fetchall()
    assert len(rows) == 5, "Expected 5 rows from v_selected_students_public"
    print("Test 2 Passed: v_selected_students_public query succeeded")
    
    # 3. Batch aliases read must succeed
    cur.execute("SELECT batch_id FROM batch_aliases WHERE alias = '25'''")
    assert cur.fetchone()[0] == '2021-2025'
    print("Test 3 Passed: batch_aliases query succeeded")
    
    # 4. Direct read from student_private_pii MUST be denied
    try:
        cur.execute("SELECT * FROM student_private_pii")
        cur.fetchall()
        assert False, "Direct read from student_private_pii should have failed!"
    except sqlite3.DatabaseError as e:
        print("Test 4 Passed: Direct PII access was blocked:", e)
        
    # 5. Direct read of roll_number column MUST be denied
    try:
        cur.execute("SELECT roll_number FROM student_private_pii")
        cur.fetchall()
        assert False, "roll_number query should have failed!"
    except sqlite3.DatabaseError as e:
        print("Test 5 Passed: roll_number column access was blocked:", e)
        
    # 6. Any INSERT operation MUST be denied
    try:
        cur.execute("INSERT INTO batches (batch_id) VALUES ('2099-2103')")
        assert False, "INSERT should have failed!"
    except sqlite3.DatabaseError as e:
        print("Test 6 Passed: INSERT was blocked:", e)
        
    # 7. Any UPDATE operation MUST be denied
    try:
        cur.execute("UPDATE companies SET canonical_name = 'Hacked' WHERE company_id = 1")
        assert False, "UPDATE should have failed!"
    except sqlite3.DatabaseError as e:
        print("Test 7 Passed: UPDATE was blocked:", e)
        
    # 8. Any DROP operation MUST be denied
    try:
        cur.execute("DROP TABLE companies")
        assert False, "DROP TABLE should have failed!"
    except sqlite3.DatabaseError as e:
        print("Test 8 Passed: DROP was blocked:", e)

    print("\nALL AUTHORIZER SECURITY TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_readonly_and_privacy()
