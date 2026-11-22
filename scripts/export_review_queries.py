"""
Export and Triage Script for Low-Confidence & Clarified Queries (Step 7).
Parses logs/query_audit.jsonl to extract:
1. Queries with confidence < 0.70
2. Queries requiring user clarification (needs_clarification=True, status="clarification_required")
3. Unhandled error queries

Outputs a structured JSON triage set (logs/review_triage.json) and Markdown summary
report (logs/review_triage_report.md) for active curation and expansion of evaluation test sets.
"""

import argparse
import datetime
import json
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional

DEFAULT_AUDIT_LOG = os.path.join("logs", "query_audit.jsonl")
DEFAULT_OUTPUT_JSON = os.path.join("logs", "review_triage.json")
DEFAULT_OUTPUT_MD = os.path.join("logs", "review_triage_report.md")


def parse_audit_log(
    log_file: str = DEFAULT_AUDIT_LOG,
    min_confidence: float = 0.70
) -> List[Dict[str, Any]]:
    """Read audit log and extract low-confidence or clarified queries."""
    if not os.path.exists(log_file):
        print(f"Warning: Audit log file '{log_file}' does not exist yet.")
        return []

    triage_records = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as e:
                print(f"Skipping malformed line {line_num}: {e}")
                continue

            q = (rec.get("question") or rec.get("query") or "").strip()
            raw_conf = rec.get("confidence", 1.0)
            try:
                conf = float(raw_conf)
            except Exception:
                conf = 1.0
            status = rec.get("status", "")
            q_spec = rec.get("query_spec") or {}
            needs_clarify = bool(q_spec.get("needs_clarification", False)) or status == "clarification_required" or rec.get("category") == "ambiguous"
            is_error = status == "error" or rec.get("error") is not None
            is_low_conf = conf < min_confidence

            if is_low_conf or needs_clarify or is_error:
                reason = []
                if is_low_conf:
                    reason.append(f"Low confidence ({conf:.2f} < {min_confidence:.2f})")
                if needs_clarify:
                    reason.append("Clarification required")
                if is_error:
                    reason.append(f"Execution error ({rec.get('error')})")

                triage_records.append({
                    "question": q,
                    "timestamp": rec.get("timestamp"),
                    "confidence": conf,
                    "status": status,
                    "category": rec.get("category"),
                    "reasons": reason,
                    "clarification_question": q_spec.get("clarification_question"),
                    "sql": rec.get("sql"),
                    "query_spec": q_spec
                })

    return triage_records


def aggregate_and_deduplicate(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group by normalized question to count frequency and aggregate reasons."""
    groups = defaultdict(list)
    for r in records:
        key = r["question"].strip().lower()
        groups[key].append(r)

    deduped = []
    for norm_q, items in groups.items():
        latest = items[-1]
        min_conf = min(it["confidence"] for it in items)
        all_reasons = list(set(r for it in items for r in it["reasons"]))
        deduped.append({
            "question": latest["question"],
            "frequency": len(items),
            "min_confidence": min_conf,
            "status": latest["status"],
            "reasons": all_reasons,
            "clarification_question": latest["clarification_question"],
            "last_seen": latest["timestamp"],
            "query_spec": latest["query_spec"],
            "sql": latest["sql"]
        })

    # Sort by frequency (descending), then confidence (ascending)
    deduped.sort(key=lambda x: (-x["frequency"], x["min_confidence"]))
    return deduped


def generate_markdown_report(records: List[Dict[str, Any]], min_conf: float) -> str:
    """Generate human-readable Markdown triage report."""
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# NITJ Placement Assistant - Query Review & Triage Report",
        f"\n*Generated on: {now}*",
        f"\n**Triage Criteria**: Confidence < {min_conf:.2f} OR Clarification Required OR Error\n",
        f"**Total Distinct Queries Requiring Review**: {len(records)}\n",
        "## Summary Table\n",
        "| # | Question | Freq | Min Conf | Status | Primary Reason | Clarification Asked |",
        "|---|---|---|---|---|---|---|"
    ]

    for idx, r in enumerate(records, 1):
        q = r["question"].replace("|", "\\|")
        freq = r["frequency"]
        conf = f"{r['min_confidence']:.2f}"
        status = r["status"]
        reason = "; ".join(r["reasons"])
        clar = (r.get("clarification_question") or "None").replace("|", "\\|")
        if len(clar) > 50:
            clar = clar[:47] + "..."
        lines.append(f"| {idx} | {q} | {freq} | {conf} | {status} | {reason} | {clar} |")

    lines.append("\n## Detailed Inspection & Recommended Actions\n")
    for idx, r in enumerate(records[:25], 1):
        lines.append(f"### {idx}. \"{r['question']}\"")
        lines.append(f"- **Frequency**: {r['frequency']} occurrence(s)")
        lines.append(f"- **Confidence**: {r['min_confidence']:.2f}")
        lines.append(f"- **Reasons**: {', '.join(r['reasons'])}")
        if r.get("clarification_question"):
            lines.append(f"- **Clarification Question**: `{r['clarification_question']}`")
        if r.get("sql"):
            lines.append(f"- **Executed SQL**:\n```sql\n{r['sql']}\n```")
        lines.append("- **Suggested Action**: Evaluate intent mapping, add canonical alias, or add to `eval/heldout.json`.\n")

    return "\n".join(lines)


def export_triage(
    audit_file: str = DEFAULT_AUDIT_LOG,
    output_json: str = DEFAULT_OUTPUT_JSON,
    output_md: str = DEFAULT_OUTPUT_MD,
    min_confidence: float = 0.70
):
    """Main export execution."""
    print(f"Reading audit records from {audit_file} (threshold < {min_confidence})...")
    raw_records = parse_audit_log(audit_file, min_confidence=min_confidence)
    deduped = aggregate_and_deduplicate(raw_records)

    # Ensure output directories exist
    os.makedirs(os.path.dirname(output_json) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(output_md) or ".", exist_ok=True)

    # 1. Write JSON triage file
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)
    print(f"Exported {len(deduped)} distinct review items to {output_json}")

    # 2. Write Markdown report
    md_content = generate_markdown_report(deduped, min_conf=min_confidence)
    with open(output_md, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Generated Markdown triage report at {output_md}")

    return deduped


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export low-confidence & clarified queries for active review.")
    parser.add_argument("--input", default=DEFAULT_AUDIT_LOG, help="Input query_audit.jsonl path")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_JSON, help="Output JSON triage file")
    parser.add_argument("--report", default=DEFAULT_OUTPUT_MD, help="Output Markdown report file")
    parser.add_argument("--min-conf", type=float, default=0.70, help="Confidence threshold (default 0.70)")
    args = parser.parse_args()

    export_triage(
        audit_file=args.input,
        output_json=args.output,
        output_md=args.report,
        min_confidence=args.min_conf
    )
