"""
Unit tests for the NL2SQL safety validator.
Run with: pytest tests/test_nl_to_sql.py -v
"""

import sys
import os
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "nlsql"))
from nl_to_sql import validate_sql, UnsafeSQLError


class TestSQLValidation:

    def test_valid_select_passes(self):
        sql = "SELECT * FROM GOLD_SCHEMA.DRUG_SUMMARY LIMIT 50"
        result = validate_sql(sql)
        assert result.upper().startswith("SELECT")

    def test_adds_limit_if_missing(self):
        sql = "SELECT gnrc_name FROM GOLD_SCHEMA.DRUG_SUMMARY"
        result = validate_sql(sql)
        assert "LIMIT" in result.upper()

    def test_aggregate_query_no_forced_limit_needed(self):
        sql = "SELECT COUNT(*) FROM GOLD_SCHEMA.DRUG_SUMMARY"
        result = validate_sql(sql)
        assert result is not None

    @pytest.mark.parametrize("bad_sql", [
        "DROP TABLE GOLD_SCHEMA.DRUG_SUMMARY",
        "DELETE FROM GOLD_SCHEMA.DRUG_SUMMARY WHERE year = 2023",
        "UPDATE GOLD_SCHEMA.DRUG_SUMMARY SET total_cost_usd = 0",
        "INSERT INTO GOLD_SCHEMA.DRUG_SUMMARY VALUES (1,2,3)",
        "TRUNCATE TABLE GOLD_SCHEMA.DRUG_SUMMARY",
        "ALTER TABLE GOLD_SCHEMA.DRUG_SUMMARY DROP COLUMN year",
        "CREATE TABLE evil AS SELECT * FROM GOLD_SCHEMA.DRUG_SUMMARY",
        "GRANT ALL ON GOLD_SCHEMA.DRUG_SUMMARY TO PUBLIC",
    ])
    def test_forbidden_statements_rejected(self, bad_sql):
        with pytest.raises(UnsafeSQLError):
            validate_sql(bad_sql)

    def test_statement_chaining_blocked(self):
        sql = "SELECT * FROM GOLD_SCHEMA.DRUG_SUMMARY; DROP TABLE GOLD_SCHEMA.DRUG_SUMMARY;"
        with pytest.raises(UnsafeSQLError):
            validate_sql(sql)

    def test_non_select_start_rejected(self):
        sql = "WITH x AS (DELETE FROM GOLD_SCHEMA.DRUG_SUMMARY) SELECT * FROM x"
        with pytest.raises(UnsafeSQLError):
            validate_sql(sql)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
