"""
Great Expectations — Silver Layer Data Quality Suite
Real GE integration (not a custom re-implementation) using the
Pandas/Spark execution engine against Silver-layer Parquet output.

Run standalone:  python great_expectations/ge_silver_suite.py --date 2026-08-15
Called from Airflow via PythonOperator in data_quality_dag.py
"""

import argparse
import logging
import sys
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GESilverSuite")

S3_SILVER = "s3://healthcare-datalake/silver"


def build_prescriber_drug_expectations(validator):
    """Define the expectation suite for GOLD_SCHEMA-bound prescriber_drug Silver data."""

    # ─── Schema / not-null expectations ─────────────────────────────────────
    validator.expect_column_to_exist("prscrbr_npi")
    validator.expect_column_to_exist("gnrc_name")
    validator.expect_column_to_exist("tot_clms")
    validator.expect_column_to_exist("tot_drug_cst")
    validator.expect_column_to_exist("avg_cost_per_claim")

    validator.expect_column_values_to_not_be_null("prscrbr_npi")
    validator.expect_column_values_to_not_be_null("gnrc_name")

    # ─── Uniqueness ──────────────────────────────────────────────────────────
    validator.expect_compound_columns_to_be_unique(
        column_list=["prscrbr_npi", "brnd_name", "year"]
    )

    # ─── Value-range expectations ────────────────────────────────────────────
    validator.expect_column_values_to_be_between(
        "tot_clms", min_value=0, max_value=10_000_000
    )
    validator.expect_column_values_to_be_between(
        "tot_drug_cst", min_value=0, max_value=1_000_000_000
    )
    validator.expect_column_values_to_be_between(
        "avg_cost_per_claim", min_value=0, max_value=500_000
    )

    # ─── Categorical / domain expectations ───────────────────────────────────
    validator.expect_column_values_to_match_regex(
        "prscrbr_state_abrvtn", r"^[A-Z]{2}$"
    )
    validator.expect_column_values_to_be_in_set(
        "is_generic", [True, False]
    )

    # ─── Statistical distribution sanity check ───────────────────────────────
    validator.expect_column_mean_to_be_between(
        "avg_cost_per_claim", min_value=1, max_value=5000
    )

    # ─── Row count sanity ─────────────────────────────────────────────────────
    validator.expect_table_row_count_to_be_between(min_value=15_000_000, max_value=50_000_000)

    return validator


def run_suite(date: str) -> bool:
    context = gx.get_context()

    datasource = context.sources.add_or_update_spark(name="healthcare_silver_datasource")
    asset = datasource.add_dataframe_asset(name="prescriber_drug_silver")

    from pyspark.sql import SparkSession
    spark = SparkSession.builder.appName("GEValidation").getOrCreate()
    df = spark.read.parquet(f"{S3_SILVER}/prescriber_drug/date={date}")

    batch_request = asset.build_batch_request(dataframe=df)

    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite_name="prescriber_drug_silver_suite",
    )

    validator = build_prescriber_drug_expectations(validator)
    validator.save_expectation_suite(discard_failed_expectations=False)

    checkpoint = context.add_or_update_checkpoint(
        name="silver_prescriber_drug_checkpoint",
        validator=validator,
    )
    results = checkpoint.run()

    success = results["success"]
    logger.info(f"\n{'='*60}\nGreat Expectations Suite Result: {'✅ PASSED' if success else '❌ FAILED'}\n{'='*60}")

    for run_result in results.run_results.values():
        validation_result = run_result["validation_result"]
        for r in validation_result["results"]:
            status = "✅" if r["success"] else "❌"
            exp_type = r["expectation_config"]["expectation_type"]
            logger.info(f"  {status} {exp_type}")

    spark.stop()
    return success


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    success = run_suite(args.date)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
