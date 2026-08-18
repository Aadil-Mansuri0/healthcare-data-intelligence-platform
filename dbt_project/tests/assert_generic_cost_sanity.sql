-- Custom test: catches the (rare but real) data-quality case where a generic
-- drug's avg_cost_per_claim exceeds $10,000 — almost certainly a unit error
-- (e.g. cents vs dollars) rather than a genuine price, since even the most
-- expensive generic drugs on Part D don't approach specialty-biologic pricing.
-- Fails (returns rows) if any such row exists, surfacing it before it reaches
-- the dashboard.

select
    generic_name,
    claim_year,
    avg_cost_per_claim
from {{ ref('fct_drug_summary') }}
where is_generic = true
  and avg_cost_per_claim > 10000
