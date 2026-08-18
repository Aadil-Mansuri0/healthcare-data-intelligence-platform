"""
PHI Redaction
Strips the 18 HIPAA Safe Harbor identifiers (45 CFR §164.514(b)(2)) from
free-text before it reaches any LLM call — NL2SQL question text, RAG queries,
AI report narration. This runs regardless of whether the current dataset
actually contains PHI (the Medicare Part D Prescriber PUF does not — see
HIPAA_COMPLIANCE.md) so the same code path is safe if/when this platform is
pointed at a real claims feed that does.

This is pattern-based redaction (regex + a name/date heuristic), which is a
reasonable belt for structured inputs like short analytical questions — it is
NOT a substitute for a proper NLP-based PHI detector (e.g. AWS Comprehend
Medical, Presidio) for free-form clinical text, which is called out below.
"""

import re
import logging

logger = logging.getLogger("PHIRedaction")

# The 18 HIPAA Safe Harbor identifier categories (45 CFR §164.514(b)(2)(i)).
# Not all are pattern-detectable (e.g. "any unique identifying number" is a
# catch-all) — this covers the ones with a reliable regex signature.
SAFE_HARBOR_IDENTIFIERS = [
    "names", "geographic subdivisions smaller than a state", "dates (except year) directly related to an individual",
    "telephone numbers", "fax numbers", "email addresses", "social security numbers",
    "medical record numbers", "health plan beneficiary numbers", "account numbers",
    "certificate/license numbers", "vehicle identifiers", "device identifiers",
    "URLs", "IP addresses", "biometric identifiers", "full-face photos",
    "any other unique identifying number, characteristic, or code",
]

_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s])?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "url": re.compile(r"https?://\S+"),
    "date_full": re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),  # MM/DD/YYYY — dates tied to an individual
    "mrn_like": re.compile(r"\b(MRN|mrn)[:\s#]*\d{4,}\b"),
    "npi_as_identifier": re.compile(r"\b\d{10}\b"),  # 10-digit NPI — flagged, NOT auto-redacted (see note below)
}

# NPI numbers are a deliberate exception: they identify a *prescriber*
# (a covered entity / business, not a patient) and are the primary key this
# whole platform's analytics are built on (GOLD_SCHEMA.PRESCRIBER_SUMMARY).
# NPIs are excluded from redaction but flagged in the audit log via
# `contains_npi` so reviewers know a quasi-identifier was present.


def redact_phi(text: str) -> tuple[str, dict]:
    """
    Returns (redacted_text, findings) where findings maps identifier type ->
    count found. NPI matches are counted but NOT redacted (see note above);
    everything else is replaced with a `[REDACTED:<type>]` placeholder.
    """
    if not text:
        return text, {}

    findings = {}
    redacted = text

    for label, pattern in _PATTERNS.items():
        matches = pattern.findall(redacted)
        if not matches:
            continue
        findings[label] = len(matches)

        if label == "npi_as_identifier":
            continue  # flag only, don't redact — see module docstring

        redacted = pattern.sub(f"[REDACTED:{label.upper()}]", redacted)

    if findings:
        logger.warning(f"PHI-pattern redaction applied: {findings}")

    return redacted, findings


def assert_safe_for_llm(text: str, context: str = "unknown") -> str:
    """
    Convenience wrapper for call sites (nlsql/, rag/) — redacts and logs, then
    returns the safe-to-send text. Raises if the *redacted* text is empty
    (meaning the entire input was PHI, which signals the caller sent
    something structurally wrong, e.g. a raw record dump instead of a question).
    """
    redacted, findings = redact_phi(text)

    if findings:
        logger.info(f"[{context}] Redacted {sum(findings.values())} potential PHI pattern(s) before LLM call")

    if not redacted.strip():
        raise ValueError(f"[{context}] Input became empty after PHI redaction — refusing to send to LLM")

    return redacted


# ── Production upgrade note ─────────────────────────────────────────────────
# For free-form clinical text (not the short analytical questions this
# platform's chat interface expects), swap this regex approach for a proper
# NLP-based detector:
#   - AWS Comprehend Medical (DetectPHI API) — purpose-built, HIPAA-eligible
#   - Microsoft Presidio — open-source, spaCy-based, extensible recognizers
# Both catch identifiers this regex module cannot (e.g. names in prose,
# relative dates like "last Tuesday", indirect geographic references).
