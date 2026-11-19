# Deploy Lumen to Vercel

The repository is configured for **one Vercel project**, with the repository root as its Root Directory:

| Component | Deployment |
| --- | --- |
| UI | `frontend/` — Next.js, Node 22 |
| API | `backend/index.py` — Python 3.12 FastAPI, mounted at `/api` |
| Order matching | `backend/Dockerfile.worker` — one continuous Vercel Daemon |
| Data | Existing Supabase PostgreSQL project |

The root `vercel.json` defines the services, routing, worker resources, and health probe. There is no localhost API dependency in the hosted frontend. Browser requests and session cookies stay on the same HTTPS origin.

## 1. Set up the database once

Use Python 3.12 and install the backend dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Put the database URL in the ignored `backend/.env` file. For setup, use the exact **Session pooler** connection URI from Supabase → Connect (port `5432`), or a direct connection if your network supports it. The session pooler supports IPv4. Set `MIGRATION_DATABASE_URL` if setup should use a different connection from the API.

```bash
python -m app.db.bootstrap
python scripts/check_deployment.py
```

Bootstrap creates missing application tables and applies privacy rules; it preserves existing accounts, prices, positions, and trades. The database role must own the tables or have permission to create tables, enable RLS, and revoke browser-role grants. The trusted SQL backend role must retain table access. Use a separate migration workflow for future changes to existing columns: `create_all` does not perform those migrations.

Vercel request instances do **not** run schema setup. Run bootstrap before deploying a release that adds tables.

## 2. Import the repository in Vercel

1. Import the Git repository into a Vercel project.
2. Keep **Root Directory at the repository root (`.`)**. Do not select `frontend/` or `backend/`.
3. Let `vercel.json` define each service's framework and build command. Do not add a conflicting project-wide build command.
4. Use a Vercel project/CLI that supports **Services and Daemons**. Daemons are in public beta. For CLI deployment, use Vercel CLI 65.6.0 or newer.
5. If using CLI, run it from the repository root. Never run `vercel frontend/` for this configuration.

## 3. Add the project environment variables

Use the root `.env.example` as a checklist, not as a file containing real credentials to commit.

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Exact Supabase **Transaction pooler** URI, port `6543`, with `?sslmode=require`. Use `postgresql://` or `postgresql+psycopg2://`. URL-encode reserved characters in the password. |
| `FRONTEND_ORIGINS` | Exact HTTPS production origin, such as `https://lumen.example.com`. Comma-separate any additional custom domains. No wildcard or trailing path. |
| `PAPER_WORKER_ENABLED` | `true` |
| `PAPER_WORKER_INTERVAL_SECONDS` | `30` |
| `PAPER_WORKER_SYMBOL_LIMIT` | `30` |
| `DB_POOL_SIZE` | `2` |
| `DB_MAX_OVERFLOW` | `0` |

Vercel supplies `VERCEL`, `VERCEL_URL`, and `VERCEL_PROJECT_PRODUCTION_URL`. The API accepts the exact generated deployment origins in addition to configured custom origins. It always uses Secure, HttpOnly, SameSite=Lax session cookies on Vercel. Do not put database credentials in `NEXT_PUBLIC_*` variables. `BACKEND_URL` and the legacy `NEXT_PUBLIC_API_BASE_URL` are not needed for the hosted services setup.

Use **separate Preview and Production database URLs** if enabling Preview deployments. Initialize each database separately. Vercel Daemons currently run only in Production, so previews support interactive paper trades but do not run the continuous matching daemon. A production daemon must never be pointed at a preview database or vice versa.

## 4. Check the worker plan and region

The manifest starts **one 1 GiB daemon in `iad1`**, with a 60-second shutdown grace period. Change the region to one near your Supabase database if needed. The internal `/health` probe runs on port 8080; it is not a public API endpoint. The daemon stops between bounded work items after SIGTERM and can safely retry persisted orders after a restart.

Daemons consume provisioned-memory quota while running. At the currently documented Hobby limit of **420 GB-hours/month**, a continuously running 1 GiB instance would need approximately **720 GB-hours for 30 days**, before other project usage. Choose a plan/quota that supports uninterrupted matching; availability in Hobby does not mean a full month of free continuous operation. Check current quotas before publishing.

## 5. Deploy and verify

Deploy Production from Vercel. Then:

Run `python scripts/check_public_routes.py https://YOUR_DOMAIN` from `backend/` to verify the homepage redirect, dashboard, standalone login/signup pages, company logo, API health, and signed-out session response against the actual deployment. A successful build alone does not verify public routing.

1. Open `https://YOUR_DOMAIN/api/health`. Expect `status: "ok"`, database connected, and paper trading in `external` mode. A `schema_setup_required` response means bootstrap needs to run against that environment's database.
2. Inspect the `paper-trading` daemon in Vercel. Its probe must be healthy and its logs should report completed paper cycles. API `external` mode indicates configuration, not a live report from the separate daemon.
3. Create a practice account. Verify signup, refresh, logout, and login on the public HTTPS domain.
4. Place a small paper buy and sell, then test an unfilled limit order and cancellation.
5. Save an asset, sign in from another browser, and verify the watchlist persists.

Optional, read-only hosted-mode preflight from `backend/` after setting the same server environment:

```bash
VERCEL=1 VERCEL_URL=YOUR_PROJECT.vercel.app python scripts/check_deployment.py
```

The existing `scripts/verify_paper_trading.py` performs a deeper database/API round trip inside a transaction that is rolled back afterward. It does not publish a website or leave a verification account behind.

## Local development

The existing two-process workflow still works:

```bash
# backend/
.venv/bin/python -m uvicorn app.main:app --reload
# frontend/, in another terminal
npm run dev
```

Local FastAPI may run the embedded worker. Hosted FastAPI never does. To test the exact cloud entrypoints locally with an initialized test database:

```bash
# backend/, API prefix and HTTPS cookie behavior use hosted settings
VERCEL=1 .venv/bin/python -m uvicorn index:app --port 8000
# backend/, separate worker process
.venv/bin/python -m uvicorn worker:app --port 8080
```

Or build the worker image from `backend/`:

```bash
docker build -f Dockerfile.worker -t lumen-paper-worker .
docker run --rm --env-file .env -p 8080:8080 lumen-paper-worker
```

Vercel's `vercel dev` does not run Daemons. Run the worker separately when exercising the Services project locally. For tests and the rollback verification script, install `backend/requirements-dev.txt`.

## References and validation scope

- [Vercel Services](https://vercel.com/docs/services)
- [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi)
- [Vercel Daemons](https://vercel.com/docs/daemons)
- [Daemon quotas](https://vercel.com/docs/daemons/limits)
- [Supabase connection modes](https://supabase.com/docs/guides/database/connecting-to-postgres)

Local validation covers the Vercel JSON schema, Node 22 frontend build, API routing under `/api`, secure cookies, origin/CSRF checks, shared hosted login throttling, bounded connection configuration, standalone worker health/shutdown, and trading regressions. The Vercel cloud build and Linux container image build still need to run in the connected Vercel account; Docker and Vercel CLI are not installed in this workspace.
