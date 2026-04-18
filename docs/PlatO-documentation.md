# PlatO — Technical Documentation

**Version:** 0.1.0
**Licence:** EUPL-1.2
**Repository:** github.com/sgort/plato
**Live:** plato.open-regels.nl
**Stack:** FastAPI · React · PostgreSQL · Azure

---

## Table of Contents

1. [Project overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Backend](#3-backend)
4. [Data sources](#4-data-sources)
5. [Frontend](#5-frontend)
6. [Infrastructure](#6-infrastructure)
7. [Development](#7-development)
8. [Known limitations](#8-known-limitations)
9. [Roadmap suggestions](#9-roadmap-suggestions)

---

## 1. Project overview

PlatO is an open-source parliamentary monitoring dashboard targeting Dutch policy officers and public affairs professionals. It aggregates real-time data from three official Dutch government open-data sources and presents it as a unified, searchable, filterable feed — comparable in scope to commercial tools like Polpo.com, but built entirely on freely available government APIs with no proprietary data and no subscription cost.

The project is part of the broader IOU Architecture ecosystem at open-regels.nl.

### Design principles

- **No vendor lock-in.** Every data source is a public government API. No API keys. No scraping.
- **Fails gracefully.** Redis cache is optional and fails silently. Database errors don't crash the API. Upstream timeouts return 502 rather than hanging.
- **No tracking.** Sessions are anonymous UUID cookies. No user accounts. No analytics.
- **Iterative.** The beta banner is intentional — the tool is deployed early and improved in production.

---

## 2. Architecture

```
Browser
  │
  ├── Azure Static Web App (plato.open-regels.nl)
  │     React + Vite + TypeScript + Tailwind CSS
  │
  └── Azure App Service (plato-api.azurewebsites.net)
        FastAPI / Python 3.12 / uvicorn
          │
          ├── Azure PostgreSQL Flexible Server
          │     Saved searches (session-scoped)
          │
          ├── Redis (optional, in-memory fallback)
          │     Response cache: 15 min TK/OB, 1 hr CBS/legislation
          │
          └── Upstream APIs (no auth required)
                Tweede Kamer OData v4
                Officiële Bekendmakingen SRU
                CBS OData v4
                CPRMV (legislation proxy)
```

### Request flow

1. Browser fetches the React SPA from Azure Static Web Apps (CDN).
2. The SPA calls `/api/*` — in production, `VITE_API_BASE` points directly to the App Service.
3. The App Service checks Redis for a cached response. On miss, calls the upstream API.
4. Results are cached, normalised, and returned as JSON.
5. Saved searches are read/written to PostgreSQL via an anonymous session cookie.

---

## 3. Backend

### Entry point — `api/main.py`

- FastAPI application with async lifespan (database init on startup, Redis close on shutdown).
- CORS configured for `localhost:5173` (dev) and `plato.open-regels.nl` (prod).
- `no_cache_api` middleware sets `Cache-Control: no-store` on all `/api/*` responses, preventing browser caching of upstream errors.
- Health endpoint: `GET /api/health → {"status": "ok"}`.

### Configuration — `api/config.py`

Managed with `pydantic-settings`. All settings have sensible local defaults and are overridden via environment variables in production.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./dashboard.db` | SQLite locally, PostgreSQL in prod |
| `REDIS_URL` | `redis://localhost:6379` | Optional cache |
| `TK_API_BASE` | `https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0` | TK OData root |
| `CACHE_TTL_TK` | `900` | TK/OB cache TTL (seconds) |
| `CACHE_TTL_STATIC` | `3600` | CBS/legislation cache TTL (seconds) |

### Database — `api/db/`

- **Engine:** SQLAlchemy async with `aiosqlite` (local) or `asyncpg` + SSL (PostgreSQL in prod).
- **SSL:** Auto-detected from `DATABASE_URL` prefix — `ssl.create_default_context()` applied for PostgreSQL connections.
- **Init:** `init_db()` runs `create_all` at startup. Failures are logged but do not crash the API — the app degrades gracefully if the database is unavailable.

### Data model — `SavedSearch`

```
saved_searches
  id           TEXT (UUID, primary key)
  session_id   TEXT (64 chars, indexed)
  label        TEXT
  query        JSON  { q, types, source }
  created_at   DATETIME (server default)
```

The `GUID` custom type handles SQLite (stores as TEXT) and PostgreSQL (native UUID) transparently.

### Cache — `api/services/cache.py`

Redis-backed with in-memory fallback. Every `cache_get` and `cache_set` is wrapped in a bare `except Exception` — if Redis is not available, the API simply fetches live on every request. This design means Redis is purely a performance optimisation, not a dependency.

### API routers

| Router | Prefix | Purpose |
|---|---|---|
| `tk.py` | `/api/tk` | TK feed + document types |
| `ob.py` | `/api/ob` | OB feed + publication types |
| `cbs.py` | `/api/cbs` | CBS dataset list + observations |
| `legislation.py` | `/api/legislation` | CPRMV rule lookup + methods |
| `searches.py` | `/api/searches` | Saved search CRUD |

All routers validate input parameters and return `400` for unknown filter values, `502` for upstream failures.

---

## 4. Data sources

### 4.1 Tweede Kamer — `api/services/tk_client.py`

**Endpoint:** `https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/Document`

The TK OData v4 API is queried for parliamentary documents. Key implementation details:

- **URL construction:** `httpx` percent-encodes `$` to `%24` when using a params dict, breaking OData query strings. The client builds the URL manually using `urllib.parse.quote()` with `safe="() =','"`.
- **Field names:** The entity is `Document`, not `Kamerstuk`. Title field is `Onderwerp`. Sort field is `GewijzigdOp`.
- **Website URLs:** The internal `Id` field (UUID) does not work as a website URL parameter. The `DocumentNummer` field (e.g. `2026D16594`) must be used: `tweedekamer.nl/kamerstukken/detail?id={DocumentNummer}&did={DocumentNummer}`.
- **Negative volgnummers:** `Volgnummer = -1` means no value. These are filtered out client-side.
- **Filter:** Always includes `Verwijderd eq false` to exclude deleted documents.

**Available document types:** Motie, Amendement, Brief, Kamervraag, Verslag, Rapport, Vergaderverslag, Antwoord, Besluitenlijst.

**Pagination:** Server-side via `$skip` / `$top`. Total count via `$count=true` → `@odata.count`.

### 4.2 Officiële Bekendmakingen — `api/services/ob_client.py`

**Endpoint:** `https://repository.overheid.nl/sru`

The OB source uses SRU (Search/Retrieve via URL), a library protocol with CQL query syntax. Key implementation details:

- **CQL operator:** Double equals `==` required for exact match (not single `=`). Confirmed from the server's echoed query in responses.
- **Namespace:** The SRU response root element uses a default namespace (no prefix): `<searchRetrieveResponse xmlns="http://docs.oasis-open.org/ns/search-ws/sruResponse">`. Python's `ElementTree` requires Clark notation `{uri}localname` for all element lookups.
- **Record structure:** `sru:recordData > gzd:gzd > gzd:originalData > overheidwetgeving:meta` with nested `owmskern`, `owmsmantel`, and `tpmeta` elements. The canonical URL is in `gzd:enrichedData > gzd:preferredUrl`.
- **`sortKeys` not supported:** The server returns a diagnostic error. Client-side sort by `dcterms:date` descending is used instead.
- **Date scoping:** `w.jaargang == "2026"` scopes results to the current year. `dcterms.date` range filtering causes silent diagnostic errors on this endpoint.
- **Publication type filter:** `w.publicatienaam == "{type}"` using double equals.
- **Fetch strategy:** On page 1, fetches 3× the requested `top` to allow client-side sort to produce a better top-N.

**Available publication types:** Staatsblad, Staatscourant, Tractatenblad, Kamerstuk, Gemeenteblad, Provinciaal blad, Blad gemeenschappelijke regeling, Waterschapsblad.

**Text search:** `cql.textAndIndexes any "{query}"` — the catch-all full-text index on this endpoint.

### 4.3 CBS Statistics Netherlands — `api/services/cbs_client.py`

**Endpoint:** `https://datasets.cbs.nl/odata/v1/CBS`

The old endpoint (`opendata.cbs.nl/OData4`) is decommissioned and returns 301. Key implementation details:

- **URL construction:** Same `$` encoding issue as TK — URL built as a string, not via httpx params dict.
- **`$orderby` fallback:** Attempts `$orderby=Perioden desc` first; on 400 response, retries without it.
- **Multi-dimension datasets:** Datasets with extra dimensions (e.g. TypeWoning for Woningvoorraad, Bestedingscategorie for CPI) need a `default_measure` to pin a single time series. Without this, period deduplication returns one row per period across all dimension values rather than a clean series.
- **Period detection:** Auto-detects the period column by checking field names and CBS period code patterns (`JJ` = annual, `KW` = quarterly, `MM` = monthly).

**Configured datasets:**

| Code | Label | Notes |
|---|---|---|
| `83474NED` | Bevolking — kerncijfers | Working |
| `82816NED` | Woningvoorraad | `default_measure: T001044` — needs validation |
| `85323NED` | Werkloosheid — kerncijfers | `default_measure: T001137` — needs validation |
| `83694NED` | Bbp — kwartaalrekeningen | Working |
| `84637NED` | Consumentenprijzen — CPI | `default_measure: M000000` — needs validation |

Measure codes can be validated at: `https://datasets.cbs.nl/odata/v1/CBS/{code}/MeasureCodes`

### 4.4 CPRMV Legislation — `api/services/cprmv_client.py`

**Endpoint:** `https://cprmv.open-regels.nl`

Proxy client for the CPRMV API, which provides structured rule text for Dutch legislation. Supports BWB (national law), CVDR (municipal/provincial regulations), and EU CELLAR. Returns `cprmv-json` — a recursive tree of rule nodes keyed by predicate URIs. Multiple output formats supported: `cprmv-json`, `turtle`, `json-ld`, `n3`, `xml`.

---

## 5. Frontend

### Tech stack

React 18 · TypeScript · Vite · Tailwind CSS · date-fns

### State management

No external state library. State is composed from:
- `useState` for local component state
- Custom hooks (`useFeed`, `useSavedSearches`, `useCbs`, `useLegislation`) for data fetching
- `SearchState` (`{ q, types, source }`) lifted to `App` as the single source of truth for the active search

### Component inventory

| Component | Purpose |
|---|---|
| `App.tsx` | Root layout: sidebar + header + feed. Owns search state and theme. |
| `SearchBar` | Debounced text input. Keyboard shortcut `/` to focus. |
| `SourceToggle` | Switches between Tweede Kamer and Officiële Bekendmakingen |
| `FilterChips` | Document/publication type multi-select toggles |
| `FeedList` | Paginated item list with skeleton loading and "Meer laden" |
| `FeedCard` | Individual document card with colour-coded type dot, relative date, and external link |
| `CbsWidget` | Collapsible sparkline chart with dataset dropdown. Pure SVG, no chart library. |
| `LegislationLookup` | BWB/CVDR lookup with recursive `RuleNode` tree for article navigation |
| `SavedSearches` | Session-scoped saved search list with save/apply/delete |
| `ThemeToggle` | Dark/light theme toggle. Persisted in `localStorage`, falls back to system preference. |

### `useFeed` hook

- 350ms debounce on search state changes to avoid hammering the API while typing.
- Resets item list and pagination when the search key changes (source, query, or types).
- Supports `loadMore` for infinite scroll pagination.
- All upstream errors are caught and surfaced as a `string | null` error state.

### API client — `frontend/src/api/client.ts`

- `VITE_API_BASE` environment variable controls the API base URL. Empty in dev (proxied by Vite), set to `https://plato-api.azurewebsites.net` in production build.
- `cache: "no-store"` on all fetch calls prevents browser from caching failed API responses.
- `credentials: "include"` ensures the session cookie is sent cross-origin in production.

### Theme system

The Tailwind config uses a custom `ink` colour palette for the dark UI (`ink-700` through `ink-950`). Light mode is toggled via the `light` class on `<html>` and stored in `localStorage`.

### CBS sparkline chart

Hand-rolled SVG — no chart library dependency. Features:
- Y-axis grid lines with value labels
- Gradient area fill
- Latest value dot
- Period labels on X-axis (annual, quarterly, monthly auto-detected)
- Trend indicator (▲ / ▼) comparing last two periods

---

## 6. Infrastructure

### Azure resources (resource group: `rg-plato-prod`)

| Resource | Name | Tier | Purpose |
|---|---|---|---|
| App Service Plan | plato-api-plan | B1 Linux | Hosts the FastAPI backend |
| App Service | plato-api | Python 3.12 | FastAPI + uvicorn |
| PostgreSQL Flexible Server | plato-postgres-prod | Standard_B1ms | Saved searches |
| Static Web App | plato-frontend | Free | React SPA + CDN |

**App Service startup command:** `uvicorn main:app --host 0.0.0.0 --port 8000`

**App Service environment variables:**

| Variable | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://platoadmin:***@plato-postgres-prod.postgres.database.azure.com:5432/dashboard?sslmode=require` |
| `TK_API_BASE` | `https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0` |
| `CACHE_TTL_TK` | `900` |
| `CACHE_TTL_STATIC` | `3600` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `false` |

### CI/CD

Two GitHub Actions workflows:

**`build-api.yml`** — triggers on push to `main` affecting `api/**`. Installs dependencies into a `./package` folder, copies app files via `rsync`, zips, and uploads as a GitHub Actions artifact for manual deployment via `az webapp deploy`.

**`deploy-frontend.yml`** — triggers on push to `main` affecting `frontend/**`. Runs `npm ci` + `npm run build` with `VITE_API_BASE` injected, then deploys to Azure Static Web Apps.

### Manual API deployment (local zip)

```bash
cd api
pip install -r requirements.txt --target ./package
rsync -av --exclude 'package' --exclude '__pycache__' --exclude '*.pyc' --exclude '*.db' ./ package/
cd package && zip -r ../../app.zip . && cd ../..
rm -rf api/package
az webapp deploy --name plato-api --resource-group rg-plato-prod --src-path app.zip --type zip
```

### Custom domain

`plato.open-regels.nl` → Azure Static Web Apps hostname binding with auto-provisioned TLS.

---

## 7. Development

### Prerequisites

- Python 3.10+
- Node.js 20+
- Redis (optional)

### Local setup

```bash
# Backend
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# → http://localhost:8000/docs

# Frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

SQLite is created automatically at `api/dashboard.db` on first run. No database server needed locally.

### Code quality

Pre-commit hooks run on every commit and push:

| Hook | Purpose |
|---|---|
| `ruff` | Linting + auto-fix |
| `ruff-format` | Code formatting |
| `mypy` | Type checking (`--ignore-missing-imports`) |
| `trailing-whitespace` | Whitespace cleanup |
| `end-of-file-fixer` | Ensure newline at EOF |
| `check-yaml` | YAML syntax validation |
| `check-merge-conflict` | Detect unresolved conflict markers |

`node_modules/` is excluded from all hooks.

```bash
pre-commit install                           # wire into git commit
pre-commit install --hook-type pre-push     # also run on push
pre-commit run --all-files                  # run manually
```

---

## 8. Known limitations

### OB date scoping

The `w.jaargang == "2026"` filter must be updated manually each January. The `dcterms.date` range filter returns diagnostic errors on the repository.overheid.nl SRU endpoint and cannot be used.

### OB sorting

Server-side sorting via `sortKeys` is not supported by repository.overheid.nl. Client-side sorting on `dcterms:date` descending is used, but only over the fetched batch (3× page size on page 1). Deep pagination may show older documents.

### OB pagination

Because of the client-side sort + trim approach, the total result count shown (e.g. "190,976 resultaten") is from the server but the actual items displayed are a sorted subset of the first batch. Subsequent pages are not re-sorted.

### CBS datasets

`82816NED` (Woningvoorraad), `85323NED` (Werkloosheid), and `84637NED` (CPI) use provisional `default_measure` codes that have not been validated against the live `MeasureCodes` endpoint. These datasets may show no data or wrong data.

### No mobile sidebar

The sidebar is hidden on screens narrower than `lg` (1024px). The mobile header shows a source label and theme toggle, but the CBS widget, legislation lookup, and saved searches are not accessible on mobile.

### Single-region deployment

Deployed to West Europe only. No geo-replication or failover.

### Anonymous sessions only

Saved searches are tied to a cookie-based anonymous session. Clearing cookies or switching browsers loses all saved searches. No user accounts.

---

## 9. Roadmap suggestions

The following are improvements beyond the CBS measure code fixes, grouped by priority.

### High priority

**OB: dynamic year scoping**
Replace the hardcoded `w.jaargang == "2026"` with a computed current year. This prevents the feed from silently going empty every January. A one-line change in `_build_cql`.

**Mobile layout**
The sidebar is invisible below 1024px. A hamburger menu or bottom sheet for mobile would make the tool accessible on phones and tablets — important for professionals checking in on the go.

**Error boundaries**
Currently, an upstream failure shows an inline error message. Adding a React error boundary would prevent a single widget failure (e.g. CBS) from breaking the entire layout.

**OB: year auto-update**
Related to above — add a nightly or on-startup check that bumps `w.jaargang` dynamically, or derive it from `datetime.today().year` at query time.

### Medium priority

**TK: Vergaderjaar filter**
The TK API supports filtering by `Vergaderjaar`. Adding a year selector (e.g. "2024-2025", "2025-2026") would let users scope results to a specific parliamentary session.

**TK: Dossier grouping**
Parliamentary documents are grouped by dossier number (e.g. `36657`). Fetching related documents per dossier and grouping them in the feed would significantly improve context — this is a key differentiator of commercial tools.

**OB: server-side pagination fix**
Investigate whether `startRecord` with a larger `maximumRecords` request (e.g. 100) allows proper pagination. The current 3× fetch + trim approach breaks at page 2+.

**Saved searches: source awareness**
Saved searches currently store `{ q, types, source }` but the UI applies them without confirming the source matches. Restoring a TK search while viewing OB silently switches sources — this should be made explicit.

**CBS: measure code validation**
Validate `T001044` (Woningvoorraad), `T001137` (Werkloosheid), and `M000000` (CPI) against the `/MeasureCodes` endpoint and update `DATASETS` accordingly.

**CBS: configurable period window**
Currently hardcoded at 16 periods. A period selector (e.g. 12 months vs 5 years) in the CbsWidget would make the chart more useful for different analysis needs.

### Lower priority / longer term

**Full-text search across sources**
A unified search that queries TK, OB, and CBS simultaneously and merges results by relevance would be a significant UX improvement — and the core value proposition of commercial alternatives.

**Alerting / subscriptions**
Allow users to subscribe to a saved search and receive email notifications when new matching documents appear. Requires a user account system (e.g. magic link) and a scheduled polling job.

**Tweede Kamer: Activiteiten feed**
The TK API also exposes `Activiteit` (committee meetings, plenary sessions) and `Stemming` (voting records). Adding these as additional source toggles would round out the parliamentary monitoring coverage.

**Legislation: CVDR search**
Currently legislation lookup requires knowing a BWB or CVDR ID upfront. Adding a search interface over the CVDR catalogue would allow users to find relevant local regulations by topic or issuing authority.

**API rate limiting**
No rate limiting is currently applied. Under load, the single B1 App Service instance could exhaust upstream API rate limits. Adding per-IP rate limiting at the FastAPI layer (e.g. `slowapi`) would protect both the service and the upstream APIs.

**Docker Compose for local development**
A `docker-compose.yml` for local development with PostgreSQL and Redis would eliminate environment inconsistencies between SQLite-local and PostgreSQL-production, particularly for saved search behaviour.

**Azure Application Insights**
Connecting Application Insights to the App Service would provide error tracking, performance monitoring, and usage telemetry without adding external analytics.

---

*Generated: April 2026 | PlatO v0.1.0*
