"""
Healthcare Data Pipeline - Main Airflow DAG
Orchestrates: PostgreSQL → S3 Bronze → Silver → Gold → Snowflake
Schedule: Daily at 2 AM IST (8:30 PM UTC)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.bash import BashOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.providers.amazon.aws.operators.emr import EmrAddStepsOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable
import logging

# ─── Default Args ────────────────────────────────────────────────────────────
default_args = {
    "owner": "aadil",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email": ["aadil@healthcare-platform.com"],
}

# ─── DAG Definition ───────────────────────────────────────────────────────────
dag = DAG(
    dag_id="healthcare_medallion_pipeline",
    default_args=default_args,
    description="End-to-end Healthcare Data Pipeline: PostgreSQL → Snowflake Gold",
    schedule_interval="30 20 * * *",  # 2:00 AM IST daily
    catchup=False,
    max_active_runs=1,
    tags=["healthcare", "medallion", "production"],
)

# ─── Task Functions ───────────────────────────────────────────────────────────

def check_postgres_connection(**context):
    """Validate source PostgreSQL is reachable before pipeline starts."""
    import psycopg2
    conn = psycopg2.connect(
        host=Variable.get("POSTGRES_HOST"),
        database=Variable.get("POSTGRES_DB"),
        user=Variable.get("POSTGRES_USER"),
        password=Variable.get("POSTGRES_PASSWORD"),
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM prescriber_drug;")
    row_count = cursor.fetchone()[0]
    logging.info(f"✅ PostgreSQL OK — prescriber_drug rows: {row_count:,}")
    conn.close()
    context["ti"].xcom_push(key="source_row_count", value=row_count)


def run_bronze_ingestion(**context):
    """Trigger Spark job: PostgreSQL → S3 Bronze (raw Parquet)."""
    import subprocess
    execution_date = context["ds"]  # YYYY-MM-DD
    
    result = subprocess.run([
        "spark-submit",
        "--master", "yarn",
        "--deploy-mode", "cluster",
        "--conf", "spark.sql.adaptive.enabled=true",
        "--conf", "spark.sql.adaptive.coalescePartitions.enabled=true",
        "s3://healthcare-scripts/medallion/bronze/ingestion.py",
        "--date", execution_date,
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Bronze ingestion failed:\n{result.stderr}")
    
    logging.info(f"✅ Bronze ingestion complete for {execution_date}")


def run_data_validation(**context):
    """Run Great Expectations suite on Bronze layer."""
    import subprocess
    execution_date = context["ds"]
    
    result = subprocess.run([
        "python", "/opt/airflow/plugins/run_validation.py",
        "--layer", "bronze",
        "--date", execution_date,
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Data validation FAILED — pipeline halted!\n{result.stderr}")
    
    logging.info("✅ Data quality checks passed on Bronze")


def run_silver_transformation(**context):
    """Spark: Bronze → Silver (clean, deduplicate, type-cast)."""
    import subprocess
    execution_date = context["ds"]
    
    result = subprocess.run([
        "spark-submit",
        "--master", "yarn",
        "--deploy-mode", "cluster",
        "s3://healthcare-scripts/medallion/silver/transformation.py",
        "--date", execution_date,
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Silver transformation failed:\n{result.stderr}")
    
    logging.info("✅ Silver transformation complete")


def choose_gold_engine(**context):
    """
    STRUCTURAL fix for the Spark-vs-dbt Gold-layer conflict: both
    medallion/gold/aggregation.py (Spark) and dbt_project/models/marts/
    (dbt) can produce GOLD_SCHEMA.DRUG_SUMMARY/PRESCRIBER_SUMMARY/STATE_KPI,
    and running both against the same tables in the same run would race
    and silently corrupt Gold data (whichever finishes last wins, with no
    error). This BranchPythonOperator makes that structurally impossible —
    exactly ONE of the two downstream paths executes per DAG run, decided
    by a single Airflow Variable, not by "remembering not to enable both".

    Set via: Airflow UI → Admin → Variables → GOLD_LAYER_ENGINE = "dbt" | "spark"
    Defaults to "dbt" — it ships with schema + custom data-quality tests
    (dbt_project/models/marts/schema.yml, tests/) that the Spark path does
    not have an equivalent of; Spark remains available for the "raw-scale
    row-level transform" case described in README.md's Spark-vs-dbt table.
    """
    engine = Variable.get("GOLD_LAYER_ENGINE", default_var="dbt").strip().lower()
    if engine not in ("dbt", "spark"):
        raise ValueError(
            f"GOLD_LAYER_ENGINE must be 'dbt' or 'spark', got '{engine}' — "
            f"refusing to guess and risk writing Gold data twice."
        )
    logging.info(f"Gold layer engine selected: {engine}")
    return "gold_aggregation_dbt" if engine == "dbt" else "gold_aggregation_spark"


def run_dbt_gold_transformation(**context):
    """
    dbt path — runs through dbt-ol (OpenLineage-instrumented dbt) so lineage
    is captured automatically (see lineage/openlineage_client.py header note).
    Writes directly to Snowflake GOLD_SCHEMA; unlike the Spark path, there is
    no separate "load to Snowflake" step afterward — dbt IS the load.
    """
    import subprocess
    result = subprocess.run(
        ["dbt-ol", "run", "--project-dir", "/opt/airflow/dbt_project", "--target", "prod"],
        capture_output=True, text=True,
    )
    logging.info(result.stdout)
    if result.returncode != 0:
        raise Exception(f"dbt run failed:\n{result.stderr}")

    test_result = subprocess.run(
        ["dbt", "test", "--project-dir", "/opt/airflow/dbt_project", "--target", "prod"],
        capture_output=True, text=True,
    )
    logging.info(test_result.stdout)
    if test_result.returncode != 0:
        raise Exception(f"dbt tests FAILED — Gold layer did not pass quality checks:\n{test_result.stderr}")

    logging.info("✅ dbt Gold-layer transformation + tests complete (with automatic lineage)")


def run_gold_aggregation(**context):
    """Spark: Silver → Gold (KPI aggregations, report-ready tables)."""
    import subprocess
    execution_date = context["ds"]
    
    result = subprocess.run([
        "spark-submit",
        "--master", "yarn",
        "--deploy-mode", "cluster",
        "s3://healthcare-scripts/medallion/gold/aggregation.py",
        "--date", execution_date,
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Gold aggregation failed:\n{result.stderr}")
    
    logging.info("✅ Gold aggregation complete (Spark path)")

    # Emit lineage: Silver prescriber_drug → Gold drug_summary/prescriber_summary/state_kpi
    # (best-effort — see lineage/openlineage_client.py docstring on failure handling)
    try:
        from lineage.openlineage_client import emit_layer_transition
        for gold_table in ("drug_summary", "prescriber_summary", "state_kpi"):
            emit_layer_transition(
                job_name="gold_aggregation_spark",
                input_layer="silver", input_table="prescriber_drug",
                output_layer="gold", output_table=gold_table,
                row_count_in=0, row_count_out=0,  # row counts logged by the Spark job itself, not xcom'd
            )
    except Exception as e:
        logging.warning(f"Lineage emission skipped (non-fatal): {e}")


def notify_success(**context):
    """Send Slack/email notification on pipeline success."""
    execution_date = context["ds"]
    source_rows = context["ti"].xcom_pull(
        task_ids="check_source", key="source_row_count"
    )
    logging.info(
        f"🎉 Pipeline SUCCESS for {execution_date} | "
        f"Source rows processed: {source_rows:,}"
    )


# ─── Snowflake Load SQL ───────────────────────────────────────────────────────
SNOWFLAKE_LOAD_SQL = """
-- Load Gold layer from S3 into Snowflake
COPY INTO HEALTHCARE_DW.GOLD_SCHEMA.DRUG_SUMMARY
FROM @HEALTHCARE_DW.PUBLIC.S3_STAGE/gold/drug_summary/
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = ABORT_STATEMENT;

COPY INTO HEALTHCARE_DW.GOLD_SCHEMA.PRESCRIBER_SUMMARY  
FROM @HEALTHCARE_DW.PUBLIC.S3_STAGE/gold/prescriber_summary/
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = ABORT_STATEMENT;

COPY INTO HEALTHCARE_DW.GOLD_SCHEMA.STATE_KPI
FROM @HEALTHCARE_DW.PUBLIC.S3_STAGE/gold/state_kpi/
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = ABORT_STATEMENT;
"""

# ─── Task Definitions ─────────────────────────────────────────────────────────

t_check_source = PythonOperator(
    task_id="check_source",
    python_callable=check_postgres_connection,
    dag=dag,
)

t_bronze_ingest = PythonOperator(
    task_id="bronze_ingestion",
    python_callable=run_bronze_ingestion,
    dag=dag,
)

t_validate_bronze = PythonOperator(
    task_id="validate_bronze",
    python_callable=run_data_validation,
    dag=dag,
)

t_silver_transform = PythonOperator(
    task_id="silver_transformation",
    python_callable=run_silver_transformation,
    dag=dag,
)

t_choose_gold_engine = BranchPythonOperator(
    task_id="choose_gold_engine",
    python_callable=choose_gold_engine,
    dag=dag,
)

t_gold_aggregate_spark = PythonOperator(
    task_id="gold_aggregation_spark",
    python_callable=run_gold_aggregation,
    dag=dag,
)

t_gold_aggregate_dbt = PythonOperator(
    task_id="gold_aggregation_dbt",
    python_callable=run_dbt_gold_transformation,
    dag=dag,
)

t_snowflake_load = SnowflakeOperator(
    task_id="snowflake_load",
    sql=SNOWFLAKE_LOAD_SQL,
    snowflake_conn_id="snowflake_healthcare",
    dag=dag,
)
# Only meaningful after the SPARK path (dbt writes directly to Snowflake —
# there's nothing to COPY INTO afterward). Skipped entirely on the dbt path.
t_snowflake_load.trigger_rule = "none_failed_min_one_success"

t_gold_join = EmptyOperator(
    task_id="gold_layer_complete",
    trigger_rule="none_failed_min_one_success",  # succeeds if exactly one branch succeeded, the other was skipped
    dag=dag,
)

t_notify = PythonOperator(
    task_id="notify_success",
    python_callable=notify_success,
    trigger_rule="all_success",
    dag=dag,
)

# ─── DAG Dependencies (Pipeline Order) ───────────────────────────────────────
# Bronze → Silver run unconditionally. Gold then forks into exactly ONE of
# {Spark, dbt} per the choose_gold_engine branch (see its docstring) — this
# is what makes the split-brain Gold-table conflict structurally impossible
# rather than just documented-against.
t_check_source >> t_bronze_ingest >> t_validate_bronze >> t_silver_transform >> t_choose_gold_engine

t_choose_gold_engine >> t_gold_aggregate_spark >> t_snowflake_load >> t_gold_join
t_choose_gold_engine >> t_gold_aggregate_dbt >> t_gold_join

t_gold_join >> t_notify
