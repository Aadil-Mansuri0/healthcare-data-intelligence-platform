"""
SILVER LAYER — Transformation & Cleansing
S3 Bronze → S3 Silver (typed, deduplicated, null-handled, standardized)
"""

import argparse
import logging
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, DoubleType, IntegerType
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SilverTransformation")

S3_BRONZE = "s3://healthcare-datalake/bronze"
S3_SILVER = "s3://healthcare-datalake/silver"

# ─── Schemas ──────────────────────────────────────────────────────────────────
PRESCRIBER_DRUG_SCHEMA = StructType([
    StructField("prscrbr_npi", LongType(), False),
    StructField("prscrbr_last_org_name", StringType(), True),
    StructField("prscrbr_first_name", StringType(), True),
    StructField("prscrbr_city", StringType(), True),
    StructField("prscrbr_state_abrvtn", StringType(), True),
    StructField("prscrbr_type", StringType(), True),
    StructField("brnd_name", StringType(), True),
    StructField("gnrc_name", StringType(), True),
    StructField("tot_clms", IntegerType(), True),
    StructField("tot_30day_fills", DoubleType(), True),
    StructField("tot_drug_cst", DoubleType(), True),
    StructField("tot_day_suply", IntegerType(), True),
    StructField("tot_benes", IntegerType(), True),
    StructField("year", IntegerType(), True),
])


def create_spark_session():
    return (
        SparkSession.builder
        .appName("HealthcareSilverTransformation")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.parquet.compression.codec", "snappy")
        .getOrCreate()
    )


def clean_prescriber_drug(df: DataFrame) -> DataFrame:
    """Core transformations for the main fact table."""
    
    logger.info("  Cleaning prescriber_drug table...")
    
    return (
        df
        # Remove duplicates based on business key
        .dropDuplicates(["prscrbr_npi", "brnd_name", "year"])
        
        # Null handling
        .fillna({"tot_clms": 0, "tot_drug_cst": 0.0, "tot_benes": 0})
        
        # Standardize text fields
        .withColumn("prscrbr_state_abrvtn", F.upper(F.trim(F.col("prscrbr_state_abrvtn"))))
        .withColumn("gnrc_name", F.upper(F.trim(F.col("gnrc_name"))))
        .withColumn("brnd_name", F.upper(F.trim(F.col("brnd_name"))))
        .withColumn("prscrbr_type", F.initcap(F.trim(F.col("prscrbr_type"))))
        
        # Data quality filters — remove clearly bad rows
        .filter(F.col("prscrbr_npi").isNotNull())
        .filter(F.col("tot_clms") >= 0)
        .filter(F.col("tot_drug_cst") >= 0)
        .filter(F.length(F.col("prscrbr_state_abrvtn")) == 2)
        
        # Derived columns
        .withColumn("avg_cost_per_claim",
            F.when(F.col("tot_clms") > 0,
                F.round(F.col("tot_drug_cst") / F.col("tot_clms"), 2)
            ).otherwise(F.lit(0.0))
        )
        .withColumn("is_generic",
            F.when(F.col("brnd_name") == F.col("gnrc_name"), True).otherwise(False)
        )
        
        # Drop metadata columns from Bronze
        .drop("_ingestion_date", "_ingestion_ts", "_source_table")
        
        # Add Silver metadata
        .withColumn("_silver_ts", F.current_timestamp())
        .withColumn("_silver_version", F.lit("1.0"))
    )


def clean_prescriber(df: DataFrame) -> DataFrame:
    logger.info("  Cleaning prescriber table...")
    return (
        df
        .dropDuplicates(["prscrbr_npi"])
        .fillna({"prscrbr_type": "Unknown", "prscrbr_city": "Unknown"})
        .withColumn("prscrbr_state_abrvtn", F.upper(F.trim(F.col("prscrbr_state_abrvtn"))))
        .filter(F.col("prscrbr_npi").isNotNull())
        .drop("_ingestion_date", "_ingestion_ts", "_source_table")
        .withColumn("_silver_ts", F.current_timestamp())
    )


def clean_drug(df: DataFrame) -> DataFrame:
    logger.info("  Cleaning drug table...")
    return (
        df
        .dropDuplicates(["gnrc_name"])
        .withColumn("gnrc_name", F.upper(F.trim(F.col("gnrc_name"))))
        .withColumn("brnd_name", F.upper(F.trim(F.col("brnd_name"))))
        .drop("_ingestion_date", "_ingestion_ts", "_source_table")
        .withColumn("_silver_ts", F.current_timestamp())
    )


CLEANERS = {
    "prescriber_drug": clean_prescriber_drug,
    "prescriber": clean_prescriber,
    "drug": clean_drug,
    "state": lambda df: df.drop("_ingestion_date", "_ingestion_ts", "_source_table")
                         .withColumn("_silver_ts", F.current_timestamp()),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    spark = create_spark_session()

    for table, cleaner in CLEANERS.items():
        logger.info(f"\n📦 Processing Silver: {table}")
        
        bronze_path = f"{S3_BRONZE}/{table}/date={args.date}"
        silver_path = f"{S3_SILVER}/{table}/date={args.date}"

        df_raw = spark.read.parquet(bronze_path)
        logger.info(f"  Bronze rows: {df_raw.count():,}")

        df_clean = cleaner(df_raw)
        silver_count = df_clean.count()
        logger.info(f"  Silver rows: {silver_count:,}")

        # Write Silver — partitioned for query performance
        if table == "prescriber_drug":
            df_clean.write.mode("overwrite").partitionBy("year", "prscrbr_state_abrvtn") \
                    .parquet(silver_path)
        else:
            df_clean.write.mode("overwrite").parquet(silver_path)

        logger.info(f"  ✅ Silver written: {silver_path}")

    logger.info("\n🎉 Silver transformation complete!")
    spark.stop()


if __name__ == "__main__":
    main()
