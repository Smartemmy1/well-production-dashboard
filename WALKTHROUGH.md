# Walkthrough: how this project works

Notes for explaining the project in an interview. Read this alongside the code.

## The problem

Production engineers check every well each morning: is it producing what it should, is water creeping up, did anything trip overnight? This app puts those answers on one screen and points at the wells that need a look first.

## Architecture in one picture

```
Browser (React + TypeScript)
   │  fetch /api/...
   ▼
nginx (serves the built React app, forwards /api)        ← Docker only; Vite does this in dev
   │
   ▼
FastAPI (routers → services → SQLAlchemy models)
   │
   ▼
PostgreSQL (Docker) or SQLite (local dev and tests)
```

## A request, end to end

Take the dashboard loading for "Grand Bank East, last 90 days":

1. `Dashboard.tsx` reads `field` and `days` from the URL and calls `api.dashboard(field, days)` through the `useApi` hook.
2. `GET /api/dashboard?field=Grand Bank East&days=90` reaches `routers/dashboard.py`.
3. FastAPI validates `days` (between 7 and 3650) and injects a database session (`get_db`) and settings (`get_settings`) via dependency injection.
4. `analytics.field_series()` runs one SQL `GROUP BY date` query that sums oil, gas and water across the field's wells.
5. The router averages the last 7 days for the headline rates, counts alerts, and returns a `DashboardSummary`. Pydantic serializes it to JSON.
6. React renders the figures, then Recharts draws the series.

## Key design decisions (and why)

**Routers, services, models are separate layers.** Routers handle HTTP only. All engineering logic sits in `services/analytics.py` as plain functions, so the alert rules are unit-tested without starting a server (`tests/test_analytics.py`).

**Rates are 7-day averages.** A single day is noisy: a well can be down for 6 hours for maintenance. Averaging gives a steadier number and matches how engineers usually talk about rates.

**Alerts compare against the well's own history.** "Down 50%" means compared with the 30 days before the last 7, not a fixed number, because a 300 bbl/d well and a 3,000 bbl/d well need different absolute limits. Thresholds are configuration, not code.

**One unit per chart.** Oil and water share bbl/d; gas (Mcf/d) gets its own chart instead of a second y-axis, which is easy to misread.

**Industry phase colors.** Oil green, water blue, gas red, the convention used in production plots, so engineers read the charts instantly.

**Duplicate days are prevented at the database level.** A unique constraint on `(well_id, date)` means two people entering the same day cannot create double-counted production. The API turns the database error into a clear 409 response.

**CSV import is idempotent.** Re-uploading the same file skips days already stored, and bad rows are reported by line number instead of failing the whole file.

**SQLite for tests, PostgreSQL in Docker.** SQLAlchemy abstracts the difference, so tests run in milliseconds with an in-memory database and the same code runs on PostgreSQL in production.

## Engineering formulas used

- **Water cut** = water / (oil + water)
- **Gas-oil ratio (GOR)** = gas (Mcf) × 1000 / oil (bbl), in scf/bbl
- **Uptime** = hours on / 24
- **Arps hyperbolic decline** (demo data): q(t) = qᵢ / (1 + b·Dᵢ·t)^(1/b)

## Questions you may be asked

- *How would you scale this to thousands of wells?* Compute alerts in one batched SQL query (window functions) instead of per well, cache the dashboard, and run alert evaluation as a scheduled job.
- *Why FastAPI?* Type hints drive validation and the interactive docs at `/docs`, and it is fast.
- *How do you prevent bad data?* Pydantic rejects negative volumes, hours over 24 and future dates; the database rejects duplicate days.
- *What would you add next?* Migrations with Alembic, authentication, decline-curve forecasting, notifications for new alerts.
