# Store Locator Service

A production-style Store Locator API service for a multi-location retail business.

The system supports public store search by address, ZIP code, or latitude/longitude, and secure internal store management with JWT authentication and role-based access control.

This repository is aligned with the course **Deliverables (Section 8)** expectations:

| Deliverable | Where it lives |
|---|---|
| **8.1 Code repository** | Clear layout under `app/`, `tests/`, `scripts/`, `migrations/`; `requirements.txt`; `.env.example` |
| **8.2 Documentation** | This README (setup, API, auth, distance, deployment); schema summary below; sample requests; interactive API at `/docs` |
| **8.3 Testing** | `pytest` suite; coverage instructions; last run: **56 passed**, **88%** line coverage on `app/` |
| **8.4 Deployment** | Docker / `docker-compose`; GCP (Cloud Run, Cloud SQL, Memorystore) — see [Deployment](#deployment) and `GCP_DEPLOYMENT_GUIDE.md` |

## Framework and CSV processing choices

- **Framework:** **FastAPI** on Uvicorn — automatic OpenAPI (`/docs` / `/redoc`), Pydantic validation, dependency injection for database sessions and RBAC.
- **CSV batch import:** Python standard library **`csv`** (with `io.StringIO`), **not pandas** — keeps the dependency set small, streams rows for validation, and fits the all-or-nothing transaction used for upserts.

## Architecture overview

```text
Clients (curl, Swagger, browser)
            |
            v
    +---------------+
    |  FastAPI app  |  JWT auth, RBAC, rate limits
    +---+-------+---+
        |       |
        |       +----------------------------+
        v                                      v
  PostgreSQL                             Redis (Memorystore)
  stores, users,                         geocode cache,
  roles, refresh tokens                  search cache, rate limit keys
        |
        +--> Optional: US Census Geocoder, Zippopotam.us (HTTP)
```

Public search geocodes addresses/ZIPs when needed, applies a **bounding-box** SQL pre-filter, then exact **geodesic** distance (see [Distance calculation](#distance-calculation-method)).

## Features

### Public Store Search

- `POST /api/stores/search`
- Search by:
  - Full address
  - ZIP code
  - Latitude and longitude
- Radius-based search with `radius_miles`
- Store service filtering with AND logic
- Store type filtering with OR logic
- Optional `open_now` filtering
- Results sorted by distance
- Bounding box pre-filter before exact distance calculation
- Geopy-based distance calculation
- Redis-backed geocoding cache
- Redis-backed search result cache
- IP-based rate limiting

### Geocoding

- ZIP code geocoding: Zippopotam.us
- Address geocoding: US Census Geocoder
- Redis cache TTL: 30 days
- Local database fallback for demo stability

### Admin Store Management

- `POST /api/admin/stores`
- `GET /api/admin/stores`
- `GET /api/admin/stores/{store_id}`
- `PATCH /api/admin/stores/{store_id}`
- `DELETE /api/admin/stores/{store_id}`

**Create (`POST`) — coordinates:** If `latitude` and `longitude` are **both omitted**, the service **auto-geocodes** the store from the full address (street, city, state, postal code, country), with a fallback to **ZIP-only** geocoding when needed. If you pass one of lat/lon, you must pass **both** (matches the course requirement: auto-geocode when coordinates are not provided).

Delete is implemented as a soft delete by setting:

```text
status = "inactive"
```

### Authentication and Authorization

JWT two-token pattern:

- Access token: 15 minutes
- Refresh token: 7 days
- Refresh tokens stored in database as hashes
- Logout revokes refresh token

Roles:

| Role | Permissions |
|---|---|
| Admin | Full access to stores, users, imports |
| Marketer | Store management and CSV import |
| Viewer | Read-only store access |

### CSV Import

- `POST /api/admin/stores/import`
- Accepts CSV upload
- Validates exact headers
- Validates each row
- Uses all-or-nothing transaction
- Supports upsert:
  - existing `store_id` -> update
  - new `store_id` -> create
- **Auto-geocode when coordinates are missing:** If a row has no `latitude` / `longitude` (or both empty), coordinates are resolved by geocoding the row’s address (then postal code if needed), same idea as project spec §2.3.
- Replaces store services during update
- Returns detailed import report

### Admin User Management (admin role only)

- `POST /api/admin/users` — create user
- `GET /api/admin/users` — list users (pagination)
- `PUT /api/admin/users/{user_id}` — update role or active status
- `DELETE /api/admin/users/{user_id}` — deactivate user (`is_active = false`)

### Testing

- Unit tests
- API tests
- Integration tests
- Mocked external geocoding calls using `unittest.mock.MagicMock` and `patch`
- Redis/rate-limit behavior tested with mocks
- Latest local run (see [Testing](#testing)):

```text
56 passed
app/ line coverage: 88%
```

---

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- PyJWT
- bcrypt
- geopy
- requests
- pytest
- Docker
- Google Cloud Run
- Google Cloud SQL for PostgreSQL
- Google Memorystore for Redis
- Google Artifact Registry

---

## Project Structure

```text
store-locator-service/
├── app/
│   ├── api/
│   │   ├── auth.py
│   │   ├── stores.py
│   │   ├── admin_stores.py
│   │   └── admin_users.py
│   ├── core/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── rate_limit.py
│   │   ├── redis_client.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── auth.py
│   │   ├── store.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── store.py
│   │   ├── admin_store.py
│   │   └── admin_user.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── cache.py
│   │   ├── csv_import.py
│   │   ├── distance.py
│   │   ├── geocoding.py
│   │   ├── hours.py
│   │   └── store_search.py
│   └── main.py
├── migrations/
│   └── 001_initial_schema.sql
├── scripts/
│   ├── __init__.py
│   ├── load_stores.py
│   ├── seed_users.py
│   └── deploy/
│       ├── load-gcp-vars.ps1
│       ├── gcp-config.ps1          (gitignored; copy from guide)
│       ├── rebuild-push-deploy.ps1
│       └── seed-cloudsql.ps1
├── tests/
├── data/
│   ├── stores_50.csv
│   ├── stores_1000.csv
│   └── stores_missing_coordinates.csv
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── GCP_DEPLOYMENT_GUIDE.md
└── README.md
```

---

## Environment Variables

Create `.env` locally:

```env
DATABASE_URL=postgresql://store_user:store_password@localhost:5432/store_locator

JWT_SECRET_KEY=replace-this-with-a-long-random-secret-key-at-least-32-bytes
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

REDIS_URL=redis://localhost:6379/0
GEOCODING_CACHE_TTL_SECONDS=2592000
SEARCH_CACHE_TTL_SECONDS=600

RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100

US_CENSUS_GEOCODER_URL=https://geocoding.geo.census.gov/geocoder/locations/onelineaddress
US_CENSUS_BENCHMARK=Public_AR_Current
ZIPPOPOTAMUS_URL=https://api.zippopotam.us/us
```

---

## Local Setup

### 1. Create virtual environment

```bash
python -m venv .venv
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start PostgreSQL and Redis

```bash
docker compose up -d postgres redis
```

Check containers:

```bash
docker compose ps
```

### 4. Create database schema

**Option A — SQL migration (recommended for production-style setup):**

```bash
psql "$DATABASE_URL" -f migrations/001_initial_schema.sql
```

On Windows PowerShell (URI may need quoting depending on your shell):

```powershell
psql $env:DATABASE_URL -f migrations/001_initial_schema.sql
```

**Option B — SQLAlchemy create-all (local development):**

```bash
python -c "from app.db.base import Base; from app.db.session import engine; import app.models; Base.metadata.create_all(bind=engine)"
```

### 5. Load store data

Run as a module (requires `scripts` as a package — `scripts/__init__.py` is included):

```bash
python -m scripts.load_stores data/stores_1000.csv
```

### 6. Seed users

```bash
python -m scripts.seed_users
```

### 7. Run the app locally

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

---

## Docker Local Run

Build image:

```bash
docker build -t store-locator-service:local .
```

Run full stack:

```bash
docker compose up --build -d
```

Open:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

---

## API Documentation

Interactive **OpenAPI** documentation is served by FastAPI:

| Resource | Local | Production (GCP Cloud Run) |
|---|---|---|
| Swagger UI | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | [https://store-locator-service-xlp6wxlioa-uc.a.run.app/docs](https://store-locator-service-xlp6wxlioa-uc.a.run.app/docs) |
| ReDoc | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) | [https://store-locator-service-xlp6wxlioa-uc.a.run.app/redoc](https://store-locator-service-xlp6wxlioa-uc.a.run.app/redoc) |
| OpenAPI JSON | [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json) | [https://store-locator-service-xlp6wxlioa-uc.a.run.app/openapi.json](https://store-locator-service-xlp6wxlioa-uc.a.run.app/openapi.json) |

**Production API root:** [https://store-locator-service-xlp6wxlioa-uc.a.run.app/](https://store-locator-service-xlp6wxlioa-uc.a.run.app/) (`GET /` returns `docs` and `health` links).

Health check:

```text
GET /health
```

Expected response:

```json
{
  "status": "ok",
  "redis": "ok"
}
```

---

## API Examples

### Public Search by Coordinates

```bash
curl -X POST "http://127.0.0.1:8000/api/stores/search" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.7505,
    "longitude": -73.9934,
    "radius_miles": 10
  }'
```

### Public Search by ZIP Code

```bash
curl -X POST "http://127.0.0.1:8000/api/stores/search" \
  -H "Content-Type: application/json" \
  -d '{
    "postal_code": "10001",
    "radius_miles": 20,
    "services": ["pickup"],
    "store_types": ["regular", "express"]
  }'
```

### Public Search by Address

```bash
curl -X POST "http://127.0.0.1:8000/api/stores/search" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "4600 Silver Hill Rd, Washington, DC 20233",
    "radius_miles": 20
  }'
```

### Admin — list users (admin access token required)

```bash
curl -X GET "http://127.0.0.1:8000/api/admin/users?page=1&page_size=20" \
  -H "Authorization: Bearer <access_token>"
```

Example success shape:

```json
{
  "total": 3,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "user_id": "U001",
      "email": "admin@test.com",
      "role_id": "admin",
      "role_name": "admin",
      "is_active": true,
      "must_change_password": false
    }
  ]
}
```

---

## Authentication Flow

### Login

```bash
curl -X POST "http://127.0.0.1:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "AdminTest123!"
  }'
```

Response:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

Use the access token:

```text
Authorization: Bearer <access_token>
```

### Refresh Access Token

```bash
curl -X POST "http://127.0.0.1:8000/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token>"
  }'
```

### Logout

```bash
curl -X POST "http://127.0.0.1:8000/api/auth/logout" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token>"
  }'
```

Logout revokes the refresh token in the database.

---

## Test Credentials

```text
Admin:
  Email: admin@test.com
  Password: AdminTest123!

Marketer:
  Email: marketer@test.com
  Password: MarketerTest123!

Viewer:
  Email: viewer@test.com
  Password: ViewerTest123!
```

---

## Distance Calculation Method

The service uses the required Bounding Box + Haversine/geodesic method.

### Step 1: Calculate bounding box

```python
latitude_delta = radius_miles / 69.0
longitude_delta = radius_miles / (69.0 * cos(latitude_radians))

min_lat = search_lat - latitude_delta
max_lat = search_lat + latitude_delta
min_lon = search_lon - longitude_delta
max_lon = search_lon + longitude_delta
```

### Step 2: SQL pre-filter

```sql
WHERE latitude BETWEEN min_lat AND max_lat
  AND longitude BETWEEN min_lon AND max_lon
  AND status = 'active'
```

### Step 3: Exact distance calculation

```python
from geopy.distance import geodesic

distance = geodesic(
    (search_lat, search_lon),
    (store.latitude, store.longitude)
).miles
```

### Step 4: Radius filter and sort

```python
results = [store for store in stores if store.distance <= radius_miles]
results.sort(key=lambda store: store.distance)
```

This reduces the number of stores that need exact distance calculation.

---

## Database Schema Overview

The canonical PostgreSQL DDL for an empty database is in `migrations/001_initial_schema.sql` (roles, permissions, `role_permissions`, `stores`, `store_services`, `users`, `refresh_tokens`). After applying it, run `python -m scripts.seed_users` to insert roles, permissions, and demo users.

### stores

Stores core store profile, address, location, hours, and status.

Key fields:

- `store_id`
- `name`
- `store_type`
- `status`
- `latitude`
- `longitude`
- `address_street`
- `address_city`
- `address_state`
- `address_postal_code`
- `address_country`
- `phone`
- `hours_mon` ... `hours_sun`

Indexes:

- `latitude, longitude`
- `status`
- `store_type`
- `address_postal_code`

### store_services

Stores services for each store.

- `store_id`
- `service_name`

### users

Stores internal users.

- `user_id`
- `email`
- `password_hash`
- `role_id`
- `is_active`

### roles

- `admin`
- `marketer`
- `viewer`

### permissions

- `manage_stores`
- `read_stores`
- `import_stores`
- `manage_users`

### role_permissions

Maps roles to permissions.

### refresh_tokens

Stores hashed refresh tokens for revocation.

---

## Testing

Run all tests:

```bash
pytest -v
```

Run coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

Generate HTML coverage report (output in `htmlcov/index.html`):

```bash
pytest --cov=app --cov-report=html
```

Latest run in this repository:

```text
56 passed
TOTAL (app/): 88% line coverage
```

Test suite coverage includes:

- Distance calculation
- Bounding box calculation
- Hours parsing
- Password hashing and verification
- Public search by coordinates, ZIP, and address
- Radius, service, and store type filters
- Authentication login, refresh, logout
- RBAC authorization
- Admin store create/list/detail/update/delete
- PATCH field restrictions
- CSV import validation and upsert behavior
- Redis cache behavior
- IP-based rate limiting
- Mocked external geocoding calls
- Admin user CRUD-style endpoints (admin-only)

---

## Deployment

Final deployment platform:

```text
Google Cloud Platform (GCP)
```

Components:

| Component | Platform |
|---|---|
| API server | Cloud Run |
| Container image | Artifact Registry |
| Database | Cloud SQL for PostgreSQL |
| Cache / rate limit | Memorystore (Redis) |
| Redis private access | Serverless VPC Access connector |

Automation scripts (PowerShell) live under `scripts/deploy/` — copy/edit `gcp-config.ps1` from `GCP_DEPLOYMENT_GUIDE.md` (the committed `.gitignore` excludes local secrets files such as `gcp-config.ps1` and generated env exports).

**Deployed service (this project):**

| Endpoint | URL |
|---|---|
| API root | [https://store-locator-service-xlp6wxlioa-uc.a.run.app/](https://store-locator-service-xlp6wxlioa-uc.a.run.app/) |
| Swagger UI | [https://store-locator-service-xlp6wxlioa-uc.a.run.app/docs](https://store-locator-service-xlp6wxlioa-uc.a.run.app/docs) |
| Health | [https://store-locator-service-xlp6wxlioa-uc.a.run.app/health](https://store-locator-service-xlp6wxlioa-uc.a.run.app/health) |

**Demo logins** (after `python -m scripts.seed_users` on that database; change passwords in real deployments):

| Role | Email | Password |
|---|---|---|
| Admin | admin@test.com | AdminTest123! |
| Marketer | marketer@test.com | MarketerTest123! |
| Viewer | viewer@test.com | ViewerTest123! |

### Deployment Summary

1. Build Docker image
2. Push image to Artifact Registry
3. Create Cloud SQL PostgreSQL instance
4. Deploy FastAPI container to Cloud Run
5. Connect Cloud Run to Cloud SQL
6. Apply schema (`migrations/001_initial_schema.sql` or proxy + `create_all`) and seed users/data (`scripts/deploy/seed-cloudsql.ps1` or manual proxy)
7. Create Memorystore Redis
8. Create Serverless VPC Access connector
9. Connect Cloud Run to Redis (private IP + connector)
10. Verify `/health`, `/docs`, public search, login, admin store APIs, and admin user APIs

Step-by-step commands and variable templates are in `GCP_DEPLOYMENT_GUIDE.md`.

---

## Production Notes

- Do not commit `.env`.
- Use a strong `JWT_SECRET_KEY` (see `.env.example`).
- Avoid running `Base.metadata.create_all(bind=engine)` during Cloud Run startup.
- Initialize production schema with `migrations/001_initial_schema.sql` (or your migration runner) and seed via scripts.
- Restrict CORS origins for a real frontend.
- Use Secret Manager for production secrets.
- Delete or stop Cloud SQL and Memorystore resources when not needed to avoid charges.

---

## Known Practical Design Choices

### Local DB fallback for geocoding

The app uses external geocoding first, then falls back to local store data for demo stability.

### Redis fallback behavior

If Redis is unavailable, cache and rate limit logic fail open instead of breaking the API. This keeps public search available during cache outages.

### PATCH restrictions

PATCH only allows:

- `name`
- `phone`
- `services`
- `status`
- `hours_*`

It does not allow:

- `store_id`
- `latitude`
- `longitude`
- address fields

### Soft delete

Deleting a store sets:

```text
status = inactive
```

No physical database row is deleted.

---

## Future Improvements

- Optional Alembic revision history on top of the baseline SQL in `migrations/`
- Secret Manager integration for all production secrets
- CI/CD with Cloud Build or GitHub Actions
- Dedicated user management endpoints
- Admin frontend dashboard
- Store ratings and reviews
- Better holiday/special-hours support
- GKE deployment option for Kubernetes-focused portfolio version
