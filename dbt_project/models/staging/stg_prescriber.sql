with source as (
    select * from {{ source('silver', 'prescriber') }}
),

renamed as (
    select
        prscrbr_npi              as prescriber_npi,
        prscrbr_last_org_name    as prescriber_last_name,
        prscrbr_first_name       as prescriber_first_name,
        prscrbr_city             as prescriber_city,
        prscrbr_state_abrvtn     as prescriber_state,
        prscrbr_type             as prescriber_specialty,
        _silver_ts                as silver_loaded_at
    from source
)

select * from renamed
