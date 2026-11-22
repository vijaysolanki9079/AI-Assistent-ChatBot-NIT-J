import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

os.makedirs('scratch/diagrams', exist_ok=True)

# -------------------------------------------------------------------------
# Diagram 1: High-Level System Architecture
# -------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 7.5), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')

# Background
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

# Title
ax.text(50, 96, "NIT Jalandhar Intelligent Placement Assistant - System Architecture", 
        color='#ffffff', fontsize=16, fontweight='bold', ha='center', va='center')
ax.text(50, 92, "Enterprise 4-Tier Architecture with Strict Grounding & Zero-Hallucination Guarantees", 
        color='#8b949e', fontsize=10, ha='center', va='center')

# Tier 1: Client
rect_client = patches.FancyBboxPatch((4, 68), 92, 19, boxstyle="round,pad=1.5,rounding_size=2", 
                                     facecolor='#161b22', edgecolor='#3b82f6', linewidth=1.8)
ax.add_patch(rect_client)
ax.text(6, 84, "TIER 1: FRONTEND PRESENTATION LAYER (React 18 + Vite + Tailwind CSS)", 
        color='#60a5fa', fontsize=11, fontweight='bold', va='center')

client_boxes = [
    ("Chat Interface (App.jsx)\nFluid Liquid UI / Dark Theme", 7, 70, 26, 11),
    ("Progressive Typewriter\nStreaming Engine (StrictAnswerView)", 36, 70, 27, 11),
    ("Fault-Tolerant React\nError Boundary Wrapper", 66, 70, 28, 11)
]
for title, x, y, w, h in client_boxes:
    box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8,rounding_size=1", 
                                facecolor='#1f2937', edgecolor='#4b5563', linewidth=1)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, title, color='#e5e7eb', fontsize=8.5, ha='center', va='center')

# Arrow Tier 1 -> Tier 2
ax.annotate("", xy=(50, 61), xytext=(50, 68), 
            arrowprops=dict(arrowstyle="->", color='#38bdf8', lw=2))
ax.text(52, 64.5, "HTTP REST / JSON (POST /api/chat, GET /api/stats)", color='#38bdf8', fontsize=8.5, fontweight='bold')

# Tier 2: Backend
rect_api = patches.FancyBboxPatch((4, 42), 92, 19, boxstyle="round,pad=1.5,rounding_size=2", 
                                  facecolor='#161b22', edgecolor='#8b5cf6', linewidth=1.8)
ax.add_patch(rect_api)
ax.text(6, 58, "TIER 2: BACKEND API & ORCHESTRATION LAYER (Node.js + Express.js)", 
        color='#c084fc', fontsize=11, fontweight='bold', va='center')

api_boxes = [
    ("Session Dialog Store\nMulti-turn context memory", 7, 44, 26, 11),
    ("Deliberation Engine\nMinimum 350ms thinking buffer", 36, 44, 27, 11),
    ("Audit Logger & Bridge\nChild-process spawn to Python", 66, 44, 28, 11)
]
for title, x, y, w, h in api_boxes:
    box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8,rounding_size=1", 
                                facecolor='#1f2937', edgecolor='#4b5563', linewidth=1)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, title, color='#e5e7eb', fontsize=8.5, ha='center', va='center')

# Arrow Tier 2 -> Tier 3
ax.annotate("", xy=(50, 35), xytext=(50, 42), 
            arrowprops=dict(arrowstyle="->", color='#c084fc', lw=2))
ax.text(52, 38.5, "Stdio IPC / Process Pipe (src/api/runner.py)", color='#c084fc', fontsize=8.5, fontweight='bold')

# Tier 3: Agent Layer
rect_agent = patches.FancyBboxPatch((4, 16), 92, 19, boxstyle="round,pad=1.5,rounding_size=2", 
                                    facecolor='#161b22', edgecolor='#10b981', linewidth=1.8)
ax.add_patch(rect_agent)
ax.text(6, 32, "TIER 3: INTELLIGENT AGENT & VERIFICATION LAYER (Python 3.13 Runtime)", 
        color='#34d399', fontsize=11, fontweight='bold', va='center')

agent_boxes = [
    ("Privacy & Scope Shields\nRegex blocks PII/Injections", 7, 18, 20, 11),
    ("Entity Resolver\nSQLite alias & fuzzy matcher", 29, 18, 20, 11),
    ("Tool Router & Synthesizer\nAnalytical SQL / FTS5 RAG", 51, 18, 22, 11),
    ("OutputVerifier Audit\nZero-hallucination check", 75, 18, 19, 11)
]
for title, x, y, w, h in agent_boxes:
    box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8,rounding_size=1", 
                                facecolor='#1f2937', edgecolor='#4b5563', linewidth=1)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, title, color='#e5e7eb', fontsize=8, ha='center', va='center')

# Arrow Tier 3 -> Tier 4
ax.annotate("", xy=(50, 9), xytext=(50, 16), 
            arrowprops=dict(arrowstyle="->", color='#34d399', lw=2))
ax.text(52, 12.5, "Hardware Authorizer Callback (PRAGMA query_only=ON)", color='#34d399', fontsize=8.5, fontweight='bold')

# Tier 4: Database Layer
rect_db = patches.FancyBboxPatch((4, 1), 92, 8, boxstyle="round,pad=1.5,rounding_size=2", 
                                 facecolor='#161b22', edgecolor='#f59e0b', linewidth=1.8)
ax.add_patch(rect_db)
ax.text(50, 5, "TIER 4: SECURE DATA LAYER (SQLite3: data/nitj_placement.db) • 2,929 Verified Offers • 409 Alumni Experiences", 
        color='#fbbf24', fontsize=10.5, fontweight='bold', ha='center', va='center')

plt.tight_layout()
plt.savefig("scratch/diagrams/architecture_diagram.png", dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()
print("Saved architecture_diagram.png")

# -------------------------------------------------------------------------
# Diagram 2: Step-by-Step Request Lifecycle Flowchart
# -------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 10), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

ax.text(50, 97, "NITJ Placement Assistant - Request Lifecycle Flowchart", 
        color='#ffffff', fontsize=16, fontweight='bold', ha='center', va='center')
ax.text(50, 94, "From User Message Arrival to Verified Progressive Typewriter Response", 
        color='#8b949e', fontsize=10, ha='center', va='center')

steps = [
    (1, "1. User Query Submitted", "React frontend captures input and sends JSON POST to /api/chat", 86, '#3b82f6'),
    (2, "2. Express Orchestrator", "Session ID mapped, conversational history passed, deliberation timer started", 76, '#8b5cf6'),
    (3, "3. Privacy Guard Check", "Regex filter inspects for roll numbers, phones, emails, DROP TABLE, admin escalation", 66, '#ef4444'),
    (4, "4. Scope Validation", "Checks for jokes, out-of-scope non-NITJ institutes, and future package projections", 56, '#f59e0b'),
    (5, "5. Entity Resolution", "Tokenizes query against SQLite alias tables (company_aliases, branch_aliases, batch_aliases)", 46, '#10b981'),
    (6, "6. Dual-Engine Dispatch", "Quantitative questions route to SQL Generator; qualitative prep queries route to FTS5 RAG", 36, '#06b6d4'),
    (7, "7. Analytical DB Execution", "Queries execute over clean views (v_offers_flat) enforced by read-only authorizer", 26, '#3b82f6'),
    (8, "8. OutputVerifier Audit", "Every drafted package, offer count, and average is checked against raw SQL rows", 16, '#10b981'),
    (9, "9. Progressive UI Reveal", "React typewriter streams words at 18ms per token with pulsing cursor & clean tables", 6, '#a855f7')
]

for num, title, desc, y, color in steps:
    # Outer box
    box = patches.FancyBboxPatch((12, y-3.5), 76, 7, boxstyle="round,pad=0.8,rounding_size=1", 
                                facecolor='#161b22', edgecolor=color, linewidth=1.5)
    ax.add_patch(box)
    
    # Step Number Circle
    circle = patches.Circle((7, y), 2.2, facecolor=color, edgecolor='#ffffff', linewidth=1)
    ax.add_patch(circle)
    ax.text(7, y, str(num), color='#ffffff', fontsize=10, fontweight='bold', ha='center', va='center')
    
    # Text
    ax.text(15, y+1.2, title, color='#ffffff', fontsize=10.5, fontweight='bold', va='center')
    ax.text(15, y-1.4, desc, color='#9ca3af', fontsize=8.2, va='center')
    
    # Arrow to next step
    if num < len(steps):
        ax.annotate("", xy=(50, y-3.5), xytext=(50, y-6.5), 
                    arrowprops=dict(arrowstyle="<-", color='#4b5563', lw=1.5))

plt.tight_layout()
plt.savefig("scratch/diagrams/request_flowchart.png", dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()
print("Saved request_flowchart.png")

# -------------------------------------------------------------------------
# Diagram 3: Security & Verification Dual-Shield Model
# -------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 6.5), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

ax.text(50, 94, "Security & Verification Dual-Shield Defense Model", 
        color='#ffffff', fontsize=16, fontweight='bold', ha='center', va='center')
ax.text(50, 89, "Hardware Enforcement at Storage Layer + Mathematical Audit at Narration Layer", 
        color='#8b949e', fontsize=10, ha='center', va='center')

# Left Shield: Privacy Guard
rect_left = patches.FancyBboxPatch((6, 12), 41, 70, boxstyle="round,pad=1.5,rounding_size=2", 
                                   facecolor='#161b22', edgecolor='#ef4444', linewidth=2)
ax.add_patch(rect_left)
ax.text(26.5, 76, "SHIELD 1: PRIVACY & ACCESS CONTROL", color='#f87171', fontsize=11, fontweight='bold', ha='center')

left_bullets = [
    ("Hardware-Level Query Authorizer", "SQLite set_authorizer rejects any read of table 'student_private_pii'."),
    ("Hardware Read-Only Sandbox", "Connection locks DB with 'PRAGMA query_only = ON'; DROP/UPDATE blocked."),
    ("Column-Level PII Denial", "Denied columns: roll_number, phone_number, personal_email, address."),
    ("Public View Anonymization", "v_selected_students_public exposes only student name, branch, batch, and company.")
]
curr_y = 66
for header, detail in left_bullets:
    ax.text(9, curr_y, f"• {header}:", color='#fca5a5', fontsize=9, fontweight='bold')
    ax.text(11, curr_y-4, detail, color='#d1d5db', fontsize=8, wrap=True)
    curr_y -= 13

# Right Shield: OutputVerifier
rect_right = patches.FancyBboxPatch((53, 12), 41, 70, boxstyle="round,pad=1.5,rounding_size=2", 
                                    facecolor='#161b22', edgecolor='#10b981', linewidth=2)
ax.add_patch(rect_right)
ax.text(73.5, 76, "SHIELD 2: ANTI-HALLUCINATION VERIFIER", color='#34d399', fontsize=11, fontweight='bold', ha='center')

right_bullets = [
    ("Mathematical Token Extraction", "Extracts every float and integer from the synthesized response draft."),
    ("SQL Ground-Truth Whitelist", "Allowed set = exact numbers returned in SQL result rows."),
    ("Prohibition on Aggregation Summing", "Strictly forbids summing max packages or averaging averages."),
    ("Automatic Safe-Fallback Recovery", "If an ungrounded number is detected, replaces text with exact verified table.")
]
curr_y = 66
for header, detail in right_bullets:
    ax.text(56, curr_y, f"• {header}:", color='#6ee7b7', fontsize=9, fontweight='bold')
    ax.text(58, curr_y-4, detail, color='#d1d5db', fontsize=8, wrap=True)
    curr_y -= 13

plt.tight_layout()
plt.savefig("scratch/diagrams/security_verification_model.png", dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()
print("Saved security_verification_model.png")

