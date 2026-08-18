/*
Intermediate model — applies business logic that multiple downstream marts
need (opioid flagging, cost-tier bucketing). Materialized as `ephemeral`
(inlined as a CTE at query time, not a physical table) since nothing queries
it directly — it exists purely for DRY-ness across fct_drug_summary and
fct_state_kpi below.
*/

with drug_claims as (
    select * from {{ ref('stg_prescriber_drug') }}
),

classified as (
    select
        *,
        -- Opioid/pain-management proxy flag — mirrors the logic in
        -- medallion/gold/aggregation.py::build_state_kpi so both transformation
        -- paths (Spark batch, dbt) agree on the same business definition.
        case
            when lower(prescriber_specialty) like '%pain%'
              or lower(prescriber_specialty) like '%anesthesi%'
            then true
            else false
        end as is_pain_management_specialty,

        case
            when avg_cost_per_claim < 20 then 'low'
            when avg_cost_per_claim < 100 then 'medium'
            when avg_cost_per_claim < 1000 then 'high'
            else 'specialty_tier'
        end as cost_tier

    from drug_claims
)

select * from classified
