-- ═══════════════════════════════════════════════════════════════════════════
-- Snowflake Setup — Auth & Audit Schemas
-- Supports JWT auth (user lookup) and AI query audit logging
-- ═══════════════════════════════════════════════════════════════════════════

USE DATABASE HEALTHCARE_DW;

CREATE SCHEMA IF NOT EXISTS AUTH_SCHEMA;
CREATE SCHEMA IF NOT EXISTS AUDIT;

-- ─── Users ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS AUTH_SCHEMA.USERS (
    username         STRING PRIMARY KEY,
    email            STRING NOT NULL,
    full_name        STRING,
    hashed_password  STRING NOT NULL,
    role             STRING NOT NULL DEFAULT 'viewer',
    is_active        BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    last_login_at    TIMESTAMP_NTZ
);

-- ─── Roles (reference / permission metadata) ───────────────────────────────
CREATE TABLE IF NOT EXISTS AUTH_SCHEMA.ROLES (
    role_name    STRING PRIMARY KEY,
    description  STRING,
    permissions  ARRAY
);

INSERT INTO AUTH_SCHEMA.ROLES (role_name, description, permissions) VALUES
    ('admin', 'Full platform access — user mgmt, all data, AI quality checks',
        ARRAY_CONSTRUCT('read:all', 'write:users', 'run:ai_quality_check', 'trigger:pipeline')),
    ('analyst', 'Read all Gold data + AI assistant, insights, reports',
        ARRAY_CONSTRUCT('read:all', 'run:nl2sql', 'run:insights', 'run:reports', 'run:recommendations')),
    ('viewer', 'Read-only dashboard access, no AI features',
        ARRAY_CONSTRUCT('read:dashboards'));

-- ─── AI Query Audit Log ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS AUDIT.AI_QUERY_LOG (
    query_id        STRING DEFAULT UUID_STRING(),
    username        STRING,
    question        STRING,
    generated_sql   STRING,
    row_count       NUMBER,
    status          STRING,  -- success | rejected | failed
    created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ─── Seed demo users (passwords hashed at app layer — placeholders here) ────
-- NOTE: In production, insert via the /api/auth/users admin endpoint, which
-- hashes with bcrypt at request time. Never insert plaintext-derived hashes
-- directly via SQL outside of controlled seeding scripts.

GRANT USAGE ON SCHEMA AUTH_SCHEMA TO ROLE HEALTHCARE_READER;
GRANT SELECT ON AUTH_SCHEMA.USERS TO ROLE HEALTHCARE_READER;
GRANT USAGE ON SCHEMA AUDIT TO ROLE HEALTHCARE_READER;
GRANT SELECT, INSERT ON AUDIT.AI_QUERY_LOG TO ROLE HEALTHCARE_READER;
