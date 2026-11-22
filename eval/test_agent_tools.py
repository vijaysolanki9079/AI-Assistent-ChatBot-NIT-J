import sys
import os

sys.path.insert(0, os.path.abspath("."))
from src.agent.tools import execute_sql, resolve_entities, search_interview_experiences, lookup_schema

def test_tools():
    print("=== Testing Agent Tools ===")

    # 1. SQL Execution
    res = execute_sql("SELECT company, ctc_lpa FROM v_offers_flat WHERE company = 'Microsoft' AND ctc_lpa IS NOT NULL")
    assert "error" not in res, f"SQL error: {res.get('error')}"
    assert res["row_count"] > 0, "Expected Microsoft offers"
    assert res["columns"][0]["name"] == "company"
    assert res["columns"][1]["unit"] == "LPA"
    print("Test 1 Passed: execute_sql returned valid typed columns and rows.")

    # 2. SQL Write Denial
    res_bad = execute_sql("INSERT INTO companies (canonical_name) VALUES ('Hacked')")
    assert "error" in res_bad, "Expected security rejection for INSERT!"
    print("Test 2 Passed: execute_sql blocked INSERT write.")

    # 3. Entity Resolution - Typo Token Bug Fix ("stasts" must NOT become branch)
    ent_adobe = resolve_entities("adobe placements stasts")
    assert ent_adobe["companies"] == ["Adobe"], f"Expected Adobe, got {ent_adobe['companies']}"
    assert ent_adobe["branches"] == [], f"Expected empty branches, got {ent_adobe['branches']}"
    print("Test 3 Passed: 'adobe placements stasts' correctly resolved Adobe without phantom branch!")

    # 4. Entity Resolution - Batch Shorthand ("25'" -> 2021-2025)
    ent_ece = resolve_entities("list me the companies that visited for ECE branch for 25' batch")
    assert "ECE" in ent_ece["branches"], f"Expected ECE, got {ent_ece['branches']}"
    assert "2021-2025" in ent_ece["batches"], f"Expected 2021-2025, got {ent_ece['batches']}"
    print("Test 4 Passed: '25'' resolved to 2021-2025 batch and ECE branch!")

    # 5. Entity Resolution - Acronym ("MSFT" -> Microsoft)
    ent_msft = resolve_entities("MSFT kitne log select hue")
    assert "Microsoft" in ent_msft["companies"], f"Expected Microsoft, got {ent_msft['companies']}"
    print("Test 5 Passed: 'MSFT' resolved to Microsoft!")

    # 6. RAG Retrieval with Citations
    rag_res = search_interview_experiences("technical round coding", company="Microsoft")
    assert rag_res["hit_count"] > 0, "Expected Microsoft interview experiences"
    chunk = rag_res["chunks"][0]
    assert chunk["experience_id"], "Missing experience_id"
    assert chunk["source_file"], "Missing source_file"
    print("Test 6 Passed: search_interview_experiences returned citations.")

    # 7. Schema Lookup
    schema_res = lookup_schema("v_offers_flat")
    assert "v_offers_flat" in schema_res, "Expected v_offers_flat documentation"
    print("Test 7 Passed: lookup_schema returned schema notes.")

    print("\nALL TOOL UNIT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_tools()

