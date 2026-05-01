# GCP Deployment Guide - Store Locator Service

This guide documents the final deployment process used for the Store Locator Service.

## Final GCP Architecture

```text
User / Swagger / API Client
        |
        v
Cloud Run HTTPS URL
        |
        v
FastAPI Docker Container
   |          |           |
   v          v           v
Cloud SQL    Memorystore  External Geocoding APIs
PostgreSQL   Redis        Zippopotam.us / US Census
```

Components:

- Application server: Google Cloud Run
- Container registry: Google Artifact Registry
- Database: Cloud SQL for PostgreSQL
- Cache / rate limiting: Memorystore for Redis
- Private Redis access: Serverless VPC Access Connector
- Local Cloud SQL seeding: Cloud SQL Auth Proxy

---

## 1. Set Variables

PowerShell:

```powershell
$PROJECT_ID="store-locator-service"
$REGION="us-central1"
$SERVICE_NAME="store-locator-service"
$REPO_NAME="store-locator-repo"
$IMAGE_NAME="store-locator-api"
$INSTANCE_NAME="store-locator-postgres"
$DB_NAME="store_locator"
$DB_USER="store_user"
$DB_PASSWORD="StoreLocatorPass12345"
```

Set project:

```powershell
gcloud auth login
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION
```

---

## 2. Enable Required APIs

```powershell
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable vpcaccess.googleapis.com
```

---

## 3. Create Artifact Registry

```powershell
gcloud artifacts repositories create $REPO_NAME `
  --repository-format=docker `
  --location=$REGION `
  --description="Store Locator Docker repository"
```

Configure Docker authentication:

```powershell
gcloud auth configure-docker "$REGION-docker.pkg.dev"
```

Generate image URI:

```powershell
$IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME`:latest"
echo $IMAGE_URI
```

Expected format:

```text
us-central1-docker.pkg.dev/store-locator-service/store-locator-repo/store-locator-api:latest
```

---

## 4. Create Cloud SQL PostgreSQL

Use Enterprise edition explicitly. Do not use `db-f1-micro` with Enterprise Plus.

```powershell
gcloud sql instances create $INSTANCE_NAME `
  --database-version=POSTGRES_16 `
  --edition=ENTERPRISE `
  --tier=db-g1-small `
  --region=$REGION `
  --storage-size=10GB `
  --storage-type=SSD
```

Create database:

```powershell
gcloud sql databases create $DB_NAME `
  --instance=$INSTANCE_NAME
```

Create user:

```powershell
gcloud sql users create $DB_USER `
  --instance=$INSTANCE_NAME `
  --password=$DB_PASSWORD
```

Get instance connection name:

```powershell
$INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe $INSTANCE_NAME --format="value(connectionName)")
echo $INSTANCE_CONNECTION_NAME
```

Expected:

```text
store-locator-service:us-central1:store-locator-postgres
```

---

## 5. Prepare Cloud Run DATABASE_URL

For Cloud Run + Cloud SQL Unix socket:

```powershell
$CLOUD_SQL_DATABASE_URL="postgresql+psycopg2://$DB_USER`:$DB_PASSWORD@/$DB_NAME`?host=/cloudsql/$INSTANCE_CONNECTION_NAME"
echo $CLOUD_SQL_DATABASE_URL
```

Expected format:

```text
postgresql+psycopg2://store_user:StoreLocatorPass12345@/store_locator?host=/cloudsql/store-locator-service:us-central1:store-locator-postgres
```

---

## 6. Build and Push Docker Image

From project root:

```powershell
docker build -t $IMAGE_URI .
docker push $IMAGE_URI
```

---

## 7. Important Production Fix

In `app/main.py`, do not run table creation during Cloud Run startup:

```python
# Base.metadata.create_all(bind=engine)
```

Reason:

- Cloud Run must start and listen on `$PORT`.
- If the app tries to connect to Cloud SQL during import/startup and the socket is not ready, the container may fail before listening.
- Schema creation should be done once through a seed/migration step.

---

## 8. Grant Cloud SQL Permission to Cloud Run Service Account

```powershell
$PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
$RUN_SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$RUN_SA" `
  --role="roles/cloudsql.client"
```

---

## 9. Create Cloud Run Environment File

Create `cloudrun-env.yaml`:

```yaml
DATABASE_URL: "postgresql+psycopg2://store_user:StoreLocatorPass12345@/store_locator?host=/cloudsql/store-locator-service:us-central1:store-locator-postgres"
JWT_SECRET_KEY: "replace-this-with-a-long-random-secret-key-at-least-32-bytes"
JWT_ALGORITHM: "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: "15"
REFRESH_TOKEN_EXPIRE_DAYS: "7"
REDIS_URL: "redis://127.0.0.1:6379/0"
GEOCODING_CACHE_TTL_SECONDS: "2592000"
SEARCH_CACHE_TTL_SECONDS: "600"
RATE_LIMIT_PER_MINUTE: "10"
RATE_LIMIT_PER_HOUR: "100"
US_CENSUS_GEOCODER_URL: "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
US_CENSUS_BENCHMARK: "Public_AR_Current"
ZIPPOPOTAMUS_URL: "https://api.zippopotam.us/us"
```

This file is for deployment only. Do not commit real secrets.

---

## 10. Deploy Cloud Run with Cloud SQL

```powershell
gcloud run deploy $SERVICE_NAME `
  --image=$IMAGE_URI `
  --region=$REGION `
  --platform=managed `
  --allow-unauthenticated `
  --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME `
  --env-vars-file=cloudrun-env.yaml
```

Get service URL:

```powershell
$SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
echo $SERVICE_URL
```

Verify:

```powershell
curl "$SERVICE_URL/health"
```

At this stage Redis may show unavailable until Memorystore is connected.

---

## 11. Initialize Cloud SQL Data

Cloud SQL is separate from local Docker PostgreSQL. Local seed data does not automatically exist in Cloud SQL.

### 11.1 Set up ADC

```powershell
gcloud auth application-default login
```

### 11.2 Start Cloud SQL Auth Proxy

From the directory containing `cloud-sql-proxy.exe`:

```powershell
.\cloud-sql-proxy.exe $INSTANCE_CONNECTION_NAME --port 5433
```

Keep this terminal open.

### 11.3 Run schema creation and seed scripts

Open another PowerShell terminal in project root:

```powershell
.\.venv\Scripts\Activate.ps1

$env:DATABASE_URL="postgresql://$DB_USER`:$DB_PASSWORD@localhost:5433/$DB_NAME"

python -c "from app.db.base import Base; from app.db.session import engine; import app.models; Base.metadata.create_all(bind=engine)"
```

If direct script import fails with `ModuleNotFoundError: No module named 'app'`, use module mode:

```powershell
type nul > scripts\__init__.py

python -m scripts.load_stores data/stores_1000.csv
python -m scripts.seed_users
```

Verify:

```powershell
python -c "from app.db.session import SessionLocal; from app.models.store import Store; from app.models.user import User; db=SessionLocal(); print('stores:', db.query(Store).count()); print('users:', db.query(User).count()); db.close()"
```

Expected:

```text
stores: 1000
users: 3
```

---

## 12. Create Memorystore Redis

```powershell
$REDIS_INSTANCE="store-locator-redis"

gcloud redis instances create $REDIS_INSTANCE `
  --size=1 `
  --region=$REGION `
  --redis-version=redis_7_0
```

Get Redis host:

```powershell
$REDIS_HOST=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="value(host)")
echo $REDIS_HOST
```

Create Redis URL:

```powershell
$PROD_REDIS_URL="redis://$REDIS_HOST`:6379/0"
echo $PROD_REDIS_URL
```

---

## 13. Create Serverless VPC Access Connector

Connector ID must be short enough. `store-locator-vpc-connector` is too long.

Use:

```powershell
$VPC_CONNECTOR="store-vpc"

gcloud compute networks vpc-access connectors create $VPC_CONNECTOR `
  --region=$REGION `
  --network=default `
  --range=10.8.0.0/28
```

Check status:

```powershell
gcloud compute networks vpc-access connectors describe $VPC_CONNECTOR `
  --region=$REGION
```

Wait until state is `READY`.

---

## 14. Connect Cloud Run to Memorystore Redis

Update Cloud Run with VPC connector and Redis URL:

```powershell
gcloud run services update $SERVICE_NAME `
  --region=$REGION `
  --vpc-connector=$VPC_CONNECTOR `
  --vpc-egress=private-ranges-only `
  --update-env-vars="REDIS_URL=$PROD_REDIS_URL"
```

Verify:

```powershell
curl "$SERVICE_URL/health"
```

Expected:

```json
{
  "status": "ok",
  "redis": "ok"
}
```

---

## 15. Verify Production

### Health

```powershell
curl "$SERVICE_URL/health"
```

### Swagger

Open:

```text
<SERVICE_URL>/docs
```

### Public Search

```powershell
curl -X POST "$SERVICE_URL/api/stores/search" `
  -H "Content-Type: application/json" `
  -d "{\"postal_code\":\"10001\",\"radius_miles\":20}"
```

### Login

```powershell
curl -X POST "$SERVICE_URL/api/auth/login" `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"admin@test.com\",\"password\":\"AdminTest123!\"}"
```

Use the returned access token in Swagger:

```text
Bearer <access_token>
```

Then test:

```text
GET /api/admin/stores
POST /api/admin/stores
PATCH /api/admin/stores/{store_id}
DELETE /api/admin/stores/{store_id}
POST /api/admin/stores/import
```

---

## 16. Troubleshooting Notes

### Cloud Run failed to listen on PORT=8080

Check logs:

```powershell
gcloud run services logs read $SERVICE_NAME `
  --region=$REGION `
  --limit=100
```

Common causes:

- App crashed before listening.
- `Base.metadata.create_all(bind=engine)` ran during startup and Cloud SQL was unavailable.
- Wrong `DATABASE_URL`.
- Missing package in `requirements.txt`.
- Container command does not listen on `0.0.0.0:$PORT`.

### Cloud SQL socket connection refused

Check:

```powershell
gcloud sql instances describe $INSTANCE_NAME --format="value(state)"
gcloud run services describe $SERVICE_NAME --region=$REGION --format="yaml(metadata.annotations)"
```

Make sure:

- Cloud SQL state is `RUNNABLE`.
- Cloud Run has Cloud SQL instance annotation.
- Cloud Run service account has `roles/cloudsql.client`.
- `DATABASE_URL` uses `/cloudsql/<INSTANCE_CONNECTION_NAME>`.

### Cloud SQL Auth Proxy credential error

Run:

```powershell
gcloud auth application-default login
```

### Script cannot import app

Use module mode:

```powershell
type nul > scripts\__init__.py
python -m scripts.load_stores data/stores_1000.csv
python -m scripts.seed_users
```

### VPC connector name invalid

Use short connector ID:

```powershell
$VPC_CONNECTOR="store-vpc"
```

---

## 17. Final Deployment Checklist

- [x] Docker image builds locally
- [x] Cloud Run deployed
- [x] Cloud SQL PostgreSQL created
- [x] Cloud SQL schema initialized
- [x] stores table loaded with 1000 records
- [x] seed users created
- [x] Artifact Registry stores Docker image
- [x] Memorystore Redis deployed
- [x] Serverless VPC Access connector created
- [x] Cloud Run connected to Redis
- [x] `/health` responds
- [x] `/docs` accessible
- [x] public search works
- [x] login works
- [x] admin endpoints work with JWT
