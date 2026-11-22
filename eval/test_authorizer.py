import sqlite3

conn = sqlite3.connect('data/nitj_placement.db')

def authorizer(action_code, arg1, arg2, db_name, trigger_name):
    # Action codes:
    # SQLITE_READ = 20
    # SQLITE_SELECT = 21
    # SQLITE_INSERT = 18
    # SQLITE_UPDATE = 23
    # SQLITE_DELETE = 9
    
    # Deny all writes / DDL
    write_actions = {
        sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_VINDEX,
        sqlite3.SQLITE_CREATE_VIEW, sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_VINDEX,
        sqlite3.SQLITE_DROP_VIEW, sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH
    }
    if action_code in write_actions:
        return sqlite3.SQLITE_DENY
        
    if action_code == sqlite3.SQLITE_READ:
        # arg1 is table name, arg2 is column name
        table = (arg1 or "").lower()
        col = (arg2 or "").lower()
        if table == "student_private_pii":
            if col in ("roll_number", "personal_email", "phone_number"):
                return sqlite3.SQLITE_DENY
            # What if someone directly queries student_private_pii?
        if table == "students" and col in ("roll_no", "email", "phone"):
            return sqlite3.SQLITE_DENY

    return sqlite3.SQLITE_OK

conn.set_authorizer(authorizer)
print("Authorizer configured successfully")

