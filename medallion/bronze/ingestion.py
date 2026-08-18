"""
BRONZE LAYER — Raw Ingestion
PostgreSQL → S3 Bronze (raw Parquet, schema preserved, immutable)
"""

import argparse
import logging
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BronzeIngestion")

# ─── Config ───────────────────────────────────────────────────────────────────
POSTGRES_JDBC = "jdbc:postgresql://{host}:5432/{db}"
S3_BRONZE_BASE = "s3://healthcare-datalake/bronze"

TABLES = [
    "prescriber_drug",  # ~25M rows — main fact table
    "prescriber",       # ~1.1M rows
    "drug",             # ~115K rows
    "state",            # ~30K rows
]

# Partition configs for efficient S3 writes
PARTITION_CONFIG = {
    "prescriber_drug": {"partition_col": "year", "num_partitions": 200},
    "prescriber":      {"partition_col": "nppes_provider_state", "num_partitions": 50},
    "drug":            {"partition_col": None, "num_partitions": 10},
    "state":           {"partition_col": None, "num_partitions": 5},
}


def create_spark_session():
    return (
        SparkSession.builder
        .appName("HealthcareBronzeIngestion")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0")
        .getOrCreate()
    )


def ingest_table(spark: SparkSession, table: str, jdbc_url: str, date: str, pg_props: dict):
    """Read a full table from PostgreSQL and write to S3 Bronze as Parquet."""
    
    logger.info(f"📥 Ingesting table: {table}")
    cfg = PARTITION_CONFIG[table]
    
    # Read from PostgreSQL with partition pushdown for large tables
    if cfg["num_partitions"] > 20:
        df = (
            spark.read.jdbc(
                url=jdbc_url,
                table=table,
                numPartitions=cfg["num_partitions"],
                column="prscrbr_npi",   # numeric PK for parallel reads
                lowerBound=0,
                upperBound=2_000_000_000,
                properties=pg_props,
            )
        )
    else:
        df = spark.read.jdbc(url=jdbc_url, table=table, properties=pg_props)

    # Add ingestion metadata columns
    df = df.withColumn("_ingestion_date", F.lit(date)) \
           .withColumn("_ingestion_ts", F.current_timestamp()) \
           .withColumn("_source_table", F.lit(table))

    row_count = df.count()
    logger.info(f"  → Rows read: {row_count:,}")

    # Write path: s3://healthcare-datalake/bronze/{table}/date={date}/
    output_path = f"{S3_BRONZE_BASE}/{table}/date={date}"
    
    writer = df.write.mode("overwrite").format("parquet")
    
    if cfg["partition_col"] and cfg["partition_col"] in df.columns:
        writer = writer.partitionBy(cfg["partition_col"])
    
    writer.save(output_path)
    logger.info(f"  ✅ Written to: {output_path}")
    
    return {"table": table, "rows": row_count, "path": output_path}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Execution date YYYY-MM-DD")
    parser.add_argument("--pg-host", default="postgres-source.rds.amazonaws.com")
    parser.add_argument("--pg-db", default="healthcare_cms")
    parser.add_argument("--pg-user", default="pipeline_user")
    parser.add_argument("--pg-password", required=True)
    args = parser.parse_args()

    spark = create_spark_session()
    
    jdbc_url = POSTGRES_JDBC.format(host=args.pg_host, db=args.pg_db)
    pg_props = {
        "user": args.pg_user,
        "password": args.pg_password,
        "driver": "org.postgresql.Driver",
        "fetchsize": "10000",  # Optimize JDBC fetch batches
    }

    results = []
    for table in TABLES:
        result = ingest_table(spark, table, jdbc_url, args.date, pg_props)
        results.append(result)

    # Summary log
    logger.info("\n=== BRONZE INGESTION SUMMARY ===")
    total_rows = 0
    for r in results:
        logger.info(f"  {r['table']:25s} → {r['rows']:>12,} rows → {r['path']}")
        total_rows += r["rows"]
    logger.info(f"  {'TOTAL':25s} → {total_rows:>12,} rows")
    logger.info("=================================")

    spark.stop()


if __name__ == "__main__":
    main()
