-- ═══════════════════════════════════════════════════════════════════════════
-- Snowflake Setup — Healthcare Data Warehouse
-- Run once to provision the warehouse, database, schemas, stage, and tables
-- ═══════════════════════════════════════════════════════════════════════════

-- 1. Warehouse
CREATE WAREHOUSE IF NOT EXISTS HEALTHCARE_WH
  WAREHOUSE_SIZE = 'X-SMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

-- 2. Database & Schemas (mirrors Medallion Architecture)
CREATE DATABASE IF NOT EXISTS HEALTHCARE_DW;
USE DATABASE HEALTHCARE_DW;

CREATE SCHEMA IF NOT EXISTS BRONZE_SCHEMA;
CREATE SCHEMA IF NOT EXISTS SILVER_SCHEMA;
CREATE SCHEMA IF NOT EXISTS GOLD_SCHEMA;

-- 3. S3 Stage (external stage pointing to the data lake)
CREATE OR REPLACE STAGE PUBLIC.S3_STAGE
  URL = 's3://healthcare-datalake/'
  CREDENTIALS = (AWS_KEY_ID = '<AWS_KEY_ID>' AWS_SECRET_KEY = '<AWS_SECRET_KEY>')
  FILE_FORMAT = (TYPE = PARQUET);

-- ─── GOLD SCHEMA TABLES ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS GOLD_SCHEMA.DRUG_SUMMARY (
    gnrc_name             STRING,
    brnd_name             STRING,
    year                  INT,
    is_generic            BOOLEAN,
    total_claims          NUMBER(18,0),
    total_cost_usd        FLOAT,
    total_beneficiaries   NUMBER(18,0),
    avg_cost_per_claim    FLOAT,
    unique_prescribers    NUMBER(18,0),
    cost_rank             INT,
    _gold_ts              TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS GOLD_SCHEMA.PRESCRIBER_SUMMARY (
    prscrbr_npi              NUMBER(18,0),
    year                     INT,
    total_claims             NUMBER(18,0),
    total_cost_usd           FLOAT,
    total_beneficiaries      NUMBER(18,0),
    unique_drugs_prescribed  NUMBER(18,0),
    generic_claims           NUMBER(18,0),
    prscrbr_last_org_name    STRING,
    prscrbr_first_name       STRING,
    prscrbr_state_abrvtn     STRING(2),
    prscrbr_type             STRING,
    prscrbr_city             STRING,
    generic_rate             FLOAT,
    state_rank                INT,
    _gold_ts                 TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS GOLD_SCHEMA.STATE_KPI (
    state_abrvtn             STRING(2),
    year                     INT,
    total_claims             NUMBER(18,0),
    total_cost_usd           FLOAT,
    total_beneficiaries      NUMBER(18,0),
    total_prescribers        NUMBER(18,0),
    unique_drugs             NUMBER(18,0),
    avg_cost_per_claim       FLOAT,
    pain_specialty_claims    NUMBER(18,0),
    cost_per_beneficiary     FLOAT,
    national_rank             INT,
    _gold_ts                 TIMESTAMP_NTZ
);

-- ─── Roles & Access ────────────────────────────────────────────────────────
CREATE ROLE IF NOT EXISTS HEALTHCARE_READER;
GRANT USAGE ON WAREHOUSE HEALTHCARE_WH TO ROLE HEALTHCARE_READER;
GRANT USAGE ON DATABASE HEALTHCARE_DW TO ROLE HEALTHCARE_READER;
GRANT USAGE ON SCHEMA GOLD_SCHEMA TO ROLE HEALTHCARE_READER;
GRANT SELECT ON ALL TABLES IN SCHEMA GOLD_SCHEMA TO ROLE HEALTHCARE_READER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA GOLD_SCHEMA TO ROLE HEALTHCARE_READER;

-- ─── Time Travel (for accidental delete recovery) ─────────────────────────
ALTER TABLE GOLD_SCHEMA.DRUG_SUMMARY SET DATA_RETENTION_TIME_IN_DAYS = 7;
ALTER TABLE GOLD_SCHEMA.PRESCRIBER_SUMMARY SET DATA_RETENTION_TIME_IN_DAYS = 7;
ALTER TABLE GOLD_SCHEMA.STATE_KPI SET DATA_RETENTION_TIME_IN_DAYS = 7;
