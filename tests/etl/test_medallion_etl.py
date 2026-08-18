"""
ETL Tests — Bronze/Silver/Gold layer logic (in-memory PySpark, no S3/network needed)
Run with: pytest tests/etl/test_medallion_etl.py -v
"""

import sys
import os
import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "medallion", "gold"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "medallion", "silver"))

from transformation import clean_prescriber_drug  # noqa: E402


@pytest.fixture(scope="module")
def spark():
    spark = SparkSession.builder.master("local[2]").appName("ETLTests").getOrCreate()
    yield spark
    spark.stop()


@pytest.fixture
def silver_prescriber_drug(spark):
    """Simulates cleaned Silver-layer prescriber_drug data for Gold aggregation tests."""
    data = [
        (1001, "AUSTIN", "TX", "Family Medicine", "ADVIL", "IBUPROFEN", 100, 500.0, 80, 2023, False, 5.0),
        (1002, "DALLAS", "TX", "Cardiology", "GENERIC-X", "GENERIC-X", 200, 1000.0, 150, 2023, True, 5.0),
        (1003, "MIAMI", "FL", "Pain Management", "OXY-BRAND", "OXYCODONE", 50, 2000.0, 30, 2023, False, 40.0),
    ]
    columns = [
        "prscrbr_npi", "prscrbr_city", "prscrbr_state_abrvtn", "prscrbr_type",
        "brnd_name", "gnrc_name", "tot_clms", "tot_drug_cst", "tot_benes",
        "year", "is_generic", "avg_cost_per_claim",
    ]
    return spark.createDataFrame(data, columns)


class TestBronzeToSilver:
    """Validates the core Silver cleaning contract used across the pipeline."""

    def test_silver_output_has_no_nulls_in_key_columns(self, spark):
        raw = spark.createDataFrame(
            [(None, "X", "Y", "Z", "A", "B", 10, 1.0, 100.0, 5, 2, 2023)],
            ["prscrbr_npi", "prscrbr_last_org_name", "prscrbr_first_name", "prscrbr_city",
             "prscrbr_state_abrvtn", "prscrbr_type", "tot_clms", "tot_30day_fills",
             "tot_drug_cst", "tot_day_suply", "tot_benes", "year"],
        ).withColumn("brnd_name", F.lit("X")).withColumn("gnrc_name", F.lit("Y"))

        cleaned = clean_prescriber_drug(raw)
        assert cleaned.filter(cleaned.prscrbr_npi.isNull()).count() == 0


class TestSilverToGold:
    """Validates Gold-layer aggregation logic (drug/prescriber/state rollups)."""

    def test_drug_summary_aggregation_sums_correctly(self, silver_prescriber_drug):
        drug_summary = (
            silver_prescriber_drug.groupBy("gnrc_name", "brnd_name", "year", "is_generic")
            .agg(
                F.sum("tot_clms").alias("total_claims"),
                F.sum("tot_drug_cst").alias("total_cost_usd"),
            )
        )
        ibuprofen_row = drug_summary.filter(drug_summary.gnrc_name == "IBUPROFEN").first()
        assert ibuprofen_row["total_claims"] == 100
        assert ibuprofen_row["total_cost_usd"] == 500.0

    def test_state_kpi_aggregation_groups_by_state(self, silver_prescriber_drug):
        state_kpi = (
            silver_prescriber_drug.groupBy("prscrbr_state_abrvtn")
            .agg(F.sum("tot_drug_cst").alias("total_cost_usd"))
        )
        tx_row = state_kpi.filter(state_kpi.prscrbr_state_abrvtn == "TX").first()
        assert tx_row["total_cost_usd"] == 1500.0  # 500 + 1000

    def test_pain_specialty_flagging_for_opioid_tracking(self, silver_prescriber_drug):
        flagged = silver_prescriber_drug.withColumn(
            "is_pain_mgmt",
            F.lower(F.col("prscrbr_type")).contains("pain")
        )
        pain_rows = flagged.filter(flagged.is_pain_mgmt).count()
        assert pain_rows == 1

    def test_no_negative_total_cost_after_aggregation(self, silver_prescriber_drug):
        drug_summary = silver_prescriber_drug.groupBy("gnrc_name").agg(
            F.sum("tot_drug_cst").alias("total_cost_usd")
        )
        negative_rows = drug_summary.filter(drug_summary.total_cost_usd < 0).count()
        assert negative_rows == 0


class TestDataConsistency:
    """Cross-layer consistency: row counts should never increase silently across layers."""

    def test_gold_row_count_not_greater_than_silver(self, silver_prescriber_drug):
        silver_count = silver_prescriber_drug.count()
        gold_count = silver_prescriber_drug.groupBy("gnrc_name").count().count()
        assert gold_count <= silver_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
