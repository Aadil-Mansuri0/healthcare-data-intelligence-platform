{{ config(materialized='table') }}

with prescribers as (
    select * from {{ ref('stg_prescriber') }}
),

claims_agg as (
    select
        prescriber_npi,
        claim_year,
        sum(total_claims)                as total_claims,
        sum(total_cost_usd)               as total_cost_usd,
        sum(total_beneficiaries)          as total_beneficiaries,
        count(distinct generic_name)      as unique_drugs_prescribed,
        sum(case when is_generic then total_claims else 0 end) as generic_claims
    from {{ ref('int_drug_claims_classified') }}
    group by prescriber_npi, claim_year
),

joined as (
    select
        p.prescriber_npi,
        p.prescriber_last_name,
        p.prescriber_first_name,
        p.prescriber_city,
        p.prescriber_state,
        p.prescriber_specialty,
        c.claim_year,
        c.total_claims,
        c.total_cost_usd,
        c.total_beneficiaries,
        c.unique_drugs_prescribed,
        round(c.generic_claims / nullif(c.total_claims, 0) * 100, 2) as generic_rate,
        rank() over (
            partition by p.prescriber_state, c.claim_year
            order by c.total_cost_usd desc
        ) as state_rank
    from prescribers p
    inner join claims_agg c on p.prescriber_npi = c.prescriber_npi
)

select
    *,
    current_timestamp() as dbt_updated_at
from joined
