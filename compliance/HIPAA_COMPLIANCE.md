# HIPAA Compliance Posture

## Scope: is this platform handling PHI?

**The Medicare Part D Prescriber Public Use File this project is built on is
NOT individually identifiable PHI** — CMS publishes it as a de-identified,
aggregated dataset (claim counts, costs, and beneficiary counts are rounded
and low-volume-suppressed specifically so no single patient is identifiable;
see `rag/knowledge_base/documents.py::kb_005` for the suppression rule this
platform already accounts for in its aggregation logic).

**However**, this platform is architected as a template for a real healthcare
data product, and a real deployment would likely ingest actual claims data
containing PHI (patient names, DOB, diagnosis codes, prescriber-patient
relationships). This document describes what changes when that's true, and
what's already in place vs. what a real go-live requires.

---

## What's already in place (works today, PHI or not)

| Safeguard | Implementation |
|---|---|
| Encryption in transit | TLS via Ingress (`infra/k8s/frontend/deployment.yaml` cert-manager) |
| Encryption at rest | S3 SSE-AES256 (`infra/terraform/modules/s3`), Snowflake encrypts at rest by default |
| Access control | JWT + RBAC, 3 least-privilege roles (`api/auth/`) |
| Audit logging (partial) | `AUDIT.AI_QUERY_LOG` records every NL2SQL query, who ran it, and the generated SQL |
| Network isolation | K8s NetworkPolicy default-deny, private EKS subnets, Snowflake role-scoped grants |
| Least-privilege IAM | IRSA — pods assume scoped roles, not node-wide credentials |

## What a real PHI deployment additionally requires (not yet implemented)

| Gap | Why it matters | Where it would go |
|---|---|---|
| **Business Associate Agreement (BAA)** | Legal requirement before any PHI touches AWS/Snowflake/OpenAI — you must have a signed BAA with *every* vendor that can access PHI, including the LLM provider | Organizational/legal, not code — but *blocks* using OpenAI's standard API for PHI-containing prompts (OpenAI's API is not BAA-eligible in the same way Azure OpenAI is) |
| **PHI must never reach the LLM directly** | Sending raw PHI into NL2SQL prompts or RAG context violates HIPAA even with a BAA, unless the LLM vendor is specifically covered | `phi_redaction.py` (this module) — strips/tokenizes identifiers before any text reaches `nlsql/` or `rag/` |
| **Comprehensive audit trail** | HIPAA requires logging *every* access to PHI, not just AI queries — every `SELECT` against a PHI-containing table | `phi_audit_middleware.py` (this module) extends the pattern from `AUDIT.AI_QUERY_LOG` to all API routes |
| **Minimum necessary access** | Role scopes must be reviewed to ensure `analyst`/`viewer` see only de-identified aggregates, never row-level PHI | Extend `AUTH_SCHEMA.ROLES` permissions; add column-level masking policies in Snowflake (`MASKING POLICY`) |
| **Breach notification plan** | 60-day notification requirement if PHI is exposed | Operational runbook — not code |
| **Data retention & disposal policy** | PHI has HIPAA-specific retention/disposal rules distinct from general data lifecycle | `data_retention_policy.sql` (this module) |
| **De-identification safe-harbor check** | If publishing "de-identified" extracts, must strip all 18 HIPAA identifiers, not just names | `phi_redaction.py::SAFE_HARBOR_IDENTIFIERS` |
| **Workforce access logging + periodic review** | Who *can* access PHI and whether that's still appropriate must be reviewed periodically | Process, supported by `AUTH_SCHEMA.USERS.last_login_at` + role audit queries |
| **Encryption key management** | HIPAA favors customer-managed keys (KMS) over default provider encryption for PHI | Upgrade S3/Snowflake to CMK (customer-managed KMS keys) — noted as TODO in `infra/terraform/modules/s3` |

## Concrete code additions in this module

- `phi_redaction.py` — identifies and redacts the 18 HIPAA Safe Harbor
  identifiers from any free-text field before it reaches an LLM prompt
  (NL2SQL question text, RAG queries, AI report narration).
- `phi_audit_middleware.py` — FastAPI middleware that logs every request to
  a PHI-tagged route (path, user, timestamp, IP) to a dedicated audit table,
  independent of the AI-specific `AUDIT.AI_QUERY_LOG`.
- `data_retention_policy.sql` — Snowflake retention/purge policy applied to
  any table tagged as containing PHI.

## What this project does NOT claim

This is a **compliance scaffold**, not a certified-compliant system. Real
HIPAA compliance requires a signed BAA, a formal risk assessment (HIPAA
Security Rule §164.308), a designated Privacy/Security Officer, and typically
a third-party audit. Treat everything in `compliance/` as the engineering
half of that work — the legal/organizational half is out of scope for a
code repository.
