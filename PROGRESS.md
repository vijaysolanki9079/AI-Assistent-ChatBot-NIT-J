# NIT Jalandhar T&P Intelligent Assistant - Project Progress Tracker

## Overall Roadmap & Status

| Phase | Description | Status | Completion Date | Artifacts / Deliverables |
|---|---|---|---|---|
| **Phase 1** | **Data Audit** (Columns, duplicates, inconsistencies, unit problems, offer types) | **Completed** | 2026-11-16 | [data_quality_report.md](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/data_quality_report.md), [scripts/deep_audit.py](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/scripts/deep_audit.py) |
| **Phase 2** | **Cleaning + Schema + Semantic Layer** (`semantic_layer.yaml`, approval of metric definitions) | **Completed** | 2026-11-16 | [semantic_layer.yaml](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/semantic_layer.yaml), [data/nitj_placement.db](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/data/nitj_placement.db) |
| **Phase 3** | **Evaluation Set** (100+ hard questions, gold SQL, `eval/questions.json`, `eval/run_eval.py`) | **Completed** | 2026-11-16 | [eval/questions.json](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/eval/questions.json), [eval/run_eval.py](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/eval/run_eval.py), [eval/eval_report.md](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/eval/eval_report.md) |
| **Phase 4** | **Entity Resolution + Planner + Text-to-SQL + Verification** | **Completed** | 2026-11-16 | [src/nlp/query_planner.py](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/nlp/query_planner.py), [eval/eval_report.md](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/eval/eval_report.md) (100% eval score) |
| **Phase 5** | **Experience Extraction + pgvector RAG + Hybrid Path** | **Completed** | 2026-11-17 | [data/interview_experiences_structured.json](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/data/interview_experiences_structured.json), [src/rag/retriever.py](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/rag/retriever.py), [data/nitj_experiences_pgvector.sql](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/data/nitj_experiences_pgvector.sql) |
| **Phase 6** | **Router + Express Backend + Liquid React UI** (Strict answer format) | **Completed** | 2026-11-17 | [server/index.js](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/server/index.js), [client/src/App.jsx](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/client/src/App.jsx), [client/src/components/](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/client/src/components/) |
| **Phase 7** | **Caching, Logging, README & Final Deliverables** | **Completed** | 2026-11-17 | [README.md](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/README.md), [logs/query_audit.jsonl](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/logs/query_audit.jsonl), LRU Caching |

---

## Phase 1 Audit Summary

- **Total Rows Audited**: 9,385 student rows across 3 Excel workbooks:
  1. `2020-24 and 2022-24 Batch_Placement Database.xlsx` (17 data sheets + 3 summary sheets)
  2. `2021-25 and 2023-25 Batch_Placement Database.xlsx` (15 data sheets + 4 summary sheets)
  3. `2022-26 and 2024-26 Batch_Placement Database UG and PG.xlsx` (5 data sheets + 3 summary sheets)
- **Total Placement / Offer Rows**: 3,009 rows.
- **Unplaced / Internship Rosters**: 6,376 rows.
- **Data Quality Issues Cataloged**: 392 records logged in [data_quality_report.md](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/data_quality_report.md).
- **Core Insights**:
  1. Header and column structures vary across sheets (e.g. `Textile Technology` swapped cols 6 & 7; `B.Tech 2023-27` added PwD column and moved Branch to Col 2; `MBA` sheets lack category/gender).
  2. Batch must be derived from Roll No prefix (first 2 digits), NOT file name.
  3. Branch must be canonically derived from Roll No digits 3-5 (with 150 offer row conflicts flagged where students appear in different department sheets).
  4. Offer types span 53 raw status values, categorized into 7 canonical types: `FTE`, `PPO`, `Intern`, `Intern+PPO`, `Intern+FTE`, `Long Intern`, `Off-campus`.
  5. 475 non-numeric package values analyzed; 18 compound strings (`40K+12.8LPA`, `45K, 22 Lac`) split into `ctc_lpa` and `stipend_monthly_inr`.
  6. 113 status-in-date rows and 5 date typos identified.
  7. Cross-workbook overlap identified for `M.Tech 2023-25` (File 1 early snapshot vs File 2 updated snapshot).
  8. Privacy sheet `Copy of Full Details` (File 2) identified and marked for exclusion (contains HR names, phones, emails).
- **Files Modified**: None (Read-only data audit).



---

## Phase 2 Cleaning & Semantic Layer Summary

- **Cleaned Database Generated**: `data/nitj_placement.db` (SQLite relational DB with analytical views).
- **Canonical Schema**:
  - `batches`: 7 distinct academic cohorts (`2020-2024`, `2021-2025`, `2022-2026`, `2023-2027`, `2022-2024`, `2023-2025`, `2024-2026`).
  - `branches`: 17 academic programs with codes (`103` CSE, `124` IT, `104` ECE, etc.), divisions (`Circuit`, `Core`, `Sciences`, `Management`), and aliases.
  - `companies`: 487 canonical recruiting organizations with 543 alias mappings (e.g., `PayPal University Team` -> `PayPal`, `Nvida` -> `Nvidia`, `Accenutre` -> `Accenture`, `Intel India` -> `Intel`).
  - `students`: 5,470 unique individual student profiles with canonical branch codes, batches, categories, and conflict flags.
  - `offers`: 2,929 deduplicated offer records (2,534 full-time/PPO qualifying offers, 2,437 with verified CTC, 451 with monthly stipend).
- **Core Semantic Layer Specification**:
  - Created [`semantic_layer.yaml`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/semantic_layer.yaml) establishing immutable metric definitions, canonical SQL formulations, branch/company aliases, program divisions (`Circuit` vs `Core`), and verification sanity checks.
  - Strict distinction enforced between `placed_students` (`COUNT(DISTINCT student_id)`) and `total_offers` (`COUNT(offer_id)`).
  - Monthly stipend (`stipend_monthly_inr`) strictly separated from annual CTC (`ctc_lpa`).


---

## Phase 3 Evaluation Set Summary

- **Evaluation Benchmark Created**: [`eval/questions.json`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/eval/questions.json)
- **Total Test Cases**: **120 questions** covering all 12 specified categories (exactly 10 questions per type).
- **Tricky Edge Cases Included**:
  - Typo and spelling variants (`Micorsoft`, `Nvida`, `intle`).
  - Strict distinction between distinct placed students and total offer counts.
  - Negative queries identifying zero-hire branches (e.g. PayPal, Uber).
  - Offer-type segregation (Intern stipends in INR vs FTE packages in LPA).
  - Unanswerable cases: unrecorded attributes (CGPA, 10th/12th board marks), unvisited companies (Apple), relative dates ("yesterday"), and privacy-blocked inquiries.
- **Evaluation Harness**: [`eval/run_eval.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/eval/run_eval.py)
  - Baseline execution verified with 100% gold pass rate.

---

## Phase 4 Entity Resolution + Planner + Text-to-SQL + Verification Summary

- **Engine Architecture Implemented**:
  1. [`src/core/semantic_loader.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/core/semantic_loader.py): High-performance typed YAML loader for entity schemas, canonical SQL metric formulations, aliases, and sanity checks.
  2. [`src/nlp/entity_resolver.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/nlp/entity_resolver.py): Multi-stage resolution for companies, branches, and batches. Employs token-boundary matching, length-descending precedence (e.g. `Reliance Industries` over `Reliance`), and safe fuzzy ratio matching (cutoff 0.82) to handle real-world user typos (`Micorsoft`, `Nvida`) without false positives on ordinary placement terms.
  3. [`src/nlp/router.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/nlp/router.py): Multi-class intent classifier directing queries into `structured`, `hybrid`, `unstructured`, `ambiguous`, or `out_of_scope` (including proactive privacy blocking of HR/student contacts, unrecorded metric rejection, and cohort range validation).
  4. [`src/db/sql_engine.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/db/sql_engine.py): Safe read-only SQLite execution engine with read-only connection pragmas (`query_only=ON`), strict single-statement enforcement, execution timeout guards, and execution retry hooks.
  5. [`src/nlp/verifier.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/nlp/verifier.py): Post-execution safety and sanity verifier (boundary checks for percentages $\in [0, 100]$, plausible CTC checks, non-negativity, and caveat flagging).
  6. [`src/nlp/query_planner.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/nlp/query_planner.py): End-to-end query planner formulating semantic SQL, executing through the safe engine, verifying output, and rendering the strict 7-part answer format.
- **Evaluation Benchmark Results**:
  - **120 / 120 (100.0%) PASS RATE** across all 12 question categories in [`eval/questions.json`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/eval/questions.json).
  - Perfect scores in all 12 types: Lookups (10/10), Counts (10/10), Breakdowns (10/10), Ranking (10/10), Aggregates (10/10), Percentages (10/10), Trends (10/10), Multi-condition (10/10), Negative/Existence (10/10), Offer-type aware (10/10), Hybrid (10/10), and Unanswerable/Ambiguous (10/10).
  - Detailed report saved to [`eval/eval_report.md`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/eval/eval_report.md).

---

## Phase 5 Experience Extraction + pgvector RAG + Hybrid Path Summary

- **Alumni Experience Dataset Ingested**:
  - Source folder: `NIT-J data/company-experience/` (21 CSV files: 20 company-specific files + 1 `_unsorted.csv`, totaling 609 raw submissions).
  - Cleaned & filtered out low-content/placeholder entries to extract **409 substantive, high-value interview experiences**.
- **Structured Pydantic Extraction**:
  - Created [`src/rag/schema.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/rag/schema.py) defining strongly-typed `InterviewExperience` and `InterviewRound` models (round types: OA, Technical, Managerial, HR; technical topics: DSA, DBMS, OS, OOP, System Design, Core Subjects; key problem statements and preparation tips).
  - Built [`src/rag/extractor.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/rag/extractor.py) using fast entity resolution to link submissions to canonical companies (`Amazon`, `Google`, `Microsoft`, `Reliance Industries`, `HPCL`, `Infosys`, etc.).
  - Serialized verified structured dataset to [`data/interview_experiences_structured.json`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/data/interview_experiences_structured.json).
- **Dual Vector Storage & Full-Text Search**:
  1. **SQLite FTS5 + Metadata Store** ([`src/rag/db_indexer.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/rag/db_indexer.py)): Indexed all 409 experiences into `interview_experiences` and `interview_experiences_fts` inside [`data/nitj_placement.db`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/data/nitj_placement.db) with Porter stemming and BM25 ranking.
  2. **PostgreSQL + pgvector Migration** ([`scripts/export_pgvector.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/scripts/export_pgvector.py)): Generated production migration script [`data/nitj_experiences_pgvector.sql`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/data/nitj_experiences_pgvector.sql) creating `interview_experiences_pgvector` table with 128-dimensional vector embeddings and IVFFlat cosine similarity index.
- **Hybrid Retrieval & Answer Merging**:
  - Built [`src/rag/retriever.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/rag/retriever.py): Metadata-filtered search filtering by company list, branch, and role.
  - Connected Hybrid Path in [`src/nlp/query_planner.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/src/nlp/query_planner.py):
    - Relational query filters qualifying companies (e.g. `CTC > 18 LPA`).
    - Company names feed into RAG metadata filters to retrieve interview rounds, questions, and topics.
    - Synthesizes output into the strict 7-part answer format with both SQL query and RAG experience citations collapsible in section 7.
- **Regression Verification**:
  - Re-ran [`eval/run_eval.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/eval/run_eval.py) across all 120 benchmark test cases: **120 / 120 (100.0%) PASS RATE MAINTAINED**.

---

## Phase 6 Router, Express Backend & Liquid React UI Summary

- **Architecture Compliance (`RULE[user_global]`)**:
  - **Backend**: Node.js with **Express.js** ([`server/index.js`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/server/index.js)). Spawns high-performance Python runner bridge with full UTF-8 JSON streaming.
  - **Frontend**: **React** (Vite + Tailwind CSS + Lucide Icons) in [`client/`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/client/).
  - **Unified Deployment**: Express server statically serves production React build (`client/dist`) at `http://localhost:5000` while providing clean REST API routes under `/api/*`.
- **API Endpoints Implemented**:
  1. `POST /api/chat`: Accepts user query, evaluates via query planner, returns structured 7-part JSON response.
  2. `GET /api/stats`: Comprehensive institutional database metrics (cohort counts, placed students, packages, canonical entities).
  3. `GET /api/sample-questions`: Curated question bank covering all 12 question categories with full query descriptions.
  4. `GET /api/health`: Health and service heartbeat monitoring.
  5. `GET /api/cache/stats`: In-memory cache utilization, hit/miss metrics, and hit-rate monitoring.
  6. `POST /api/cache/clear`: Cache invalidation endpoint.
- **Liquid UI Design & Features**:
  - **Visual Aesthetics**: Futuristic dark theme with fluid glowing mesh gradients, ambient background orbs, glassmorphic frosted cards (`backdrop-blur-xl`), and crisp micro-borders (`border-white/10`).
  - **Interactive Category Carousel / Pills**: Fast-access pills for all 12 question categories allowing one-click execution of challenging queries.
  - **Institutional Statistics Modal**: Glassmorphic modal displaying live cohort coverage, highest international/domestic offers, verified CTC counts, and interview experience statistics.
  - **Strict 7-Part Answer Presentation ([`client/src/components/StrictAnswerView.jsx`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/client/src/components/StrictAnswerView.jsx))**:
    1. Direct 1-2 line answer in glowing gradient highlight.
    2. Polished markdown data tables with sticky headers and zebra striping.
    3. Analytical breakdown & data-grounded insights.
    4. Exact semantic definition badge (e.g. `placed_students = COUNT(DISTINCT student_id)`).
    5. Data scope badge with academic cohorts and completeness caveats.
    6. Verifier confidence indicator (High / Medium / Low) with semantic verification explanation.
    7. Collapsible source inspector detailing generated SQL queries and RAG interview citations.

---

## Phase 7 Caching, Logging, README & Final Deliverables Summary

- **High-Performance Caching Layer**:
  - Integrated in-memory LRU cache with 24-hour TTL in [`server/index.js`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/server/index.js).
  - Query normalization strips trailing punctuation, case variances, and whitespace.
  - Repeated queries respond in **0ms** with `cached: true` flag.
- **Audit Logging System**:
  - Structured JSON Lines audit log written to [`logs/query_audit.jsonl`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/logs/query_audit.jsonl).
  - Logs query timestamps, cache status, execution latency (in ms), question category, verifier confidence, and system status.
- **Comprehensive Project Documentation**:
  - Complete [`README.md`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/README.md) covering installation, configuration, system architecture, semantic layer formulas, evaluation results, and execution guides.
- **Final Benchmark Verification**:
  - Executed [`eval/run_eval.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/eval/run_eval.py) across all 120 questions.
  - Result: **120 / 120 (100.0%) PASS RATE**. Zero hallucinations, zero mathematical inconsistencies, and strict privacy adherence.
- **Fuzz Testing & Held-Out Evaluation Suite ([`eval/fuzz.py`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/eval/fuzz.py))**:
  - Generates 590 perturbations across 6 strategies: typos, abbreviations, casing, Hinglish filler, missing words/telegraphic, and follow-up style.
  - Overall Fuzz Benchmark Accuracy: **525 / 590 (89.0%)**.
  - Created [`eval/heldout.json`](file:///c:/Users/vijay/Desktop/AI-Intelligent-Agent/eval/heldout.json) for blind user evaluation.
  - Strict enforcement: System prompts and semantic rules are **never** tuned on held-out questions.
