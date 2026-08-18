"""
Claim Event Schema
Defines the contract for streaming claim events — this is the "data contract"
that was missing from the batch-only version of the pipeline. Producers and
consumers both import this to stay in sync; a schema-registry (Confluent
Schema Registry with Avro/Protobuf) would enforce this at the broker level
in a full production setup — this lightweight version is the dependency-free
equivalent for the same correctness guarantee at the application layer.
"""

from datetime import datetime

REQUIRED_FIELDS = {
    "claim_id": str,
    "prscrbr_npi": int,
    "prscrbr_state_abrvtn": str,
    "gnrc_name": str,
    "brnd_name": str,
    "is_opioid": bool,
    "drug_cost_usd": (int, float),
    "claim_timestamp": str,
}

VALID_STATE_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC","PR",
}


def validate_claim_event(claim: dict) -> list[str]:
    """Returns a list of validation errors; empty list = valid."""
    errors = []

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in claim:
            errors.append(f"Missing required field: {field}")
            continue
        if not isinstance(claim[field], expected_type):
            errors.append(f"Field '{field}' has wrong type: expected {expected_type}, got {type(claim[field])}")

    if "prscrbr_state_abrvtn" in claim and claim["prscrbr_state_abrvtn"] not in VALID_STATE_CODES:
        errors.append(f"Invalid state code: {claim['prscrbr_state_abrvtn']}")

    if "drug_cost_usd" in claim and isinstance(claim["drug_cost_usd"], (int, float)):
        if claim["drug_cost_usd"] < 0:
            errors.append("drug_cost_usd cannot be negative")
        if claim["drug_cost_usd"] > 1_000_000:
            errors.append("drug_cost_usd exceeds sane upper bound (possible data error)")

    if "prscrbr_npi" in claim and isinstance(claim["prscrbr_npi"], int):
        if not (1_000_000_000 <= claim["prscrbr_npi"] <= 9_999_999_999):
            errors.append("prscrbr_npi must be a 10-digit NPI number")

    if "claim_timestamp" in claim:
        try:
            datetime.fromisoformat(claim["claim_timestamp"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            errors.append("claim_timestamp must be a valid ISO 8601 timestamp")

    return errors
