# scripts/deploy/rebuild-push-deploy.ps1

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Resolve-Path "$SCRIPT_DIR\..\.."

Write-Host "Loading GCP variables..."
& "$SCRIPT_DIR\load-gcp-vars.ps1"

. "$PROJECT_ROOT\gcp-vars.generated.ps1"

Set-Location $PROJECT_ROOT

Write-Host ""
Write-Host "Building Docker image..."
docker build -t $IMAGE_URI .

Write-Host ""
Write-Host "Pushing Docker image..."
docker push $IMAGE_URI

Write-Host ""
Write-Host "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME `
  --image=$IMAGE_URI `
  --region=$REGION `
  --platform=managed `
  --allow-unauthenticated `
  --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME `
  --vpc-connector=$VPC_CONNECTOR `
  --vpc-egress=private-ranges-only `
  --env-vars-file="$PROJECT_ROOT\cloudrun-env.generated.yaml"

Write-Host ""
Write-Host "Getting service URL..."
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)"
Write-Host "SERVICE_URL=$SERVICE_URL"

Write-Host ""
Write-Host "Testing health endpoint..."
curl "$SERVICE_URL/health"

Write-Host ""
Write-Host "Deployment complete."