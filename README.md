# PlatO

Open-source political monitoring dashboard for Dutch policy officers and public affairs professionals. Pulls live data from three official open data sources — no API keys required.

## Data sources

| Source | What | Endpoint |
|--------|------|----------|
| **Tweede Kamer** | Parliamentary documents — moties, brieven, Kamervragen, amendementen | `gegevensmagazijn.tweedekamer.nl/OData/v4/2.0` |
| **Officiële Bekendmakingen** | Staatsblad, Staatscourant, Tractatenblad | `zoekservice.overheid.nl/sru/Search` |
| **CBS** | Population, housing, unemployment, GDP, CPI time series | `datasets.cbs.nl/odata/v1/CBS` |

Legislation lookup is proxied via [CPRMV API](https://cprmv.open-regels.nl) (BWB national law, CVDR municipal regulations).

---

## Project structure

```
PlatO/
├── api/                   # FastAPI backend (Python 3.12)
│   ├── db/                # SQLAlchemy models + async engine
│   ├── routers/           # API route handlers
│   └── services/          # Data source clients + Redis cache
├── frontend/              # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── api/           # Fetch wrappers
│       ├── components/    # UI components
│       └── hooks/         # Data hooks
├── docker-compose.yml     # Production stack
├── Caddyfile              # Reverse proxy (HTTPS)
└── .pre-commit-config.yaml
```

---

## Local development (no Docker)

### Requirements

- Python 3.10+
- Node.js 20+
- Redis (optional — app works without it, just no caching)

### Backend

```bash
cd api
pip install -r requirements.txt (on Windows: pip install -r requirements-dev.txt)
cp ../.env.example ../.env
python -m uvicorn main:app --reload --port 8000
```

The API starts at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

SQLite is used by default — a `dashboard.db` file is created automatically in `api/` on first run. No database server needed.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. The Vite dev server proxies `/api/*` to `localhost:8000` automatically.

---

## Environment variables

Copy `.env.example` to `.env`. All defaults work out of the box for local dev.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./dashboard.db` | SQLite for local dev. Use `postgresql+asyncpg://...` for production. |
| `REDIS_URL` | `redis://localhost:6379` | Optional. Caches API responses (15 min for TK/OB, 1 hr for CBS/legislation). |
| `TK_API_BASE` | `https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0` | Tweede Kamer OData endpoint. |
| `CACHE_TTL_TK` | `900` | TK/OB cache TTL in seconds. |
| `CACHE_TTL_STATIC` | `3600` | CBS/legislation cache TTL in seconds. |

---

## Docker (production)

```bash
cp .env.example .env
# Edit .env: set DATABASE_URL to postgresql+asyncpg://dashboard:dashboard@db:5432/dashboard
docker compose up --build
```

Edit `Caddyfile` and replace `yourdomain.nl` with your actual domain before deploying. Caddy handles HTTPS automatically.

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/tk/feed` | Parliamentary documents. Query: `q`, `types[]`, `skip`, `top` |
| `GET` | `/api/tk/types` | Available TK document types |
| `GET` | `/api/ob/feed` | Officiële Bekendmakingen. Query: `q`, `types[]`, `skip`, `top` |
| `GET` | `/api/ob/types` | Available OB publication types |
| `GET` | `/api/cbs/datasets` | List of available CBS datasets |
| `GET` | `/api/cbs/dataset/{code}/observations` | Time-series observations. Query: `measure`, `periods` |
| `GET` | `/api/legislation/rule/{rule_id_path}` | Rule text from CPRMV API. Supports BWB and CVDR IDs. |
| `GET` | `/api/searches` | List saved searches (session-scoped) |
| `POST` | `/api/searches` | Save a search |
| `DELETE` | `/api/searches/{id}` | Delete a saved search |
| `GET` | `/api/health` | Health check |

---

## Development

### Code quality

```bash
# Install dev tools (from project root)
pip install pre-commit ruff mypy

# Install git hooks
pre-commit install
pre-commit install --hook-type pre-push

# Run manually
pre-commit run --all-files
```

Hooks run on every commit and push: `ruff` (lint + format), `mypy` (type check), trailing whitespace, YAML validation.

### Frontend type check

```bash
cd frontend
npm run typecheck
npm run lint
```

---

## Licence

[EUPL-1.2](https://eupl.eu/1.2/en/) — compatible with the broader [IOU Architecture](https://iou-architectuur.open-regels.nl) ecosystem this project is designed to complement.
