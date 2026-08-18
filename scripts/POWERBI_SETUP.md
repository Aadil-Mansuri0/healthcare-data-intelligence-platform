# 📊 Power BI Integration Guide

## Connect Power BI Desktop to Snowflake GOLD_SCHEMA

### Step 1: Get Data → Snowflake Connector
1. Open Power BI Desktop → **Get Data** → search **Snowflake**
2. Enter:
   - **Server**: `<your_account>.snowflakecomputing.com`
   - **Warehouse**: `HEALTHCARE_WH`
   - **Role** (optional): `HEALTHCARE_READER`

### Step 2: Authenticate
- Use **Username/Password** (service account recommended) or **SSO** if your org supports it.

### Step 3: Select Tables (Import or DirectQuery)
Navigator will show `HEALTHCARE_DW` → select:
- `GOLD_SCHEMA.DRUG_SUMMARY`
- `GOLD_SCHEMA.PRESCRIBER_SUMMARY`
- `GOLD_SCHEMA.STATE_KPI`

> **Recommendation**: Use **DirectQuery** mode so the dashboard always reflects the latest Gold-layer refresh from Airflow, without manual re-imports.

### Step 4: Build Relationships
In Power BI Model view, link:
```
DRUG_SUMMARY[year]        ←→ STATE_KPI[year]
PRESCRIBER_SUMMARY[year]  ←→ STATE_KPI[year]
PRESCRIBER_SUMMARY[prscrbr_state_abrvtn] ←→ STATE_KPI[state_abrvtn]
```

### Step 5: Suggested Visuals
| Visual | Fields |
|---|---|
| **Map (Filled Map)** | `state_abrvtn` (location) + `total_cost_usd` (color saturation) |
| **Bar Chart** | Top 10 drugs by `total_cost_usd` |
| **KPI Cards** | Sum of `total_beneficiaries`, `total_claims`, avg `cost_per_beneficiary` |
| **Line Chart** | `total_cost_usd` trend by `year` |
| **Donut Chart** | Generic vs Brand claim share (`is_generic`) |
| **Table + Conditional Formatting** | Top prescribers ranked by `state_rank` |

### Step 6: Scheduled Refresh (Power BI Service)
1. Publish report to Power BI Service
2. Go to **Dataset Settings** → **Scheduled Refresh**
3. Set refresh to run **after** your Airflow DAG's daily 2 AM IST completion — e.g. schedule Power BI refresh for **3:30 AM IST** to guarantee Gold data has landed.
4. Add on-premises data gateway only if Snowflake network policy requires it (usually not needed since Snowflake is cloud-native).

### Step 7: Row-Level Security (Optional, enterprise touch)
Create a Snowflake secure view filtering by region, and set up RLS roles in Power BI Model view if you want to demo access-control awareness in your report/viva.
