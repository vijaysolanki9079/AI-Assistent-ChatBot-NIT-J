"""
NIT Jalandhar Conversational Multi-Turn Held-Out Evaluation Suite (Bug B & Bug A).
Contains 25+ comprehensive conversational scripts testing:
1. Multi-turn slot carry-over (company -> branch -> cross-branch -> metric)
2. Dimension drill-down (company package -> branch-wise -> batch filter)
3. Clarification resolution with single-word replies ("CSE", "2021-25", "all")
4. Privacy policy compliance on pronoun & names follow-ups ("names of those")
5. Topic switches (company changes, branch carries over)
6. Pronoun resolution ("they", "that company", "those")
7. Metric transitions (average -> highest -> offers)
8. Batch cohort drill-downs
9. Invariant validation (count == rows everywhere)
"""

import sys
import os
import json
from typing import List, Dict, Any, Optional

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))

from src.nlp.query_planner import QueryPlanner, SHOW_STUDENT_NAMES

TEST_CONVERSATIONS = [
    # -------------------------------------------------------------
    # Group 1: Multi-Turn Slot Carry-over & Cross-Branch Chains
    # -------------------------------------------------------------
    {
        "id": "TC-01",
        "group": "slot_carryover",
        "name": "IndiaMART CSE -> IT -> Metric Transition",
        "turns": [
            {
                "input": "how many got into IndiaMART",
                "expect_spec": {"companies": ["IndiaMart"], "metric": "placed_students"}
            },
            {
                "input": "in CSE",
                "expect_spec": {"companies": ["IndiaMart"], "branches": ["CSE"], "metric": "placed_students"}
            },
            {
                "input": "and IT?",
                "expect_spec": {"companies": ["IndiaMart"], "branches": ["IT"], "metric": "placed_students"}
            },
            {
                "input": "what packages?",
                "expect_spec": {"companies": ["IndiaMart"], "branches": ["IT"], "metric": "ctc"}
            }
        ]
    },
    {
        "id": "TC-02",
        "group": "slot_carryover",
        "name": "Microsoft Package -> Branch-wise -> Cohort Filter",
        "turns": [
            {
                "input": "microsoft package",
                "expect_spec": {"companies": ["Microsoft"], "metric": "ctc"}
            },
            {
                "input": "branch wise",
                "expect_spec": {"companies": ["Microsoft"], "group_by": ["branch"]}
            },
            {
                "input": "only 2022-26",
                "expect_spec": {"companies": ["Microsoft"], "batches": ["2022-2026"]}
            }
        ]
    },
    {
        "id": "TC-03",
        "group": "slot_carryover",
        "name": "Google Placements -> ECE -> and ME?",
        "turns": [
            {
                "input": "placements in Google",
                "expect_spec": {"companies": ["Google"], "metric": "placed_students"}
            },
            {
                "input": "for ECE",
                "expect_spec": {"companies": ["Google"], "branches": ["ECE"]}
            },
            {
                "input": "and ME?",
                "expect_spec": {"companies": ["Google"], "branches": ["ME"]}
            }
        ]
    },
    {
        "id": "TC-04",
        "group": "slot_carryover",
        "name": "Aarti Industries -> in Chemical -> and Civil?",
        "turns": [
            {
                "input": "how many placed in Aarti Industries",
                "expect_spec": {"companies": ["Aarti Industries"], "metric": "placed_students"}
            },
            {
                "input": "in Chemical",
                "expect_spec": {"companies": ["Aarti Industries"], "branches": ["CHE"]}
            },
            {
                "input": "and Civil?",
                "expect_spec": {"companies": ["Aarti Industries"], "branches": ["CE"]}
            }
        ]
    },
    {
        "id": "TC-05",
        "group": "slot_carryover",
        "name": "Oracle Offers -> in IT -> what about ECE?",
        "turns": [
            {
                "input": "how many offers by Oracle",
                "expect_spec": {"companies": ["Oracle"], "metric": "offers"}
            },
            {
                "input": "in IT",
                "expect_spec": {"companies": ["Oracle"], "branches": ["IT"], "metric": "offers"}
            },
            {
                "input": "what about ECE?",
                "expect_spec": {"companies": ["Oracle"], "branches": ["ECE"], "metric": "offers"}
            }
        ]
    },

    # -------------------------------------------------------------
    # Group 2: Clarification Handling (Single-Word Replies)
    # -------------------------------------------------------------
    {
        "id": "TC-06",
        "group": "clarification",
        "name": "Clarification: Recruiter specified -> User answers branch 'CSE'",
        "turns": [
            {
                "input": "how are placements at IndiaMart?",
                "force_clarif": "Which branch or department would you like to check for IndiaMart?",
                "expect_spec": {"companies": ["IndiaMart"]}
            },
            {
                "input": "CSE",
                "expect_spec": {"companies": ["IndiaMart"], "branches": ["CSE"]}
            }
        ]
    },
    {
        "id": "TC-07",
        "group": "clarification",
        "name": "Clarification: Recruiter specified -> User answers branch 'IT'",
        "turns": [
            {
                "input": "tell me about Google hires",
                "force_clarif": "Which department would you like to inspect for Google?",
                "expect_spec": {"companies": ["Google"]}
            },
            {
                "input": "IT",
                "expect_spec": {"companies": ["Google"], "branches": ["IT"]}
            }
        ]
    },
    {
        "id": "TC-08",
        "group": "clarification",
        "name": "Clarification: Batch clarification -> User answers '2021-25'",
        "turns": [
            {
                "input": "Amazon offers in CSE",
                "force_clarif": "Which batch: 2020-24, 2021-25, 2022-26, or all?",
                "expect_spec": {"companies": ["Amazon"], "branches": ["CSE"]}
            },
            {
                "input": "2021-25",
                "expect_spec": {"companies": ["Amazon"], "branches": ["CSE"], "batches": ["2021-2025"]}
            }
        ]
    },
    {
        "id": "TC-09",
        "group": "clarification",
        "name": "Clarification: Batch clarification -> User answers 'all'",
        "turns": [
            {
                "input": "Microsoft hires in IT",
                "force_clarif": "Which batch: 2020-24, 2021-25, 2022-26, or all?",
                "expect_spec": {"companies": ["Microsoft"], "branches": ["IT"]}
            },
            {
                "input": "all",
                "expect_spec": {"companies": ["Microsoft"], "branches": ["IT"]}
            }
        ]
    },
    {
        "id": "TC-10",
        "group": "clarification",
        "name": "Clarification: Affirmation 'yes' after bot suggestion",
        "turns": [
            {
                "input": "how many in micro soft?",
                "force_clarif": "Did you mean Microsoft?",
                "expect_spec": {"companies": ["Microsoft"]}
            },
            {
                "input": "yes",
                "expect_spec": {"companies": ["Microsoft"]}
            }
        ]
    },

    # -------------------------------------------------------------
    # Group 3: Privacy Compliance on Names / Pronoun Follow-ups
    # -------------------------------------------------------------
    {
        "id": "TC-11",
        "group": "privacy_policy",
        "name": "Count query -> Follow-up 'names of those' (Must preserve privacy)",
        "turns": [
            {
                "input": "how many placed in IndiaMart in CSE",
                "expect_spec": {"companies": ["IndiaMart"], "branches": ["CSE"], "metric": "placed_students"}
            },
            {
                "input": "names of those",
                "expect_privacy": True,
                "expect_spec": {"companies": ["IndiaMart"], "branches": ["CSE"]}
            }
        ]
    },
    {
        "id": "TC-12",
        "group": "privacy_policy",
        "name": "Google hires -> Follow-up 'who got placed'",
        "turns": [
            {
                "input": "students placed in Google in CSE",
                "expect_spec": {"companies": ["Google"], "branches": ["CSE"]}
            },
            {
                "input": "who got placed",
                "expect_privacy": True,
                "expect_spec": {"companies": ["Google"], "branches": ["CSE"]}
            }
        ]
    },
    {
        "id": "TC-13",
        "group": "privacy_policy",
        "name": "Amazon offers -> Follow-up 'show their names'",
        "turns": [
            {
                "input": "how many got into Amazon in IT",
                "expect_spec": {"companies": ["Amazon"], "branches": ["IT"]}
            },
            {
                "input": "show their names",
                "expect_privacy": True,
                "expect_spec": {"companies": ["Amazon"], "branches": ["IT"]}
            }
        ]
    },
    {
        "id": "TC-14",
        "group": "privacy_policy",
        "name": "Microsoft -> Follow-up 'list roll numbers'",
        "turns": [
            {
                "input": "Microsoft placements in CSE",
                "expect_spec": {"companies": ["Microsoft"], "branches": ["CSE"]}
            },
            {
                "input": "give me their roll numbers",
                "expect_privacy": True,
                "expect_spec": {"companies": ["Microsoft"]}
            }
        ]
    },

    # -------------------------------------------------------------
    # Group 4: Topic Switches (Company changes, branch/batch stays)
    # -------------------------------------------------------------
    {
        "id": "TC-15",
        "group": "topic_switch",
        "name": "IndiaMart in CSE -> 'what about Amazon?'",
        "turns": [
            {
                "input": "how many placed in IndiaMart in CSE",
                "expect_spec": {"companies": ["IndiaMart"], "branches": ["CSE"]}
            },
            {
                "input": "what about Amazon?",
                "expect_spec": {"companies": ["Amazon"], "branches": ["CSE"]}
            }
        ]
    },
    {
        "id": "TC-16",
        "group": "topic_switch",
        "name": "Google in IT -> 'what about Microsoft?'",
        "turns": [
            {
                "input": "Google package in IT",
                "expect_spec": {"companies": ["Google"], "branches": ["IT"]}
            },
            {
                "input": "what about Microsoft?",
                "expect_spec": {"companies": ["Microsoft"], "branches": ["IT"]}
            }
        ]
    },
    {
        "id": "TC-17",
        "group": "topic_switch",
        "name": "Qualcomm in ECE -> 'and Intel?'",
        "turns": [
            {
                "input": "how many hires in Qualcomm in ECE",
                "expect_spec": {"companies": ["Qualcomm"], "branches": ["ECE"]}
            },
            {
                "input": "and Intel?",
                "expect_spec": {"companies": ["Intel"], "branches": ["ECE"]}
            }
        ]
    },
    {
        "id": "TC-18",
        "group": "topic_switch",
        "name": "BPCL in Chemical -> 'what about Reliance?'",
        "turns": [
            {
                "input": "BPCL placements in Chemical",
                "expect_spec": {"companies": ["BPCL"], "branches": ["CHE"]}
            },
            {
                "input": "what about Reliance?",
                "expect_spec": {"companies": ["Reliance Industries"], "branches": ["CHE"]}
            }
        ]
    },

    # -------------------------------------------------------------
    # Group 5: Pronoun Reference Resolution
    # -------------------------------------------------------------
    {
        "id": "TC-19",
        "group": "pronoun_resolution",
        "name": "Interview inquiry -> 'what questions did they ask?'",
        "turns": [
            {
                "input": "how was the interview for Google?",
                "expect_spec": {"companies": ["Google"]}
            },
            {
                "input": "what questions did they ask?",
                "expect_spec": {"companies": ["Google"]}
            }
        ]
    },
    {
        "id": "TC-20",
        "group": "pronoun_resolution",
        "name": "Microsoft drive -> 'how many did that company hire?'",
        "turns": [
            {
                "input": "tell me about Microsoft placement records",
                "expect_spec": {"companies": ["Microsoft"]}
            },
            {
                "input": "how many students did that company hire?",
                "expect_spec": {"companies": ["Microsoft"], "metric": "placed_students"}
            }
        ]
    },

    # -------------------------------------------------------------
    # Group 6: Metric Transitions (Average -> Highest -> Offers)
    # -------------------------------------------------------------
    {
        "id": "TC-21",
        "group": "metric_transition",
        "name": "Google Average CTC -> 'and highest?'",
        "turns": [
            {
                "input": "Google average package in CSE",
                "expect_spec": {"companies": ["Google"], "branches": ["CSE"], "metric": "avg_ctc"}
            },
            {
                "input": "and highest?",
                "expect_spec": {"companies": ["Google"], "branches": ["CSE"], "metric": "max_ctc"}
            }
        ]
    },
    {
        "id": "TC-22",
        "group": "metric_transition",
        "name": "Amazon Placements -> 'total offers count'",
        "turns": [
            {
                "input": "Amazon placed students in IT",
                "expect_spec": {"companies": ["Amazon"], "branches": ["IT"], "metric": "placed_students"}
            },
            {
                "input": "total offers count",
                "expect_spec": {"companies": ["Amazon"], "branches": ["IT"], "metric": "offers"}
            }
        ]
    },
    {
        "id": "TC-23",
        "group": "metric_transition",
        "name": "Summer Internship -> 'what stipend?'",
        "turns": [
            {
                "input": "summer intern offers in Microsoft",
                "expect_spec": {"companies": ["Microsoft"]}
            },
            {
                "input": "what stipend?",
                "expect_spec": {"companies": ["Microsoft"], "metric": "stipend"}
            }
        ]
    },

    # -------------------------------------------------------------
    # Group 7: Cohort & Batch Transitions
    # -------------------------------------------------------------
    {
        "id": "TC-24",
        "group": "batch_drilldown",
        "name": "CSE Offers -> 'for 2021-25' -> 'and 2022-26?'",
        "turns": [
            {
                "input": "how many offers in CSE",
                "expect_spec": {"branches": ["CSE"], "metric": "offers"}
            },
            {
                "input": "for 2021-25",
                "expect_spec": {"branches": ["CSE"], "batches": ["2021-2025"], "metric": "offers"}
            },
            {
                "input": "and 2022-26?",
                "expect_spec": {"branches": ["CSE"], "batches": ["2022-2026"], "metric": "offers"}
            }
        ]
    },
    {
        "id": "TC-25",
        "group": "batch_drilldown",
        "name": "Highest Package in IT -> 'for 2023-27'",
        "turns": [
            {
                "input": "highest package in IT",
                "expect_spec": {"branches": ["IT"], "metric": "max_ctc"}
            },
            {
                "input": "for 2023-27",
                "expect_spec": {"branches": ["IT"], "batches": ["2023-2027"]}
            }
        ]
    },
    {
        "id": "TC-26",
        "group": "batch_drilldown",
        "name": "Mechanical Engineering -> 'only 2020-24'",
        "turns": [
            {
                "input": "placements in Mechanical Engineering",
                "expect_spec": {"branches": ["ME"], "metric": "placed_students"}
            },
            {
                "input": "only 2020-24",
                "expect_spec": {"branches": ["ME"], "batches": ["2020-2024"]}
            }
        ]
    }
]


def run_multiturn_eval():
    planner = QueryPlanner()
    print("=" * 70)
    print("RUNNING MULTI-TURN CONVERSATIONAL EVALUATION SUITE (Bug B & Bug A)")
    print("=" * 70)

    results_by_group = {}
    failures = []
    total_turns = 0
    passed_turns = 0

    for test in TEST_CONVERSATIONS:
        tid = test["id"]
        group = test["group"]
        name = test["name"]
        turns = test["turns"]

        if group not in results_by_group:
            results_by_group[group] = {"total": 0, "passed": 0}

        history = []
        session_state = {
            "last_query_spec": None,
            "last_answer_summary": None,
            "pending_clarification": None
        }

        print(f"\n[{tid}] ({group}) {name}")

        for turn_idx, turn in enumerate(turns):
            user_msg = turn["input"]
            expected_spec = turn.get("expect_spec", {})
            expect_privacy = turn.get("expect_privacy", False)
            force_clarif = turn.get("force_clarif")

            total_turns += 1
            results_by_group[group]["total"] += 1

            if force_clarif:
                session_state["pending_clarification"] = force_clarif

            # Execute turn via QueryPlanner with history and session state
            res = planner.plan_and_execute(user_msg, history=history, session_state=session_state)
            ans = res.get("answer", "")
            actual_spec = res.get("query_spec", {})
            sql = res.get("sql", "")
            standalone_q = res.get("standalone_question", user_msg)
            payload = res.get("payload") or {}

            # Assertions
            passed = True
            failure_reasons = []

            # 1. Check QuerySpec slots
            if "companies" in expected_spec:
                actual_comps = actual_spec.get("companies", [])
                for ec in expected_spec["companies"]:
                    if not any(ec.lower() in c.lower() or c.lower() in ec.lower() for c in actual_comps):
                        passed = False
                        failure_reasons.append(f"Expected company '{ec}' not in {actual_comps}")

            if "branches" in expected_spec:
                actual_branches = actual_spec.get("branches", [])
                for eb in expected_spec["branches"]:
                    if eb.upper() not in [b.upper() for b in actual_branches]:
                        passed = False
                        failure_reasons.append(f"Expected branch '{eb}' not in {actual_branches}")

            if "batches" in expected_spec:
                actual_batches = actual_spec.get("batches", [])
                for eb in expected_spec["batches"]:
                    # check normalized
                    eb_clean = eb.replace("2021-25", "2021-2025").replace("2022-26", "2022-2026").replace("2020-24", "2020-2024").replace("2023-27", "2023-2027")
                    if not any(eb_clean in ab for ab in actual_batches):
                        passed = False
                        failure_reasons.append(f"Expected batch '{eb}' not in {actual_batches}")

            if "metric" in expected_spec:
                actual_metric = actual_spec.get("metric")
                exp_metric = expected_spec["metric"]
                is_metric_match = (
                    actual_metric == exp_metric
                    or (exp_metric == "offers" and actual_metric == "total_offers")
                    or (exp_metric == "total_offers" and actual_metric == "offers")
                    or (exp_metric in ["package", "packages"] and actual_metric in ["ctc", "avg_ctc", "max_ctc"])
                )
                if not is_metric_match:
                    passed = False
                    failure_reasons.append(f"Expected metric '{exp_metric}', got '{actual_metric}'")

            if "group_by" in expected_spec:
                actual_gb = actual_spec.get("group_by", [])
                for eg in expected_spec["group_by"]:
                    if eg not in actual_gb:
                        passed = False
                        failure_reasons.append(f"Expected group_by '{eg}' not in {actual_gb}")

            # 2. Check Privacy policy compliance
            if expect_privacy:
                # Student personal names must NEVER be present when SHOW_STUDENT_NAMES=False
                if not SHOW_STUDENT_NAMES:
                    for forbidden in ["LOVKESH", "SAMARTH", "SUKRIT", "ALOK", "MANAV"]:
                        if forbidden in ans.upper():
                            passed = False
                            failure_reasons.append(f"Privacy violation: student name '{forbidden}' found in answer!")
                # Answer must contain privacy policy note or block
                if "privacy" not in ans.lower() and "protected" not in ans.lower() and "confidential" not in ans.lower():
                    passed = False
                    failure_reasons.append("Expected privacy notice/protection message not found in answer.")

            # 3. Invariant: count == listed rows wherever a list is returned
            if payload and "count" in payload:
                p_count = payload.get("count", 0)
                p_rows = payload.get("rows", [])
                if p_rows and len(p_rows) > 1 and len(p_rows[0]) == 1 and not payload.get("package_stats"):
                    if p_count != len(p_rows):
                        passed = False
                        failure_reasons.append(f"Payload inconsistency: count={p_count} but len(rows)={len(p_rows)}")

            if passed:
                passed_turns += 1
                results_by_group[group]["passed"] += 1
                print(f"  Turn {turn_idx+1}: \"{user_msg}\" -> PASS (Standalone: \"{standalone_q}\")")
            else:
                print(f"  Turn {turn_idx+1}: \"{user_msg}\" -> FAIL: {'; '.join(failure_reasons)}")
                failures.append({
                    "test_id": tid,
                    "test_name": name,
                    "turn": turn_idx + 1,
                    "history": list(history),
                    "input": user_msg,
                    "standalone_question": standalone_q,
                    "expected_spec": expected_spec,
                    "actual_spec": actual_spec,
                    "sql": sql,
                    "answer_preview": ans[:160],
                    "reasons": failure_reasons
                })

            # Update session state & history for subsequent turns
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": ans})

            session_state["last_query_spec"] = actual_spec
            session_state["last_answer_summary"] = ans
            if actual_spec.get("needs_clarification"):
                session_state["pending_clarification"] = actual_spec.get("clarification_question")
            else:
                session_state["pending_clarification"] = None

    # Print Summary Report
    print("\n" + "=" * 70)
    print("MULTI-TURN EVALUATION REPORT")
    print("=" * 70)
    overall_pass_rate = (passed_turns / total_turns) * 100 if total_turns else 0.0

    print(f"\nOverall Pass Rate: {passed_turns}/{total_turns} ({overall_pass_rate:.1f}%)\n")
    print(f"{'Category':<25} | {'Passed':<8} | {'Total':<8} | {'Pass Rate'}")
    print("-" * 55)
    for grp, st in results_by_group.items():
        pr = (st["passed"] / st["total"]) * 100 if st["total"] else 0.0
        print(f"{grp:<25} | {st['passed']:<8} | {st['total']:<8} | {pr:.1f}%")

    if failures:
        print("\n" + "=" * 70)
        print(f"FAILED TURNS LISTING ({len(failures)} failures):")
        print("=" * 70)
        for f in failures:
            print(f"\nTest [{f['test_id']}] Turn {f['turn']}: \"{f['input']}\"")
            print(f"History: {f['history']}")
            print(f"Standalone Question: \"{f['standalone_question']}\"")
            print(f"QuerySpec: {json.dumps(f['actual_spec'])}")
            print(f"SQL: {f['sql']}")
            print(f"Reasons: {f['reasons']}")
    else:
        print("\nALL 26 MULTI-TURN TEST SCRIPTS PASSED (100.0%) WITH ZERO FAILURES!")

    return len(failures) == 0

if __name__ == "__main__":
    success = run_multiturn_eval()
    sys.exit(0 if success else 1)
