/*
Staging model — thin 1:1 pass-through over the Silver source with renamed/
typed columns. Staging models never contain business logic (joins,
aggregations); they exist purely to give downstream models a stable,
well-named contract even if the upstream Spark output column names change.
*/

with source as (
    select * from {{ source('silver', 'prescriber_drug') }}
),

renamed as (
    select
        prscrbr_npi                                    as prescriber_npi,
        brnd_name                                       as brand_name,
        gnrc_name                                        as generic_name,
        prscrbr_state_abrvtn                            as prescriber_state,
        prscrbr_type                                     as prescriber_specialty,
        year                                              as claim_year,
        cast(tot_clms as number(18,0))                   as total_claims,
        cast(tot_drug_cst as float)                       as total_cost_usd,
        cast(tot_benes as number(18,0))                   as total_beneficiaries,
        cast(avg_cost_per_claim as float)                 as avg_cost_per_claim,
        is_generic,
        _silver_ts                                        as silver_loaded_at
    from source
)

select * from renamed
