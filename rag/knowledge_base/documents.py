"""
Healthcare Knowledge Base — Source Documents for RAG Ingestion
These are domain-knowledge chunks (drug classes, CMS policy context, ICD-10
categories relevant to Medicare Part D) that the AI assistant retrieves
to ground its answers beyond raw SQL results — e.g. "why does the opioid
prescribing rate matter" or "what counts as a generic substitution".

In production these would be sourced from CMS.gov, FDA Orange Book, and
internal policy docs. Chunked to ~150-300 words each for good retrieval
granularity (not too broad, not too fragmented).
"""

KNOWLEDGE_DOCUMENTS = [
    {
        "id": "kb_001",
        "category": "drug_classification",
        "text": (
            "Generic drugs contain the same active ingredient, dosage form, and strength "
            "as their brand-name equivalents, and are required by the FDA to demonstrate "
            "bioequivalence. Medicare Part D typically reimburses generics at a lower rate "
            "because manufacturers do not bear the same R&D and marketing costs as brand "
            "originators. A high generic dispensing rate (GDR) in a prescriber's claims is "
            "generally viewed as a cost-efficiency indicator, though it must be interpreted "
            "alongside clinical appropriateness — not all conditions have a generic option."
        ),
    },
    {
        "id": "kb_002",
        "category": "opioid_monitoring",
        "text": (
            "CMS monitors opioid prescribing patterns under Part D through metrics like "
            "morphine milligram equivalent (MME) per day and the number of prescribers per "
            "beneficiary. Prescribers with unusually high claim volumes for Schedule II "
            "opioids relative to their specialty peer group are flagged for review under "
            "CMS's Overutilization Monitoring System (OMS). Pain management and anesthesiology "
            "specialties naturally show higher opioid claim volumes and should be benchmarked "
            "against specialty-specific norms rather than the general population."
        ),
    },
    {
        "id": "kb_003",
        "category": "cost_drivers",
        "text": (
            "The largest driver of Part D drug spend is typically a small number of "
            "high-cost specialty and biologic drugs (e.g. for autoimmune conditions, cancer, "
            "hepatitis C) rather than high claim volume. A drug can rank low in total claims "
            "but still be a top cost driver due to per-claim price. When analyzing 'total cost "
            "of drug' figures, always cross-reference against claim count and cost-per-claim "
            "to distinguish volume-driven spend from price-driven spend."
        ),
    },
    {
        "id": "kb_004",
        "category": "geographic_variation",
        "text": (
            "State-level Part D spending varies due to demographics (elderly population "
            "density), regional prescribing culture, cost-of-living-adjusted drug pricing, "
            "and the mix of urban vs. rural prescriber access. States with older populations "
            "(e.g. Florida, Arizona) typically show higher total beneficiary counts and "
            "aggregate spend, which should not be conflated with higher per-beneficiary cost "
            "efficiency. Always normalize state comparisons by cost-per-beneficiary, not raw "
            "totals, when assessing efficiency rather than volume."
        ),
    },
    {
        "id": "kb_005",
        "category": "data_quality_context",
        "text": (
            "Medicare Part D Prescriber Public Use Files suppress claim counts below 11 for "
            "beneficiary privacy (the CMS 'low-volume suppression' rule). This means Silver "
            "and Gold layer aggregates may slightly undercount true totals for rare drug/"
            "prescriber combinations. Analysts should treat state- and national-level "
            "aggregates as directionally accurate but not treat small subgroup counts (e.g. "
            "a single rural prescriber's totals) as complete."
        ),
    },
    {
        "id": "kb_006",
        "category": "prescriber_types",
        "text": (
            "CMS prescriber taxonomy groups providers into specialties such as Family "
            "Medicine, Internal Medicine, Cardiology, Pain Management, and Nurse "
            "Practitioner. Nurse Practitioners and Physician Assistants have expanded "
            "prescribing authority in most states as of the mid-2020s and often show growing "
            "claim volumes in primary-care-adjacent categories. When comparing prescriber "
            "cost or volume across specialties, note that scope-of-practice differences "
            "across states affect what a given specialty is legally permitted to prescribe."
        ),
    },
    {
        "id": "kb_007",
        "category": "cost_saving_strategy",
        "text": (
            "Common Part D cost-containment strategies include: (1) generic substitution "
            "programs, (2) prior authorization for high-cost specialty drugs, (3) step "
            "therapy requiring a lower-cost option be tried first, and (4) preferred "
            "pharmacy networks. When recommending savings opportunities from data, the "
            "highest-confidence signal is a large brand-vs-generic cost gap on a drug with "
            "high claim volume, since the total dollar impact scales with volume."
        ),
    },
]
