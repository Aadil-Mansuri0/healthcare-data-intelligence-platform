# Demo Mode — Run Without Any Cloud Credentials

Every previous "Quick Start" in this repo assumed real Snowflake + AWS + OpenAI
credentials. That's correct for production, but it means nobody could actually
click through this project without first provisioning cloud infrastructure —
which isn't "live demo ready" in any honest sense. This mode fixes that.

## What Demo Mode replaces

| Production dependency | Demo Mode replacement |
|---|---|
| Snowflake (GOLD_SCHEMA tables) | **SQLite** (`demo/healthcare_demo.db`), same schema, seeded with realistic synthetic data |
| OpenAI (NL2SQL, RAG, AI services) | **Deterministic mock responses** (`demo/mock_llm.py`) — pattern-matches common question shapes to real SQL against the SQLite demo DB, so the AI chat still *works end-to-end*, just without a live LLM call |
| ChromaDB + real embeddings | Skipped — demo mode's mock LLM doesn't need retrieval, since it pattern-matches directly |
| AWS S3 / Airflow / Kafka | Not needed for the demo — those are the *pipeline that produces* Gold data; demo mode starts from pre-seeded Gold data directly |

**Everything else runs for real**: FastAPI, JWT auth + RBAC, rate limiting,
the Next.js dashboard, the chat UI, PHI redaction, audit logging. The only
things swapped are the three external paid/cloud services, so anyone can
`git clone` and see a fully working product in under 5 minutes.

## Run it

```bash
cd demo
python seed_database.py          # creates demo/healthcare_demo.db + seed data
cd ..
docker-compose -f docker/docker-compose.demo.yml up
```

Then open `http://localhost:3000/login` — login as `admin` / `Admin@123`.

## What you'll see working

- **Dashboard** — real charts, populated from the seeded SQLite data (top drugs, generic vs brand, state costs)
- **AI Chat** — ask "Which state had the highest total drug cost?" and get a real answer with real generated SQL, run against the demo database — no OpenAI key needed
- **Auth** — real JWT login/logout/token-revocation, real RBAC (try logging in as `viewer` and note the AI chat link disappears)
- **Rate limiting** — try logging in wrong 6 times in a minute, see the 429

## What you will NOT see in Demo Mode

- Free-form AI questions outside the 7 pattern groups `demo/mock_llm.py` recognizes (it responds honestly: "I don't have a demo answer for that — this would call a real LLM in production")
- Airflow pipeline execution (there's no pipeline to run — data is pre-seeded)
- RAG retrieval quality (no real embeddings are computed) — the chat endpoint still works in demo mode, but returns the same pattern-matched answers as the base assistant, with a note that retrieval/memory aren't active
- **AI Services beyond chat** — `/api/ai/insights`, `/api/ai/reports/*`, `/api/ai/data-quality-check`, `/api/ai/recommendations`, and `/api/rag/agent` all require live OpenAI calls and are outside demo mode's scope. Each returns an explicit `503` with a clear explanation in demo mode — not a crash, not a fake response. They aren't wired into any frontend page yet regardless (API-only, testable via `/docs`), so this doesn't affect the demo's visible click-through surface.

This is intentional — Demo Mode's job is to prove the *application* works,
not to simulate the full data platform. See the main README's "Quick Start"
for the real cloud-connected setup.

## Verified safe to import without any environment variables set

Every module that constructs an OpenAI client does so with
`os.environ.get("OPENAI_API_KEY", "not-configured")` instead of a hard
`os.environ["OPENAI_API_KEY"]` index — the latter would crash Python's
`import` statement itself (before FastAPI even starts) the moment any route
module transitively imported it, regardless of whether that specific route
was ever called. This was an actual bug caught during demo-mode
implementation (8 files affected) and verified fixed via AST-based static
analysis across the full codebase (see `python3` snippet in project commit
history / build log — zero module-level hard `os.environ[...]` indexing
remains anywhere in the 64 Python files that make up the API + libraries).
