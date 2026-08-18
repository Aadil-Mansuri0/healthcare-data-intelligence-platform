-- ═══════════════════════════════════════════════════════════════════════════
-- HIPAA-Aligned Data Retention & Audit Tables
-- See compliance/HIPAA_COMPLIANCE.md for the policy this DDL implements.
-- ═══════════════════════════════════════════════════════════════════════════

USE DATABASE HEALTHCARE_DW;

-- ─── PHI Access Audit Log ───────────────────────────────────────────────────
-- Written by compliance/phi_audit_middleware.py on every request to a
-- PHI-adjacent route. Separate from AUDIT.AI_QUERY_LOG (which captures the
-- generated SQL specifically) — this captures ALL access, AI-assisted or not.
CREATE TABLE IF NOT EXISTS AUDIT.PHI_ACCESS_LOG (
    log_id          STRING DEFAULT UUID_STRING(),
    username        STRING,
    path            STRING,
    method          STRING,
    status_code     NUMBER,
    duration_ms     FLOAT,
    client_ip       STRING,
    accessed_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- HIPAA requires audit logs be retained a minimum of 6 years (45 CFR
-- §164.316(b)(2)(i)). Snowflake Time Travel is NOT a retention mechanism on
-- its own (it protects against accidental deletes for a short window, not
-- long-term archival) — retention here is enforced by simply never deleting
-- rows younger than 6 years, combined with a scheduled task that archives
-- (not deletes) anything older to cheaper storage.
CREATE OR REPLACE TASK AUDIT.ARCHIVE_OLD_PHI_LOGS
  WAREHOUSE = HEALTHCARE_WH
  SCHEDULE = 'USING CRON 0 3 1 * * UTC'  -- monthly, 3 AM UTC on the 1st
AS
  INSERT INTO AUDIT.PHI_ACCESS_LOG_ARCHIVE
  SELECT * FROM AUDIT.PHI_ACCESS_LOG
  WHERE accessed_at < DATEADD(year, -6, CURRENT_TIMESTAMP());
  -- Note: intentionally NOT deleting from the source table in the same task —
  -- deletion of audit records requires a documented, approved retention
  -- policy sign-off, not an automated task. Archive first; delete is a
  -- separate, deliberately manual step after legal/compliance review.

CREATE TABLE IF NOT EXISTS AUDIT.PHI_ACCESS_LOG_ARCHIVE LIKE AUDIT.PHI_ACCESS_LOG;

-- ─── Column-level masking (minimum-necessary-access enforcement) ──────────
-- If/when real per-patient PHI columns exist, apply a masking policy so that
-- the `viewer` role (dashboards-only, no AI) never sees raw identifiers even
-- if a future query accidentally selects them. Example pattern (no PHI
-- columns exist in the current Gold schema — this is the template to reuse):
--
-- CREATE MASKING POLICY IF NOT EXISTS mask_patient_identifier AS (val STRING) RETURNS STRING ->
--   CASE
--     WHEN CURRENT_ROLE() IN ('HEALTHCARE_READER_ADMIN') THEN val
--     ELSE '***MASKED***'
--   END;
-- ALTER TABLE <table> MODIFY COLUMN <phi_column> SET MASKING POLICY mask_patient_identifier;

-- ─── Grants ─────────────────────────────────────────────────────────────────
GRANT SELECT, INSERT ON AUDIT.PHI_ACCESS_LOG TO ROLE HEALTHCARE_READER;
GRANT SELECT ON AUDIT.PHI_ACCESS_LOG_ARCHIVE TO ROLE HEALTHCARE_READER;
