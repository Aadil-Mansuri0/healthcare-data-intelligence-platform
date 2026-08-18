"""
Unit tests for Silver-layer cleaning logic using local PySpark session.
Run with: pytest tests/test_silver_transformation.py -v
"""

import sys
import os
import pytest
from pyspark.sql import SparkSession

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "medallion", "silver"))
from transformation import clean_prescriber_drug


@pytest.fixture(scope="module")
def spark():
    spark = (
        SparkSession.builder
        .master("local[2]")
        .appName("SilverTransformTests")
        .getOrCreate()
    )
    yield spark
    spark.stop()


@pytest.fixture
def sample_df(spark):
    data = [
        (1001, "SMITH", "JOHN", "AUSTIN", "tx", "Family Medicine",
         "Advil", "ibuprofen", 100, 50.0, 500.0, 300, 80, 2023),
        (1001, "SMITH", "JOHN", "AUSTIN", "tx", "Family Medicine",
         "Advil", "ibuprofen", 100, 50.0, 500.0, 300, 80, 2023),  # duplicate
        (1002, "DOE", "JANE", "DALLAS", "TX", "Cardiology",
         "generic-x", "generic-x", 200, 100.0, 1000.0, 600, 150, 2023),
        (None, "BAD", "ROW", "NOWHERE", "ZZ", "Unknown",
         "x", "x", -5, 0.0, -10.0, 0, 0, 2023),  # bad row: null NPI, negative cost/claims
    ]
    columns = [
        "prscrbr_npi", "prscrbr_last_org_name", "prscrbr_first_name",
        "prscrbr_city", "prscrbr_state_abrvtn", "prscrbr_type",
        "brnd_name", "gnrc_name", "tot_clms", "tot_30day_fills",
        "tot_drug_cst", "tot_day_suply", "tot_benes", "year",
    ]
    return spark.createDataFrame(data, columns)


class TestSilverCleaning:

    def test_removes_duplicates(self, sample_df):
        result = clean_prescriber_drug(sample_df)
        smith_rows = result.filter(result.prscrbr_npi == 1001).count()
        assert smith_rows == 1

    def test_removes_null_npi_rows(self, sample_df):
        result = clean_prescriber_drug(sample_df)
        null_npi_count = result.filter(result.prscrbr_npi.isNull()).count()
        assert null_npi_count == 0

    def test_removes_negative_cost_rows(self, sample_df):
        result = clean_prescriber_drug(sample_df)
        negative_cost = result.filter(result.tot_drug_cst < 0).count()
        assert negative_cost == 0

    def test_state_code_uppercased(self, sample_df):
        result = clean_prescriber_drug(sample_df)
        states = [r.prscrbr_state_abrvtn for r in result.select("prscrbr_state_abrvtn").distinct().collect()]
        assert all(s == s.upper() for s in states if s)

    def test_avg_cost_per_claim_calculated(self, sample_df):
        result = clean_prescriber_drug(sample_df)
        row = result.filter(result.prscrbr_npi == 1001).first()
        assert row["avg_cost_per_claim"] == 5.0  # 500.0 / 100

    def test_is_generic_flag(self, sample_df):
        result = clean_prescriber_drug(sample_df)
        row = result.filter(result.prscrbr_npi == 1002).first()
        assert row["is_generic"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
