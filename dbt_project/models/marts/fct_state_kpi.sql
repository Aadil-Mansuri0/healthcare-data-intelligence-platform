{{
    config(
        materialized='table',
        cluster_by=['claim_year']
    )
}}

with classified as (
    select * from {{ ref('int_drug_claims_classified') }}
),

state_kpi as (
    select
        prescriber_state as state_abrvtn,
        claim_year,
        sum(total_claims)                                                as total_claims,
        sum(total_cost_usd)                                               as total_cost_usd,
        sum(total_beneficiaries)                                          as total_beneficiaries,
        count(distinct prescriber_npi)                                    as total_prescribers,
        count(distinct generic_name)                                      as unique_drugs,
        avg(avg_cost_per_claim)                                            as avg_cost_per_claim,
        sum(case when is_pain_management_specialty then total_claims else 0 end) as pain_specialty_claims
    from classified
    group by prescriber_state, claim_year
),

with_rank as (
    select
        *,
        round(total_cost_usd / nullif(total_beneficiaries, 0), 2) as cost_per_beneficiary,
        rank() over (partition by claim_year order by total_cost_usd desc) as national_rank
    from state_kpi
)

select
    *,
    current_timestamp() as dbt_updated_at
from with_rank
