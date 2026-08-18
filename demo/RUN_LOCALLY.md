# Run This Locally — Exact Steps

Run these **on your own machine** (not in any sandbox), from the
`healthcare_advanced/` folder (the repo root, where this README's parent
directory's `README.md` lives).

## Step 1 — Preflight check

```bash
bash demo/preflight_check.sh
```

Fixes anything it flags before continuing. Common misses: Docker Desktop
not started, ports 3000/8000 already used by something else.

## Step 2 — Seed the demo database

```bash
python3 demo/seed_database.py
```

**Expected output:**
```
  drug_summary           -> 45 rows
  prescriber_summary     -> 1,800 rows
  state_kpi              -> 60 rows

✅ Demo database created: .../demo/healthcare_demo.db
   Login uses the existing hardcoded demo accounts (api/auth/user_store.py) —
   admin/Admin@123, analyst/Analyst@123, viewer/Viewer@123 — no separate seeding needed.
```

**If this fails:** almost certainly a Python version or missing-module issue
(this script only uses Python's standard library, so it should work with any
Python 3.9+ with zero pip installs — if you see an import error, paste it here).

## Step 3 — Generate the frontend lockfile (one-time, first run only)

```bash
cd frontend
npm install
cd ..
```

This creates `frontend/package-lock.json` — the one file I genuinely could
not generate for you (needs live npm registry access). Takes ~30 seconds.

## Step 4 — Build and start

```bash
docker-compose -f docker/docker-compose.demo.yml up --build
```

First run will take a few minutes (building 2 Docker images). Watch for:
- `healthcare_advanced-api-1  | INFO: Application startup complete.`
- `healthcare_advanced-frontend-1  | ▲ Next.js ... - Local: http://localhost:3000`

**If the build fails**, paste the full error — the most likely failure points,
ranked by probability, are:
1. A Python package in `api/requirements.txt` failing to install (version conflict on your machine's Docker platform — e.g. Apple Silicon sometimes needs platform-specific wheels)
2. `npm run build` failing inside the frontend image (would confirm/deny the Tailwind config fix actually works — this is the thing I could NOT test myself)
3. Port conflicts if step 1's check was skipped

## Step 5 — Open it

```
http://localhost:3000
```

Should redirect to `/login`. Log in as `admin` / `Admin@123`.

**Click-through checklist** (tell me which of these breaks, if any):
- [ ] Login succeeds, redirects to `/dashboard`
- [ ] Dashboard shows charts with real numbers (not blank/error state)
- [ ] Sidebar/nav lets you reach `/chat`
- [ ] Typing "Which state had the highest total drug cost in 2023?" in chat returns a real answer with SQL shown
- [ ] Logging out and back in works
- [ ] Waiting isn't required to test refresh — but if you leave it open 30+ min and click something, it should silently keep working (that's the token-refresh fix from earlier)

## Step 6 — Report back

Paste here, in order of what you hit:
1. The exact command you ran
2. The exact error output (full text, not paraphrased — exact tracebacks matter)
3. Your OS (Mac/Windows/Linux) and if Mac, Intel or Apple Silicon (M1/M2/M3) — this affects Docker platform compatibility

I'll diagnose and fix from that, same as every bug found so far in this project.

## Shutting down

```bash
docker-compose -f docker/docker-compose.demo.yml down
```

Add `-v` to also wipe the ChromaDB volume if you want a totally clean restart:
```bash
docker-compose -f docker/docker-compose.demo.yml down -v
```
