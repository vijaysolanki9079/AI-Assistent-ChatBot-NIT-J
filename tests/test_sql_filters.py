"""
Test Suite asserting that every filter in QuerySpec (company, branch, batch, offer_type)
MUST appear in the generated SQL WHERE clause (Fix B).
"""

import unittest
from src.nlp.query_spec import QuerySpec
from src.nlp.sql_generator import SafeSQLService

class TestSQLFilters(unittest.TestCase):

    def test_company_and_branch_and_batch_and_offer_type(self):
        spec = QuerySpec(
            intent="count",
            metrics=["placed_students"],
            metric="placed_students",
            companies=["Google"],
            branches=["CSE"],
            batches=["2021-2025"],
            offer_types=["FTE", "PPO"],
            confidence=0.95
        )
        sql, defn, qtype, err = SafeSQLService.generate_and_validate(spec, "How many placed in Google from CSE in 2021-25?")
        self.assertIsNotNone(sql, f"SQL was None: {err}")
        sql_upper = sql.upper()
        # Company
        self.assertIn("GOOGLE", sql_upper, "Company 'Google' missing in SQL")
        # Branch
        self.assertTrue("CSE" in sql_upper or "103" in sql_upper, "Branch 'CSE' missing in SQL")
        # Batch
        self.assertIn("2021-2025", sql, "Batch '2021-2025' missing in SQL")
        # Offer type
        self.assertIn("OFFER_TYPE", sql_upper, "Offer type missing in SQL")

    def test_default_all_batches_filter_present(self):
        spec = QuerySpec(
            intent="count",
            metrics=["placed_students"],
            metric="placed_students",
            companies=["Oracle"],
            branches=["IT"],
            batches=["2020-2024", "2021-2025", "2022-2026"],
            offer_types=["FTE", "PPO"],
            confidence=0.95
        )
        sql, defn, qtype, err = SafeSQLService.generate_and_validate(spec, "IT got into Oracle")
        self.assertIsNotNone(sql, f"SQL was None: {err}")
        sql_upper = sql.upper()
        self.assertIn("ORACLE", sql_upper, "Company 'Oracle' missing in SQL")
        self.assertTrue("IT" in sql_upper or "124" in sql_upper, "Branch 'IT' missing in SQL")
        self.assertIn("BATCH_ID", sql_upper, "Batch filter missing in SQL")
        self.assertIn("OFFER_TYPE", sql_upper, "Offer type filter missing in SQL")

    def test_lookup_company_branch_filters(self):
        spec = QuerySpec(
            intent="lookup",
            metrics=["ctc"],
            metric="ctc",
            companies=["Microsoft"],
            branches=["CSE"],
            batches=["2020-2024", "2021-2025", "2022-2026"],
            offer_types=["FTE", "PPO"],
            confidence=0.95
        )
        sql, defn, qtype, err = SafeSQLService.generate_and_validate(spec, "micorsoft package cse")
        self.assertIsNotNone(sql, f"SQL was None: {err}")
        sql_upper = sql.upper()
        self.assertIn("MICROSOFT", sql_upper, "Company 'Microsoft' missing in SQL")
        self.assertTrue("CSE" in sql_upper or "103" in sql_upper, "Branch 'CSE' missing in SQL")
        self.assertIn("BATCH_ID", sql_upper, "Batch filter missing in SQL")

if __name__ == "__main__":
    unittest.main()

