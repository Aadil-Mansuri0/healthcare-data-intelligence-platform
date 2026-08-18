"""
GOLD LAYER — KPI Aggregation
S3 Silver → S3 Gold (report-ready, Snowflake-loadable tables)
"""

import argparse
import logging
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoldAggregation")

S3_SILVER = "s3://healthcare-datalake/silver"
S3_GOLD   = "s3://healthcare-datalake/gold"


def create_spark_session():
    return (
        SparkSession.builder
        .appName("HealthcareGoldAggregation")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )


def build_drug_summary(spark, date: str):
    """
    GOLD TABLE: drug_summary
    Aggregated drug spend and claim counts by drug name, year
    → Loaded into Snowflake GOLD_SCHEMA.DRUG_SUMMARY
    """
    df = spark.read.parquet(f"{S3_SILVER}/prescriber_drug/date={date}")

    drug_summary = (
        df.groupBy("gnrc_name", "brnd_name", "year", "is_generic")
        .agg(
            F.sum("tot_clms").alias("total_claims"),
            F.sum("tot_drug_cst").alias("total_cost_usd"),
            F.sum("tot_benes").alias("total_beneficiaries"),
            F.avg("avg_cost_per_claim").alias("avg_cost_per_claim"),
            F.countDistinct("prscrbr_npi").alias("unique_prescribers"),
        )
        .withColumn("cost_rank",
            F.rank().over(Window.partitionBy("year").orderBy(F.desc("total_cost_usd")))
        )
        .withColumn("_gold_ts", F.current_timestamp())
    )

    drug_summary.write.mode("overwrite").parquet(f"{S3_GOLD}/drug_summary/date={date}")
    logger.info(f"  ✅ drug_summary: {drug_summary.count():,} rows")


def build_prescriber_summary(spark, date: str):
    """
    GOLD TABLE: prescriber_summary
    Top prescribers by total cost, claims, beneficiaries
    → Loaded into Snowflake GOLD_SCHEMA.PRESCRIBER_SUMMARY
    """
    df = spark.read.parquet(f"{S3_SILVER}/prescriber_drug/date={date}")
    prescriber = spark.read.parquet(f"{S3_SILVER}/prescriber/date={date}")

    prescriber_summary = (
        df.groupBy("prscrbr_npi", "year")
        .agg(
            F.sum("tot_clms").alias("total_claims"),
            F.sum("tot_drug_cst").alias("total_cost_usd"),
            F.sum("tot_benes").alias("total_beneficiaries"),
            F.countDistinct("gnrc_name").alias("unique_drugs_prescribed"),
            F.sum(F.when(F.col("is_generic"), F.col("tot_clms")).otherwise(0))
             .alias("generic_claims"),
        )
        .join(prescriber.select(
            "prscrbr_npi", "prscrbr_last_org_name", "prscrbr_first_name",
            "prscrbr_state_abrvtn", "prscrbr_type", "prscrbr_city"
        ), on="prscrbr_npi", how="left")
        .withColumn("generic_rate",
            F.round(F.col("generic_claims") / F.col("total_claims") * 100, 2)
        )
        .withColumn("state_rank",
            F.rank().over(
                Window.partitionBy("prscrbr_state_abrvtn", "year")
                .orderBy(F.desc("total_cost_usd"))
            )
        )
        .withColumn("_gold_ts", F.current_timestamp())
    )

    prescriber_summary.write.mode("overwrite") \
        .partitionBy("year", "prscrbr_state_abrvtn") \
        .parquet(f"{S3_GOLD}/prescriber_summary/date={date}")
    logger.info(f"  ✅ prescriber_summary: {prescriber_summary.count():,} rows")


def build_state_kpi(spark, date: str):
    """
    GOLD TABLE: state_kpi
    State-level KPIs for Power BI map visualizations
    → Loaded into Snowflake GOLD_SCHEMA.STATE_KPI
    """
    df = spark.read.parquet(f"{S3_SILVER}/prescriber_drug/date={date}")
    state_ref = spark.read.parquet(f"{S3_SILVER}/state/date={date}")

    state_kpi = (
        df.groupBy("prscrbr_state_abrvtn", "year")
        .agg(
            F.sum("tot_clms").alias("total_claims"),
            F.sum("tot_drug_cst").alias("total_cost_usd"),
            F.sum("tot_benes").alias("total_beneficiaries"),
            F.countDistinct("prscrbr_npi").alias("total_prescribers"),
            F.countDistinct("gnrc_name").alias("unique_drugs"),
            F.avg("avg_cost_per_claim").alias("avg_cost_per_claim"),
            # Opioid flag (simplified: flag if prscrbr_type contains pain mgmt)
            F.sum(F.when(
                F.lower(F.col("prscrbr_type")).contains("pain") |
                F.lower(F.col("prscrbr_type")).contains("anesthesi"),
                F.col("tot_clms")
            ).otherwise(0)).alias("pain_specialty_claims"),
        )
        .join(state_ref, on=df["prscrbr_state_abrvtn"] == state_ref["state_abrvtn"], how="left")
        .withColumn("cost_per_beneficiary",
            F.round(F.col("total_cost_usd") / F.col("total_beneficiaries"), 2)
        )
        .withColumn("national_rank",
            F.rank().over(Window.partitionBy("year").orderBy(F.desc("total_cost_usd")))
        )
        .withColumn("_gold_ts", F.current_timestamp())
    )

    state_kpi.write.mode("overwrite").partitionBy("year") \
        .parquet(f"{S3_GOLD}/state_kpi/date={date}")
    logger.info(f"  ✅ state_kpi: {state_kpi.count():,} rows")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    spark = create_spark_session()
    logger.info(f"\n🥇 Gold aggregation started for date: {args.date}")

    build_drug_summary(spark, args.date)
    build_prescriber_summary(spark, args.date)
    build_state_kpi(spark, args.date)

    logger.info("\n🎉 Gold aggregation complete — ready for Snowflake load!")
    spark.stop()


if __name__ == "__main__":
    main()
