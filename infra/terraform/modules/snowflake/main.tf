/*
Snowflake Module — Terraform-managed warehouse/database/schema/role setup.
Replaces manual `snowsql -f scripts/snowflake_setup.sql` execution with
version-controlled, plan-reviewable infrastructure. The raw .sql files under
/scripts are kept as a manual-run fallback for environments without the
Snowflake Terraform provider configured (e.g. quick local demos).
*/

variable "warehouse_size" {
  type    = string
  default = "XSMALL"
}

variable "environment" {
  type = string
}

resource "snowflake_warehouse" "healthcare_wh" {
  name           = "HEALTHCARE_WH_${upper(var.environment)}"
  warehouse_size = var.warehouse_size
  auto_suspend   = 60
  auto_resume    = true
  initially_suspended = true
}

resource "snowflake_database" "healthcare_dw" {
  name = "HEALTHCARE_DW_${upper(var.environment)}"
}

resource "snowflake_schema" "bronze" {
  database = snowflake_database.healthcare_dw.name
  name     = "BRONZE_SCHEMA"
}

resource "snowflake_schema" "silver" {
  database = snowflake_database.healthcare_dw.name
  name     = "SILVER_SCHEMA"
}

resource "snowflake_schema" "gold" {
  database = snowflake_database.healthcare_dw.name
  name     = "GOLD_SCHEMA"

  data_retention_time_in_days = 7  # Time Travel window for accidental-delete recovery
}

resource "snowflake_schema" "auth" {
  database = snowflake_database.healthcare_dw.name
  name     = "AUTH_SCHEMA"
}

resource "snowflake_schema" "audit" {
  database = snowflake_database.healthcare_dw.name
  name     = "AUDIT"
}

# ─── Least-privilege reader role for the FastAPI service ──────────────────────
resource "snowflake_role" "healthcare_reader" {
  name = "HEALTHCARE_READER_${upper(var.environment)}"
}

resource "snowflake_warehouse_grant" "reader_wh_usage" {
  warehouse_name = snowflake_warehouse.healthcare_wh.name
  privilege      = "USAGE"
  roles          = [snowflake_role.healthcare_reader.name]
}

resource "snowflake_database_grant" "reader_db_usage" {
  database_name = snowflake_database.healthcare_dw.name
  privilege     = "USAGE"
  roles         = [snowflake_role.healthcare_reader.name]
}

resource "snowflake_schema_grant" "reader_gold_usage" {
  database_name = snowflake_database.healthcare_dw.name
  schema_name   = snowflake_schema.gold.name
  privilege     = "USAGE"
  roles         = [snowflake_role.healthcare_reader.name]
}

resource "snowflake_table_grant" "reader_gold_select" {
  database_name = snowflake_database.healthcare_dw.name
  schema_name   = snowflake_schema.gold.name
  privilege     = "SELECT"
  roles         = [snowflake_role.healthcare_reader.name]
  on_future     = true  # applies to tables created after this grant too
}

# ─── Writer role for the Airflow pipeline (loads Gold layer daily) ────────────
resource "snowflake_role" "healthcare_pipeline_writer" {
  name = "HEALTHCARE_PIPELINE_WRITER_${upper(var.environment)}"
}

resource "snowflake_schema_grant" "writer_all_schemas" {
  for_each = toset([
    snowflake_schema.bronze.name,
    snowflake_schema.silver.name,
    snowflake_schema.gold.name,
  ])
  database_name = snowflake_database.healthcare_dw.name
  schema_name   = each.value
  privilege     = "USAGE"
  roles         = [snowflake_role.healthcare_pipeline_writer.name]
}

resource "snowflake_table_grant" "writer_insert_gold" {
  database_name = snowflake_database.healthcare_dw.name
  schema_name   = snowflake_schema.gold.name
  privilege     = "INSERT"
  roles         = [snowflake_role.healthcare_pipeline_writer.name]
  on_future     = true
}

output "warehouse_name" {
  value = snowflake_warehouse.healthcare_wh.name
}

output "database_name" {
  value = snowflake_database.healthcare_dw.name
}

output "reader_role_name" {
  value = snowflake_role.healthcare_reader.name
}
