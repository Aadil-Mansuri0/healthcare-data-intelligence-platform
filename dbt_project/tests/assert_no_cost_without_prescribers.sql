-- Custom test: flags any state-year row with drug spend but zero recorded
-- prescribers — a data integrity impossibility that would indicate a broken
-- join upstream. dbt tests pass when the query returns ZERO rows.

select
    state_abrvtn,
    claim_year,
    total_cost_usd,
    total_prescribers
from {{ ref('fct_state_kpi') }}
where total_cost_usd > 0
  and total_prescribers = 0
