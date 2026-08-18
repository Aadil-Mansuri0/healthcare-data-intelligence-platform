"""
Data Lineage — OpenLineage Integration
Automatically emits lineage events (which datasets each Airflow task reads/
writes) to Marquez, so "where did this number come from" is answerable by
clicking through a lineage graph instead of grepping DAG code.

This module is imported by the Airflow DAGs to manually emit lineage for the
Spark-based tasks (OpenLineage's automatic Airflow instrumentation covers
task-level lineage out of the box via the openlineage-airflow provider; this
adds dataset-level detail for the medallion layers specifically).
"""

import os
import logging
from datetime import datetime
from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Run, Job
from openlineage.client.facet import (
    SqlJobFacet, DataQualityMetricsInputDatasetFacet, SchemaDatasetFacet, SchemaField,
)
from openlineage.client.uuid import generate_new_uuid

logger = logging.getLogger("DataLineage")

MARQUEZ_URL = os.environ.get("MARQUEZ_URL", "http://marquez:5000")
NAMESPACE = "healthcare_medallion_pipeline"

_client = None


def get_lineage_client() -> OpenLineageClient:
    global _client
    if _client is None:
        _client = OpenLineageClient(url=MARQUEZ_URL)
    return _client


def _dataset_uri(layer: str, table: str) -> str:
    return f"s3://healthcare-datalake/{layer}/{table}"


def emit_layer_transition(
    job_name: str,
    input_layer: str,
    input_table: str,
    output_layer: str,
    output_table: str,
    row_count_in: int,
    row_count_out: int,
    run_id: str | None = None,
):
    """
    Emits a START + COMPLETE lineage event pair for a Bronze→Silver or
    Silver→Gold transformation, recording the input/output datasets and
    row-count facts — enough for Marquez to render "this Gold table traces
    back through these Silver/Bronze datasets to this PostgreSQL source".
    """
    client = get_lineage_client()
    run_id = run_id or str(generate_new_uuid())

    job = Job(namespace=NAMESPACE, name=job_name)
    run = Run(runId=run_id)

    input_dataset = {
        "namespace": NAMESPACE,
        "name": _dataset_uri(input_layer, input_table),
        "facets": {
            "dataQualityMetrics": DataQualityMetricsInputDatasetFacet(
                rowCount=row_count_in, bytes=None,
            )
        },
    }
    output_dataset = {
        "namespace": NAMESPACE,
        "name": _dataset_uri(output_layer, output_table),
        "facets": {
            "schema": SchemaDatasetFacet(fields=[
                SchemaField(name="_gold_ts", type="TIMESTAMP"),
            ]),
        },
    }

    for state in (RunState.START, RunState.COMPLETE):
        event = RunEvent(
            eventType=state,
            eventTime=datetime.utcnow().isoformat() + "Z",
            run=run,
            job=job,
            producer="https://github.com/<your-org>/healthcare_advanced",
            inputs=[input_dataset],
            outputs=[output_dataset] if state == RunState.COMPLETE else [],
        )
        try:
            client.emit(event)
        except Exception as e:
            # Lineage emission failures should never fail the actual pipeline —
            # observability is best-effort, not a hard dependency.
            logger.warning(f"Lineage emission failed (non-fatal): {e}")

    logger.info(
        f"Lineage recorded: {input_layer}/{input_table} ({row_count_in} rows) "
        f"→ {output_layer}/{output_table} ({row_count_out} rows) [job: {job_name}]"
    )
    return run_id


def emit_dbt_lineage_note():
    """
    dbt models get lineage automatically via `dbt-ol` (the OpenLineage dbt
    wrapper) instead of manual emission — run dbt through it in the Airflow
    dbt task:
        dbt-ol run --project-dir dbt_project
    in place of `dbt run`. This captures full column-level lineage from dbt's
    own manifest, which is richer than what we hand-emit for the Spark jobs.
    """
    pass
