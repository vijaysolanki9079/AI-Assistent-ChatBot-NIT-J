import sqlite3
import os

WRITE_ACTIONS = {
    sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
    sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_INDEX,
    sqlite3.SQLITE_CREATE_VIEW, sqlite3.SQLITE_CREATE_TRIGGER,
    sqlite3.SQLITE_CREATE_VTABLE,
    sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_INDEX,
    sqlite3.SQLITE_DROP_VIEW, sqlite3.SQLITE_DROP_TRIGGER,
    sqlite3.SQLITE_DROP_VTABLE,
    sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH
}

FORBIDDEN_COLUMNS = {
    "roll_no", "roll_number", "email", "personal_email", "phone", "phone_number"
}

def readonly_authorizer(action, arg1, arg2, db, trigger):
    """
    SQLite Authorizer enforcing strict read-only access and student privacy:
    - Denies all write, DDL, and attach/detach actions.
    - Denies direct queries against student_private_pii table (only allowed when expanded within v_selected_students_public).
    - Denies direct queries against private PII columns (roll numbers, emails, phone numbers).
    """
    if action in WRITE_ACTIONS:
        return sqlite3.SQLITE_DENY
        
    if action == sqlite3.SQLITE_READ:
        table = (arg1 or "").lower()
        col = (arg2 or "").lower()
        
        # Deny direct access to student_private_pii table
        if table == "student_private_pii" and trigger != "v_selected_students_public":
            return sqlite3.SQLITE_DENY
            
        # Deny access to sensitive PII columns anywhere
        if col in FORBIDDEN_COLUMNS:
            return sqlite3.SQLITE_DENY

    return sqlite3.SQLITE_OK

def get_readonly_connection(db_path: str = "data/nitj_placement.db") -> sqlite3.Connection:
    """
    Returns an open SQLite connection with query timeout and read-only authorizer installed.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")
        
    # Open URI in read-only mode if supported, or standard connection with authorizer
    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=10.0)
    except sqlite3.OperationalError:
        conn = sqlite3.connect(db_path, timeout=10.0)
        
    conn.set_authorizer(readonly_authorizer)
    return conn

