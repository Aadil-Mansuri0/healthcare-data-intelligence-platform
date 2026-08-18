/*
Mart: fct_drug_summary — the dbt-managed equivalent of
medallion/gold/aggregation.py::build_drug_summary. Two transformation paths
exist deliberately: Spark handles the 25M-row Silver cleaning at scale where
DataFrame partitioning matters; dbt handles this Gold-layer aggregation where
SQL is more concise and the win is version-controlled, tested, documented
business logic that analysts (not just data engineers) can read and modify.

In a real rollout, pick ONE as the source of truth per table to avoid split-
brain — the recommendation here is: dbt owns Gold, Spark stops writing Gold
directly and instead the Airflow DAG's gold_aggregation task is replaced with
a `dbt run` step. Both implementations are kept in this repo to demonstrate
the pattern; see README dbt section for the migration note.
*/

{{
    config(
        materialized='table',
        cluster_by=['claim_year']
    )
}}

with classified as (
    select * from {{ ref('int_drug_claims_classified') }}
),

drug_summary as (
    select
        generic_name,
        brand_name,
        claim_year,
        is_generic,
        sum(total_claims)                          as total_claims,
        sum(total_cost_usd)                         as total_cost_usd,
        sum(total_beneficiaries)                    as total_beneficiaries,
        avg(avg_cost_per_claim)                     as avg_cost_per_claim,
        count(distinct prescriber_npi)              as unique_prescribers,
        rank() over (
            partition by claim_year
            order by sum(total_cost_usd) desc
        )                                            as cost_rank
    from classified
    group by generic_name, brand_name, claim_year, is_generic
)

select
    *,
    current_timestamp() as dbt_updated_at
from drug_summary
