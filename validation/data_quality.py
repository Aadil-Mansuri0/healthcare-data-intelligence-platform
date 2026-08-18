"""
DATA VALIDATION FRAMEWORK
Custom Great-Expectations-style quality checks run between medallion layers.
Fails the Airflow task (and halts the pipeline) if critical checks fail.
"""

import argparse
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataValidation")


class Severity(Enum):
    CRITICAL = "critical"   # fails pipeline
    WARNING = "warning"     # logs but continues


@dataclass
class CheckResult:
    check_name: str
    table: str
    passed: bool
    severity: Severity
    details: str = ""


@dataclass
class ValidationReport:
    results: list = field(default_factory=list)

    def add(self, result: CheckResult):
        self.results.append(result)

    @property
    def critical_failures(self):
        return [r for r in self.results if not r.passed and r.severity == Severity.CRITICAL]

    @property
    def warnings(self):
        return [r for r in self.results if not r.passed and r.severity == Severity.WARNING]

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        return f"{passed}/{total} checks passed | {len(self.critical_failures)} critical failures | {len(self.warnings)} warnings"


# ─── Individual Checks ────────────────────────────────────────────────────────

def check_not_empty(df: DataFrame, table: str, report: ValidationReport):
    count = df.count()
    passed = count > 0
    report.add(CheckResult(
        "table_not_empty", table, passed, Severity.CRITICAL,
        f"Row count: {count:,}"
    ))


def check_no_null_pk(df: DataFrame, table: str, pk_col: str, report: ValidationReport):
    if pk_col not in df.columns:
        return
    null_count = df.filter(F.col(pk_col).isNull()).count()
    passed = null_count == 0
    report.add(CheckResult(
        f"no_null_{pk_col}", table, passed, Severity.CRITICAL,
        f"Null {pk_col} count: {null_count:,}"
    ))


def check_no_duplicates(df: DataFrame, table: str, key_cols: list, report: ValidationReport):
    total = df.count()
    distinct = df.select(*key_cols).distinct().count()
    dup_count = total - distinct
    passed = dup_count == 0
    report.add(CheckResult(
        "no_duplicate_keys", table, passed, Severity.WARNING,
        f"Duplicate rows on {key_cols}: {dup_count:,}"
    ))


def check_value_range(df: DataFrame, table: str, col: str, min_val, max_val, report: ValidationReport):
    if col not in df.columns:
        return
    out_of_range = df.filter((F.col(col) < min_val) | (F.col(col) > max_val)).count()
    passed = out_of_range == 0
    report.add(CheckResult(
        f"{col}_in_range", table, passed, Severity.WARNING,
        f"Rows outside [{min_val}, {max_val}]: {out_of_range:,}"
    ))


def check_row_count_drift(df: DataFrame, table: str, expected_min: int, report: ValidationReport):
    """Detect suspicious drops in row count vs a historical baseline."""
    count = df.count()
    passed = count >= expected_min
    report.add(CheckResult(
        "row_count_not_dropped", table, passed, Severity.CRITICAL,
        f"Row count {count:,} vs expected minimum {expected_min:,}"
    ))


def check_schema_columns(df: DataFrame, table: str, required_cols: list, report: ValidationReport):
    missing = [c for c in required_cols if c not in df.columns]
    passed = len(missing) == 0
    report.add(CheckResult(
        "required_columns_present", table, passed, Severity.CRITICAL,
        f"Missing columns: {missing}" if missing else "All required columns present"
    ))


def check_valid_state_codes(df: DataFrame, table: str, col: str, report: ValidationReport):
    if col not in df.columns:
        return
    VALID_STATES = {
        "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
        "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
        "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
        "VA","WA","WV","WI","WY","DC","PR"
    }
    invalid = df.filter(~F.col(col).isin(list(VALID_STATES))).count()
    passed = invalid == 0
    report.add(CheckResult(
        "valid_state_codes", table, passed, Severity.WARNING,
        f"Rows with invalid state code: {invalid:,}"
    ))


# ─── Suite Runner ──────────────────────────────────────────────────────────────

def run_bronze_suite(spark: SparkSession, date: str) -> ValidationReport:
    report = ValidationReport()
    base = "s3://healthcare-datalake/bronze"

    tables_config = {
        "prescriber_drug": {"pk": "prscrbr_npi", "min_rows": 20_000_000},
        "prescriber": {"pk": "prscrbr_npi", "min_rows": 900_000},
        "drug": {"pk": "gnrc_name", "min_rows": 100_000},
        "state": {"pk": "state_abrvtn", "min_rows": 25_000},
    }

    for table, cfg in tables_config.items():
        logger.info(f"  Validating Bronze: {table}")
        df = spark.read.parquet(f"{base}/{table}/date={date}")
        check_not_empty(df, table, report)
        check_no_null_pk(df, table, cfg["pk"], report)
        check_row_count_drift(df, table, cfg["min_rows"], report)

    return report


def run_silver_suite(spark: SparkSession, date: str) -> ValidationReport:
    report = ValidationReport()
    base = "s3://healthcare-datalake/silver"

    df = spark.read.parquet(f"{base}/prescriber_drug/date={date}")
    check_schema_columns(df, "prescriber_drug",
        ["prscrbr_npi", "gnrc_name", "tot_clms", "tot_drug_cst", "avg_cost_per_claim"],
        report)
    check_no_duplicates(df, "prescriber_drug", ["prscrbr_npi", "brnd_name", "year"], report)
    check_value_range(df, "prescriber_drug", "tot_clms", 0, 10_000_000, report)
    check_value_range(df, "prescriber_drug", "avg_cost_per_claim", 0, 500_000, report)
    check_valid_state_codes(df, "prescriber_drug", "prscrbr_state_abrvtn", report)

    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--layer", required=True, choices=["bronze", "silver"])
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    spark = SparkSession.builder.appName("DataValidation").getOrCreate()

    logger.info(f"\n🔍 Running {args.layer.upper()} validation suite for {args.date}")

    if args.layer == "bronze":
        report = run_bronze_suite(spark, args.date)
    else:
        report = run_silver_suite(spark, args.date)

    logger.info(f"\n=== VALIDATION REPORT ({args.layer.upper()}) ===")
    for r in report.results:
        status = "✅ PASS" if r.passed else f"❌ FAIL [{r.severity.value.upper()}]"
        logger.info(f"  {status} | {r.table}.{r.check_name} — {r.details}")
    logger.info(f"\nSummary: {report.summary()}")

    spark.stop()

    if report.critical_failures:
        logger.error("🛑 CRITICAL data quality failures detected — halting pipeline!")
        sys.exit(1)

    if report.warnings:
        logger.warning(f"⚠️  {len(report.warnings)} warnings — pipeline continues")

    logger.info("✅ Validation passed — proceeding to next layer")
    sys.exit(0)


if __name__ == "__main__":
    main()
