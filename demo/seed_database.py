"""
Demo Database Seeder
Creates demo/healthcare_demo.db (SQLite) with the same logical schema as the
Snowflake GOLD_SCHEMA tables (scripts/snowflake_setup.sql), populated with
realistic synthetic data — same shape/scale-down of the real Medicare Part D
aggregates, generated deterministically (fixed random seed) so demo runs are
reproducible.

Note on auth: demo mode does NOT seed a users table here. Login already has
a working fallback for exactly this situation — api/auth/user_store.py's
get_user_by_username() tries the (Snowflake/demo-SQLite) AUTH_SCHEMA.USERS
query first, and on failure (which it always will be in demo mode, since
this seeder deliberately doesn't create that table) falls back to a
hardcoded 3-account set with real bcrypt hashes computed via the same
hash_password() function production uses. Duplicating that here would be
redundant and a second place for the demo accounts to drift out of sync.

Run: python demo/seed_database.py
"""

import sqlite3
import random
from pathlib import Path

random.seed(42)  # reproducible demo data across runs

DB_PATH = Path(__file__).parent / "healthcare_demo.db"

STATES = ["TX", "CA", "FL", "NY", "PA", "OH", "IL", "GA", "NC", "MI",
          "AZ", "WA", "TN", "MA", "IN", "MO", "MD", "WI", "CO", "MN"]

DRUGS = [
    # (generic, brand, is_generic, base_cost_per_claim)
    ("LISINOPRIL", "PRINIVIL", True, 8.5),
    ("ATORVASTATIN", "LIPITOR", True, 12.0),
    ("METFORMIN", "GLUCOPHAGE", True, 6.0),
    ("AMLODIPINE", "NORVASC", True, 9.0),
    ("OMEPRAZOLE", "PRILOSEC", True, 10.5),
    ("LEVOTHYROXINE", "SYNTHROID", True, 11.0),
    ("GABAPENTIN", "NEURONTIN", True, 14.0),
    ("HYDROCHLOROTHIAZIDE", "MICROZIDE", True, 7.5),
    ("SERTRALINE", "ZOLOFT", True, 13.0),
    ("OXYCODONE", "OXYCONTIN", False, 185.0),
    ("INSULIN GLARGINE", "LANTUS", False, 320.0),
    ("ADALIMUMAB", "HUMIRA", False, 5800.0),
    ("APIXABAN", "ELIQUIS", False, 520.0),
    ("EMPAGLIFLOZIN", "JARDIANCE", False, 580.0),
    ("SEMAGLUTIDE", "OZEMPIC", False, 935.0),
]

SPECIALTIES = [
    "Family Medicine", "Internal Medicine", "Cardiology", "Endocrinology",
    "Pain Management", "Anesthesiology", "Psychiatry", "Nurse Practitioner",
]

YEARS = [2022, 2023, 2024]


def create_schema(conn: sqlite3.Connection):
    conn.executescript("""
    DROP TABLE IF EXISTS drug_summary;
    DROP TABLE IF EXISTS prescriber_summary;
    DROP TABLE IF EXISTS state_kpi;

    CREATE TABLE drug_summary (
        gnrc_name TEXT, brnd_name TEXT, year INTEGER, is_generic INTEGER,
        total_claims INTEGER, total_cost_usd REAL, total_beneficiaries INTEGER,
        avg_cost_per_claim REAL, unique_prescribers INTEGER, cost_rank INTEGER
    );

    CREATE TABLE prescriber_summary (
        prscrbr_npi INTEGER, year INTEGER, prscrbr_last_org_name TEXT,
        prscrbr_first_name TEXT, prscrbr_state_abrvtn TEXT, prscrbr_type TEXT,
        prscrbr_city TEXT, total_claims INTEGER, total_cost_usd REAL,
        total_beneficiaries INTEGER, unique_drugs_prescribed INTEGER,
        generic_rate REAL, state_rank INTEGER
    );

    CREATE TABLE state_kpi (
        state_abrvtn TEXT, year INTEGER, total_claims INTEGER,
        total_cost_usd REAL, total_beneficiaries INTEGER, total_prescribers INTEGER,
        unique_drugs INTEGER, avg_cost_per_claim REAL, cost_per_beneficiary REAL,
        national_rank INTEGER, pain_specialty_claims INTEGER
    );
    """)


def seed_drug_summary(conn: sqlite3.Connection):
    rows = []
    for year in YEARS:
        year_costs = []
        for gnrc, brnd, is_generic, base_cost in DRUGS:
            claims = random.randint(5_000, 400_000) if is_generic else random.randint(500, 50_000)
            cost_variance = random.uniform(0.85, 1.15)
            cost_per_claim = round(base_cost * cost_variance, 2)
            total_cost = round(claims * cost_per_claim, 2)
            beneficiaries = int(claims * random.uniform(0.6, 0.9))
            prescribers = random.randint(200, 15_000)
            year_costs.append((gnrc, brnd, year, int(is_generic), claims, total_cost,
                                beneficiaries, cost_per_claim, prescribers))

        # Rank within year by total_cost_usd desc
        year_costs.sort(key=lambda r: -r[5])
        for rank, row in enumerate(year_costs, start=1):
            rows.append(row + (rank,))

    conn.executemany(
        "INSERT INTO drug_summary VALUES (?,?,?,?,?,?,?,?,?,?)", rows
    )


LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Wilson", "Anderson", "Taylor", "Thomas", "Moore"]
FIRST_NAMES = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
               "Linda", "David", "Elizabeth", "Sarah", "Priya", "Wei", "Aadil"]
CITIES = {"TX": "Austin", "CA": "Sacramento", "FL": "Miami", "NY": "Albany",
          "PA": "Philadelphia", "OH": "Columbus", "IL": "Chicago", "GA": "Atlanta"}


def seed_prescriber_and_state(conn: sqlite3.Connection):
    prescriber_rows = []
    state_agg = {}  # (state, year) -> accumulator

    npi_counter = 1_000_000_000
    for year in YEARS:
        state_prescribers = {s: [] for s in STATES}

        for _ in range(600):  # 600 prescribers per year across all states
            npi_counter += random.randint(1, 5)
            state = random.choice(STATES)
            specialty = random.choice(SPECIALTIES)
            claims = random.randint(50, 8_000)
            cost = round(claims * random.uniform(15, 400), 2)
            beneficiaries = int(claims * random.uniform(0.5, 0.85))
            unique_drugs = random.randint(3, 25)
            generic_rate = round(random.uniform(45, 92), 2)

            row = [npi_counter, year, random.choice(LAST_NAMES), random.choice(FIRST_NAMES),
                   state, specialty, CITIES.get(state, "Unknown"), claims, cost,
                   beneficiaries, unique_drugs, generic_rate]
            state_prescribers[state].append(row)

            key = (state, year)
            if key not in state_agg:
                state_agg[key] = {"claims": 0, "cost": 0.0, "benes": 0, "prescribers": 0,
                                   "drugs": set(), "pain_claims": 0}
            agg = state_agg[key]
            agg["claims"] += claims
            agg["cost"] += cost
            agg["benes"] += beneficiaries
            agg["prescribers"] += 1
            if specialty in ("Pain Management", "Anesthesiology"):
                agg["pain_claims"] += claims

        # Rank prescribers within (state, year)
        for state, rows in state_prescribers.items():
            rows.sort(key=lambda r: -r[8])  # sort by cost desc
            for rank, row in enumerate(rows, start=1):
                prescriber_rows.append(tuple(row) + (rank,))

    conn.executemany(
        "INSERT INTO prescriber_summary VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        prescriber_rows
    )

    # Build state_kpi from the aggregates collected above
    state_rows = []
    for year in YEARS:
        year_states = [(s, year) for s in STATES if (s, year) in state_agg]
        year_states.sort(key=lambda k: -state_agg[k]["cost"])
        for rank, key in enumerate(year_states, start=1):
            agg = state_agg[key]
            state, yr = key
            cost_per_bene = round(agg["cost"] / agg["benes"], 2) if agg["benes"] else 0
            avg_cost_per_claim = round(agg["cost"] / agg["claims"], 2) if agg["claims"] else 0
            unique_drugs = random.randint(80, 140)
            state_rows.append((
                state, yr, agg["claims"], round(agg["cost"], 2), agg["benes"],
                agg["prescribers"], unique_drugs, avg_cost_per_claim, cost_per_bene,
                rank, agg["pain_claims"],
            ))

    conn.executemany(
        "INSERT INTO state_kpi VALUES (?,?,?,?,?,?,?,?,?,?,?)", state_rows
    )


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    seed_drug_summary(conn)
    seed_prescriber_and_state(conn)
    conn.commit()

    # Print a summary so `python seed_database.py` gives immediate feedback
    for table in ("drug_summary", "prescriber_summary", "state_kpi"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:22s} -> {count:,} rows")

    conn.close()
    print(f"\n✅ Demo database created: {DB_PATH}")
    print("   Login uses the existing hardcoded demo accounts (api/auth/user_store.py) —")
    print("   admin/Admin@123, analyst/Analyst@123, viewer/Viewer@123 — no separate seeding needed.")


if __name__ == "__main__":
    main()
