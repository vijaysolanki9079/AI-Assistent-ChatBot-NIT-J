import sys
import os
sys.path.insert(0, os.path.abspath("."))
import sqlite3
import re

DB_PATH = "data/nitj_placement.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1. Add columns to interview_experiences if not present
cur.execute("PRAGMA table_info(interview_experiences)")
cols = [c[1] for c in cur.fetchall()]
print("Current columns in interview_experiences:", cols)

if "company_id" not in cols:
    cur.execute("ALTER TABLE interview_experiences ADD COLUMN company_id INTEGER REFERENCES companies(company_id)")
    print("Added column company_id")
if "branch_code" not in cols:
    cur.execute("ALTER TABLE interview_experiences ADD COLUMN branch_code TEXT REFERENCES branches(branch_code)")
    print("Added column branch_code")
if "batch_id" not in cols:
    cur.execute("ALTER TABLE interview_experiences ADD COLUMN batch_id TEXT REFERENCES batches(batch_id)")
    print("Added column batch_id")
conn.commit()

# 2. Build canonical company lookup map
cur.execute("SELECT company_id, canonical_name FROM companies")
company_canonical = {cname.lower().strip(): cid for cid, cname in cur.fetchall()}

cur.execute("SELECT alias, company_id FROM company_aliases")
company_aliases = {alias.lower().strip(): cid for alias, cid in cur.fetchall()}

def resolve_company(name_str):
    if not name_str: return None
    clean = name_str.lower().strip()
    if clean in company_canonical:
        return company_canonical[clean]
    if clean in company_aliases:
        return company_aliases[clean]
    # Check normalized strip punctuation
    norm = re.sub(r'[^a-z0-9]', '', clean)
    for cname, cid in company_canonical.items():
        if re.sub(r'[^a-z0-9]', '', cname) == norm:
            return cid
    for alias, cid in company_aliases.items():
        if re.sub(r'[^a-z0-9]', '', alias) == norm:
            return cid
    return None

# 3. Build canonical branch lookup map
cur.execute("SELECT branch_code, canonical_name, short_name FROM branches")
branches_data = cur.fetchall()
branch_lookup = {}
for bcode, bcanon, bshort in branches_data:
    branch_lookup[bcode.lower().strip()] = bcode
    branch_lookup[bcanon.lower().strip()] = bcode
    branch_lookup[bshort.lower().strip()] = bcode

cur.execute("SELECT alias, branch_code FROM branch_aliases")
for alias, bcode in cur.fetchall():
    branch_lookup[alias.lower().strip()] = bcode

# Common alias variants in interview experiences
branch_lookup["cs"] = "103"
branch_lookup["computer science"] = "103"
branch_lookup["information technology"] = "107"
branch_lookup["it"] = "107"
branch_lookup["ece"] = "105"
branch_lookup["ee"] = "104"
branch_lookup["me"] = "108"
branch_lookup["ice"] = "106"
branch_lookup["che"] = "102"
branch_lookup["ce"] = "101"
branch_lookup["ipe"] = "109"
branch_lookup["bt"] = "111"
branch_lookup["tt"] = "110"

def resolve_branch(b_str, text_str=""):
    if b_str:
        clean = b_str.lower().strip()
        if clean in branch_lookup:
            return branch_lookup[clean]
    # Attempt backfill from full_text or title if branch is null/missing
    combined = (str(b_str or '') + " " + str(text_str or '')).lower()
    for pattern, code in [
        (r'\b(cse|computer science)\b', '103'),
        (r'\b(information technology)\b', '107'),
        (r'\b(ece|electronics and communication)\b', '105'),
        (r'\b(electrical engineering)\b', '104'),
        (r'\b(mechanical engineering)\b', '108'),
        (r'\b(ice|instrumentation and control)\b', '106'),
        (r'\b(chemical engineering)\b', '102'),
        (r'\b(civil engineering)\b', '101'),
        (r'\b(industrial and production)\b', '109'),
        (r'\b(biotechnology)\b', '111'),
        (r'\b(textile technology)\b', '110'),
    ]:
        if re.search(pattern, combined):
            return code
    return None

# 4. Build canonical batch lookup
cur.execute("SELECT batch_id FROM batches")
valid_batches = set(b[0] for b in cur.fetchall())

def resolve_batch(bat_str, text_str=""):
    if bat_str:
        clean = bat_str.strip()
        if clean in valid_batches:
            return clean
        # Match e.g. 2021-25 -> 2021-2025
        m = re.search(r'(20\d\d)[-_/](20\d\d)', clean)
        if m:
            full = f"{m.group(1)}-{m.group(2)}"
            if full in valid_batches: return full
        m2 = re.search(r'(20\d\d)[-_/](\d\d)', clean)
        if m2:
            full = f"{m2.group(1)}-20{m2.group(2)}"
            if full in valid_batches: return full
    
    # Try backfilling from text
    combined = (str(bat_str or '') + " " + str(text_str or ''))
    m3 = re.search(r'\b(202\d[-_/]202\d)\b', combined)
    if m3:
        cand = m3.group(1).replace('_', '-').replace('/', '-')
        if cand in valid_batches: return cand
    m4 = re.search(r'\b(202\d[-_/]2\d)\b', combined)
    if m4:
        parts = re.split(r'[-_/]', m4.group(1))
        cand = f"{parts[0]}-20{parts[1]}"
        if cand in valid_batches: return cand
    return None

# 5. Process all 409 rows in interview_experiences
cur.execute("SELECT experience_id, company_name, branch, batch, title, full_text, author FROM interview_experiences")
all_exps = cur.fetchall()
print(f"\nProcessing {len(all_exps)} interview experiences...")

linked_companies = 0
unlinked_companies = []
linked_branches = 0
unlinked_branches = []
linked_batches = 0
unlinked_batches = []

updates = []

for exp_id, cname, br, bat, title, ftext, author in all_exps:
    cid = resolve_company(cname)
    if cid:
        linked_companies += 1
    else:
        unlinked_companies.append((exp_id, cname))
        
    bcode = resolve_branch(br, f"{title} {ftext}")
    if bcode:
        linked_branches += 1
    else:
        unlinked_branches.append((exp_id, author, cname, br))
        
    bid = resolve_batch(bat, f"{title} {ftext}")
    if bid:
        linked_batches += 1
    else:
        unlinked_batches.append((exp_id, author, cname, bat))
        
    updates.append((cid, bcode, bid, exp_id))

cur.executemany("""
    UPDATE interview_experiences
    SET company_id = ?, branch_code = ?, batch_id = ?
    WHERE experience_id = ?
""", updates)
conn.commit()

print(f"\nResults of canonical linking:")
print(f"Company ID linked: {linked_companies} / {len(all_exps)} ({len(unlinked_companies)} unlinked)")
print(f"Branch Code linked: {linked_branches} / {len(all_exps)} ({len(unlinked_branches)} unlinked)")
print(f"Batch ID linked: {linked_batches} / {len(all_exps)} ({len(unlinked_batches)} unlinked)")

# Specific check for IndiaMart rows
cur.execute("SELECT author, company_name, company_id, branch, branch_code, batch, batch_id FROM interview_experiences WHERE company_name LIKE '%IndiaMart%'")
print("\nIndiaMART rows after linking:")
for r in cur.fetchall():
    print(r)

conn.close()

