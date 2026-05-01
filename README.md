# Store Locator Service

A production-style Store Locator API service for a multi-location retail business.

The system supports public store search by address, ZIP code, or latitude/longitude, and secure internal store management with JWT authentication and role-based access control.

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
- Replaces store services during update
- Returns detailed import report

### Testing

- Unit tests
- API tests
- Integration tests
- Mocked external geocoding calls using `unittest.mock.MagicMock` and `patch`
- Redis/rate-limit behavior tested with mocks
- Current result:

```text
40 passed
Total coverage: 83%
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
│   │   └── admin_stores.py
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
│   │   └── admin_store.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── cache.py
│   │   ├── csv_import.py
│   │   ├── distance.py
│   │   ├── geocoding.py
│   │   ├── hours.py
│   │   └── store_search.py
│   └── main.py
├── scripts/
│   ├── load_stores.py
│   └── seed_users.py
├── tests/
├── data/
│   ├── stores_50.csv
│   └── stores_1000.csv
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
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

```bash
python -c "from app.db.base import Base; from app.db.session import engine; import app.models; Base.metadata.create_all(bind=engine)"
```

### 5. Load store data

If direct script execution cannot import `app`, run scripts as modules:

```bash
type nul > scripts\__init__.py
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

Swagger UI:

```text
/docs
```

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

Generate HTML coverage report:

```bash
pytest --cov=app --cov-report=html
```

Current result:

```text
40 passed
Total coverage: 83%
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

---

## Deployment

Final deployment platform:

```text
Google Cloud Platform
```

Components:

| Component | Platform |
|---|---|
| API server | Cloud Run |
| Container image | Artifact Registry |
| Database | Cloud SQL for PostgreSQL |
| Cache / rate limit | Memorystore Redis |
| Redis private access | Serverless VPC Access Connector |

Production URLs:

```text
API Base URL: <YOUR_CLOUD_RUN_URL>
Swagger: <YOUR_CLOUD_RUN_URL>/docs
Health: <YOUR_CLOUD_RUN_URL>/health
```

### Deployment Summary

1. Build Docker image
2. Push image to Artifact Registry
3. Create Cloud SQL PostgreSQL instance
4. Deploy FastAPI container to Cloud Run
5. Connect Cloud Run to Cloud SQL
6. Initialize Cloud SQL schema and data through Cloud SQL Auth Proxy
7. Create Memorystore Redis
8. Create Serverless VPC Access connector
9. Connect Cloud Run to Redis
10. Verify `/health`, `/docs`, public search, login, and admin APIs

Detailed deployment commands are documented in `GCP_DEPLOYMENT_GUIDE.md`.

---

## Production Notes

- Do not commit `.env`.
- Use a strong `JWT_SECRET_KEY`.
- Avoid running `Base.metadata.create_all(bind=engine)` during Cloud Run startup.
- Initialize production schema and seed data through script or migration.
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

- Alembic migrations instead of manual `create_all`
- Secret Manager integration for all production secrets
- CI/CD with Cloud Build or GitHub Actions
- Dedicated user management endpoints
- Admin frontend dashboard
- Store ratings and reviews
- Better holiday/special-hours support
- GKE deployment option for Kubernetes-focused portfolio version
