"""
Data Quality DAG — Great Expectations
Runs independently (or is triggered by the main pipeline) to validate
Silver-layer data using the real GE suite, and sends alerts on failure.
"""

from datetime import timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import logging

logger = logging.getLogger("DataQualityDAG")

default_args = {
    "owner": "aadil",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email": ["aadil@healthcare-platform.com"],
}

dag = DAG(
    dag_id="data_quality_ge_suite",
    default_args=default_args,
    description="Great Expectations validation suite on Silver layer",
    schedule_interval=None,  # triggered by healthcare_medallion_pipeline
    start_date=days_ago(1),
    catchup=False,
    tags=["healthcare", "data-quality", "great-expectations"],
)


def run_ge_validation(**context):
    """Executes the Great Expectations suite and pushes results to XCom."""
    import subprocess
    execution_date = context["ds"]

    result = subprocess.run(
        ["python", "/opt/airflow/great_expectations/ge_silver_suite.py", "--date", execution_date],
        capture_output=True, text=True,
    )
    logger.info(result.stdout)

    if result.returncode != 0:
        logger.error(result.stderr)
        raise Exception(f"❌ Great Expectations validation FAILED for {execution_date}")

    context["ti"].xcom_push(key="ge_validation_status", value="passed")
    logger.info(f"✅ Great Expectations validation PASSED for {execution_date}")


def run_ai_quality_check(**context):
    """Calls the AI-augmented anomaly detector as a secondary quality signal."""
    import requests
    import os

    execution_date = context["ds"]
    year = int(execution_date.split("-")[0])

    api_base = os.environ.get("API_BASE_URL", "http://api:8000")
    try:
        resp = requests.get(
            f"{api_base}/api/ai/data-quality-check",
            params={"year": year},
            headers={"Authorization": f"Bearer {os.environ.get('SERVICE_ACCOUNT_TOKEN', '')}"},
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"AI Quality Check status: {result.get('status')}")
        if result.get("status") == "issues_found":
            logger.warning(f"AI-detected issues: {result.get('ai_explanation')}")
    except Exception as e:
        logger.warning(f"AI quality check call failed (non-blocking): {e}")


t_ge_validation = PythonOperator(
    task_id="run_great_expectations_suite",
    python_callable=run_ge_validation,
    dag=dag,
)

t_ai_quality_check = PythonOperator(
    task_id="run_ai_quality_check",
    python_callable=run_ai_quality_check,
    dag=dag,
)

t_ge_validation >> t_ai_quality_check
