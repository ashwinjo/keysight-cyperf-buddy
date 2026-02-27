# CyperfBuddy Deployment Guide — Google Cloud Run

Complete step-by-step guide to deploy the entire CyperfBuddy stack (Frontend, Backend, Redis, PostgreSQL) to Google Cloud Run.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Google Cloud Setup](#google-cloud-setup)
4. [Database Setup (Cloud SQL PostgreSQL)](#database-setup-cloud-sql-postgresql)
5. [Redis Setup (Cloud Memorystore)](#redis-setup-cloud-memorystore)
6. [Build & Push Docker Images](#build--push-docker-images)
7. [Deploy Backend to Cloud Run](#deploy-backend-to-cloud-run)
8. [Deploy Frontend to Cloud Run](#deploy-frontend-to-cloud-run)
9. [Configure Networking](#configure-networking)
10. [Environment Variables & Secrets](#environment-variables--secrets)
11. [Verification & Testing](#verification--testing)
12. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
13. [Cost Optimization](#cost-optimization)

---

## Prerequisites

### Required Tools

```bash
# Install Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# Verify installation
gcloud --version
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Install Docker
# https://docs.docker.com/get-docker/

# Verify Docker
docker --version
```

### Required GCP Services (Enable in Console)

- ☐ Cloud Run
- ☐ Cloud SQL Admin API
- ☐ Cloud Memorystore for Redis API
- ☐ Container Registry (or Artifact Registry)
- ☐ Cloud Build (optional, for automated builds)
- ☐ Secret Manager (for secure credential storage)

```bash
# Enable services via CLI
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  containerregistry.googleapis.com \
  secretmanager.googleapis.com
```

### Environment Details

- **Project ID:** `your-gcp-project-id`
- **Region:** `us-central1` (adjust as needed)
- **Frontend Port:** 3000
- **Backend Port:** 8000
- **Redis Port:** 6379
- **PostgreSQL Port:** 5432

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Google Cloud Run                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐         ┌──────────────────────┐     │
│  │  Frontend Service│         │  Backend Service     │     │
│  │  (React+Vite)    │────────→│  (FastAPI)           │     │
│  │  Port: 3000      │ HTTPS   │  Port: 8000          │     │
│  └──────────────────┘         └──────────────────────┘     │
│                                         ↓                   │
│                              ┌──────────────────────┐       │
│                              │  Cloud SQL           │       │
│                              │  (PostgreSQL 15)     │       │
│                              │  Private IP          │       │
│                              └──────────────────────┘       │
│                                         ↑                   │
│                              ┌──────────────────────┐       │
│                              │  Cloud Memorystore   │       │
│                              │  (Redis 7)           │       │
│                              │  Private IP          │       │
│                              └──────────────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Key Design Decisions:**
- Frontend and Backend run as separate Cloud Run services
- Both services communicate over HTTPS
- Database and Redis are managed services (not containerized)
- Services connect to DB/Redis via private IP (VPC Connector)
- All traffic encrypted in transit
- Environment variables stored in Secret Manager

---

## Google Cloud Setup

### Step 1: Create a GCP Project

```bash
# Set your project ID
export PROJECT_ID="cyperf-buddy-prod"
export REGION="us-central1"

# Create project
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# Enable billing
gcloud billing projects link $PROJECT_ID --billing-account=BILLING_ACCOUNT_ID
```

### Step 2: Create VPC for Private Connectivity

```bash
# Create VPC network
gcloud compute networks create cyperf-network \
  --subnet-mode=auto \
  --bgp-routing-mode=regional

# Create VPC Connector (required for Cloud Run ↔ Cloud SQL/Redis)
gcloud compute networks vpc-access connectors create cyperf-connector \
  --network=cyperf-network \
  --region=$REGION \
  --min-throughput=200 \
  --max-throughput=300
```

### Step 3: Set Up Secret Manager

Store sensitive credentials securely:

```bash
# Store Keysight CyPerf credentials
echo -n "admin" | gcloud secrets create cyperf-username --data-file=-
echo -n "CyPerf&Keysight#1" | gcloud secrets create cyperf-password --data-file=-

# Store SMTP credentials (for contact form emails)
echo -n "your-smtp-user@gmail.com" | gcloud secrets create smtp-user --data-file=-
echo -n "your-app-password" | gcloud secrets create smtp-password --data-file=-

# Store JWT secret (if using authentication)
echo -n "$(openssl rand -hex 32)" | gcloud secrets create jwt-secret --data-file=-

# List created secrets
gcloud secrets list
```

### Step 4: Create Service Account

```bash
# Create dedicated service account for Cloud Run services
gcloud iam service-accounts create cyperf-app \
  --display-name="CyperfBuddy Application"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:cyperf-app@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/cloudsql.client

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:cyperf-app@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/redis.editor

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:cyperf-app@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor

# Allow service account to access VPC Connector
gcloud compute networks vpc-access connectors add-iam-policy-binding cyperf-connector \
  --region=$REGION \
  --member=serviceAccount:cyperf-app@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/compute.networkUser
```

---

## Database Setup (Cloud SQL PostgreSQL)

### Step 1: Create Cloud SQL Instance

```bash
# Create PostgreSQL 15 instance
gcloud sql instances create cyperf-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --network=cyperf-network \
  --no-backup \
  --availability-type=ZONAL \
  --enable-bin-log=false

# Note: db-f1-micro is free tier. For production, use db-custom-2-7680 or higher.
```

### Step 2: Create Database & User

```bash
# Get the connection name
export DB_CONNECTION_NAME=$(gcloud sql instances describe cyperf-db \
  --format='value(connectionName)')

echo "Connection name: $DB_CONNECTION_NAME"

# Create database
gcloud sql databases create cyperf_cve_prod \
  --instance=cyperf-db \
  --charset=utf8mb4

# Create application user
gcloud sql users create cyperf_app \
  --instance=cyperf-db \
  --password

# Note: You'll be prompted to set a password. Save this!
export DB_PASSWORD="your-generated-password"

# Create root user password (for migrations)
gcloud sql users set-password postgres \
  --instance=cyperf-db \
  --password

export DB_ROOT_PASSWORD="your-root-password"
```

### Step 3: Configure Database Connection

```bash
# Get the private IP of the Cloud SQL instance
export DB_PRIVATE_IP=$(gcloud sql instances describe cyperf-db \
  --format='value(ipAddresses[0].ipAddress)')

echo "Database Private IP: $DB_PRIVATE_IP"

# Connection string for application
export DATABASE_URL="postgresql://cyperf_app:${DB_PASSWORD}@${DB_PRIVATE_IP}:5432/cyperf_cve_prod"

# Save this for later use in environment variables
```

### Step 4: Run Database Migrations

```bash
# From your local machine, connect and run migrations
gcloud sql connect cyperf-db \
  --user=postgres

# Or use Cloud SQL Proxy for local development:
# cloud_sql_proxy -instances=$DB_CONNECTION_NAME=tcp:5432 &
# psql -h 127.0.0.1 -U postgres -d cyperf_cve_prod
```

---

## Redis Setup (Cloud Memorystore)

### Step 1: Create Redis Instance

```bash
# Create Redis instance
gcloud redis instances create cyperf-redis \
  --size=1 \
  --region=$REGION \
  --redis-version=7.0 \
  --network=cyperf-network \
  --tier=basic

# Note: size=1 means 1GB (free tier limit). For production, increase size.
```

### Step 2: Get Redis Connection Details

```bash
# Get Redis host and port
export REDIS_HOST=$(gcloud redis instances describe cyperf-redis \
  --region=$REGION \
  --format='value(host)')

export REDIS_PORT=$(gcloud redis instances describe cyperf-redis \
  --region=$REGION \
  --format='value(port)')

echo "Redis URL: redis://${REDIS_HOST}:${REDIS_PORT}/0"

# Store for later
export REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}/0"
```

### Step 3: Test Redis Connection (Optional)

```bash
# Install redis-cli locally
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-tools

# Connect using Cloud SQL Proxy pattern (or direct if same network)
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping
# Should return: PONG
```

---

## Build & Push Docker Images

### Step 1: Configure Docker for GCP

```bash
# Authenticate Docker with GCP
gcloud auth configure-docker

# Set image registry
export IMAGE_REGISTRY="gcr.io/${PROJECT_ID}"
```

### Step 2: Build Backend Docker Image

```bash
# Navigate to project root
cd /Users/ashwin.joshi/claudeExp

# Create backend Dockerfile (if not exists)
# File: backend/Dockerfile

cat > backend/Dockerfile << 'EOF'
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir uv
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Build backend image
docker build -t ${IMAGE_REGISTRY}/cyperf-backend:latest backend/

# Push to Container Registry
docker push ${IMAGE_REGISTRY}/cyperf-backend:latest
```

### Step 3: Build Frontend Docker Image

```bash
# Create frontend Dockerfile
cat > frontend/Dockerfile << 'EOF'
# Build stage
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM node:22-alpine

WORKDIR /app

# Install serve to serve static files
RUN npm install -g serve

# Copy built files from builder
COPY --from=builder /app/dist ./dist

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

# Serve the React app
CMD ["serve", "-s", "dist", "-l", "3000"]
EOF

# Build frontend image
docker build -t ${IMAGE_REGISTRY}/cyperf-frontend:latest frontend/

# Push to Container Registry
docker push ${IMAGE_REGISTRY}/cyperf-frontend:latest
```

### Step 4: Verify Images

```bash
# List images in Container Registry
gcloud container images list --repository-format=json | grep cyperf

# Get image details
gcloud container images describe ${IMAGE_REGISTRY}/cyperf-backend:latest
gcloud container images describe ${IMAGE_REGISTRY}/cyperf-frontend:latest
```

---

## Deploy Backend to Cloud Run

### Step 1: Deploy Backend Service

```bash
# Deploy backend
gcloud run deploy cyperf-backend \
  --image=${IMAGE_REGISTRY}/cyperf-backend:latest \
  --region=$REGION \
  --platform=managed \
  --service-account=cyperf-app@${PROJECT_ID}.iam.gserviceaccount.com \
  --vpc-connector=cyperf-connector \
  --vpc-egress=private-ranges-only \
  --memory=512Mi \
  --cpu=1 \
  --timeout=3600 \
  --max-instances=10 \
  --no-allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO"

# Note:
# - --no-allow-unauthenticated requires authentication (see next step)
# - For public access, use --allow-unauthenticated
```

### Step 2: Configure Backend Environment Variables

```bash
# Update service with environment variables
gcloud run services update cyperf-backend \
  --region=$REGION \
  --update-env-vars=\
DATABASE_URL=$(gcloud secrets versions access latest --secret=db-url),\
REDIS_URL=$(gcloud secrets versions access latest --secret=redis-url),\
CYPERF_USERNAME=$(gcloud secrets versions access latest --secret=cyperf-username),\
CYPERF_PASSWORD=$(gcloud secrets versions access latest --secret=cyperf-password),\
CYPERF_CONTROLLER_IP=$(gcloud secrets versions access latest --secret=cyperf-endpoint),\
SMTP_USER=$(gcloud secrets versions access latest --secret=smtp-user),\
SMTP_PASSWORD=$(gcloud secrets versions access latest --secret=smtp-password)

# Store secrets first if not done:
echo -n "postgresql://cyperf_app:PASSWORD@DB_IP:5432/cyperf_cve_prod" | \
  gcloud secrets create db-url --data-file=-

echo -n "redis://REDIS_IP:6379/0" | \
  gcloud secrets create redis-url --data-file=-

echo -n "44.255.23.243" | \
  gcloud secrets create cyperf-endpoint --data-file=-
```

### Step 3: Get Backend URL

```bash
# Get the service URL
export BACKEND_URL=$(gcloud run services describe cyperf-backend \
  --region=$REGION \
  --format='value(status.url)')

echo "Backend URL: $BACKEND_URL"
echo "Backend API: ${BACKEND_URL}/health/"
```

### Step 4: Enable Public Access (Optional)

If you want public API access without authentication:

```bash
gcloud run services add-iam-policy-binding cyperf-backend \
  --region=$REGION \
  --member=allUsers \
  --role=roles/run.invoker
```

---

## Deploy Frontend to Cloud Run

### Step 1: Create Frontend Configuration

Frontend needs to know the backend URL. Create a `.env.production` or use build-time config:

```bash
# Option 1: Build-time environment variable
export VITE_API_URL="${BACKEND_URL}"

# Option 2: Runtime configuration (injected via docker-entrypoint.sh)
# See advanced section below
```

### Step 2: Update Vite Config for Production

```typescript
// frontend/vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/admin': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### Step 3: Deploy Frontend Service

```bash
# Rebuild with production backend URL
docker build \
  --build-arg VITE_API_URL="${BACKEND_URL}" \
  -t ${IMAGE_REGISTRY}/cyperf-frontend:latest \
  frontend/

docker push ${IMAGE_REGISTRY}/cyperf-frontend:latest

# Deploy to Cloud Run
gcloud run deploy cyperf-frontend \
  --image=${IMAGE_REGISTRY}/cyperf-frontend:latest \
  --region=$REGION \
  --platform=managed \
  --service-account=cyperf-app@${PROJECT_ID}.iam.gserviceaccount.com \
  --memory=256Mi \
  --cpu=1 \
  --timeout=60 \
  --max-instances=10 \
  --allow-unauthenticated \
  --set-env-vars="VITE_API_URL=${BACKEND_URL}"
```

### Step 4: Get Frontend URL

```bash
# Get the service URL
export FRONTEND_URL=$(gcloud run services describe cyperf-frontend \
  --region=$REGION \
  --format='value(status.url)')

echo "Frontend URL: $FRONTEND_URL"
```

---

## Configure Networking

### Step 1: Enable Service-to-Service Communication

```bash
# Allow frontend to call backend
gcloud run services add-iam-policy-binding cyperf-backend \
  --region=$REGION \
  --member=serviceAccount:cyperf-app@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/run.invoker
```

### Step 2: Configure CORS (if needed)

Update backend to accept requests from frontend domain:

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://*.run.app",  # Allow all Cloud Run URLs
        f"https://{FRONTEND_DOMAIN}",  # Your frontend domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Step 3: Set Up Custom Domain (Optional)

```bash
# Map custom domain to frontend
gcloud beta run domain-mappings create \
  --service=cyperf-frontend \
  --domain=cyperf.yourdomain.com \
  --region=$REGION

# Verify DNS records pointed to Cloud Run
# Follow gcloud output for CNAME/A records
```

---

## Environment Variables & Secrets

### Complete Environment Variables List

**Backend:**
```
ENVIRONMENT=production
LOG_LEVEL=INFO
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
CYPERF_CONTROLLER_IP=44.255.23.243
CYPERF_USERNAME=admin
CYPERF_PASSWORD=***
CYPERF_SYNC_INTERVAL_HOURS=24
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=***
SMTP_FROM_NAME=CyperfBuddy
```

**Frontend:**
```
VITE_API_URL=https://cyperf-backend-xxxxx.run.app
NODE_ENV=production
```

### Manage Secrets Script

```bash
#!/bin/bash
# save as: scripts/manage-secrets.sh

PROJECT_ID="cyperf-buddy-prod"
REGION="us-central1"

# Create secrets from .env file
create_secrets() {
  # Database
  gcloud secrets create database-url --data-file=- << EOF
postgresql://cyperf_app:${DB_PASSWORD}@${DB_IP}:5432/cyperf_cve_prod
EOF

  # Redis
  gcloud secrets create redis-url --data-file=- << EOF
redis://${REDIS_IP}:6379/0
EOF

  # Keysight credentials
  gcloud secrets create cyperf-username --data-file=- << EOF
admin
EOF

  gcloud secrets create cyperf-password --data-file=- << EOF
${CYPERF_PASSWORD}
EOF

  # SMTP
  gcloud secrets create smtp-user --data-file=- << EOF
${SMTP_USER}
EOF

  gcloud secrets create smtp-password --data-file=- << EOF
${SMTP_PASSWORD}
EOF
}

# Rotate secret
rotate_secret() {
  local SECRET_NAME=$1
  local NEW_VALUE=$2
  echo -n "$NEW_VALUE" | gcloud secrets versions add $SECRET_NAME --data-file=-
}

# Usage
case "$1" in
  create) create_secrets ;;
  rotate) rotate_secret $2 $3 ;;
  *) echo "Usage: $0 {create|rotate SECRET_NAME NEW_VALUE}" ;;
esac
```

---

## Verification & Testing

### Step 1: Test Backend Health

```bash
# Check backend health endpoint
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  ${BACKEND_URL}/health/

# Should return:
# {"status":"ok"}
```

### Step 2: Test Database Connection

```bash
# Check database connectivity from backend logs
gcloud run logs read cyperf-backend \
  --region=$REGION \
  --limit=50

# Should show: "Database connection successful" or similar
```

### Step 3: Test Redis Connection

```bash
# Check Redis connectivity from logs
gcloud run logs read cyperf-backend \
  --region=$REGION \
  --limit=50 | grep -i redis
```

### Step 4: Test API Endpoints

```bash
# Get auth token for protected endpoints
export TOKEN=$(gcloud auth print-identity-token)

# Test CVE search endpoint
curl -H "Authorization: Bearer $TOKEN" \
  "${BACKEND_URL}/api/cve/search?q=CVE-2024-1234"

# Test admin endpoint
curl -H "Authorization: Bearer $TOKEN" \
  "${BACKEND_URL}/admin/sync-status"

# Test health check (public)
curl "${BACKEND_URL}/health/"
```

### Step 5: Test Frontend

```bash
# Open in browser
echo $FRONTEND_URL
# Visit: https://cyperf-frontend-xxxxx.run.app

# Check browser console for errors
# Test search functionality
# Test CVE lookup
```

---

## Monitoring & Troubleshooting

### Step 1: View Logs

```bash
# Backend logs (last 50 lines)
gcloud run logs read cyperf-backend \
  --region=$REGION \
  --limit=50

# Frontend logs
gcloud run logs read cyperf-frontend \
  --region=$REGION \
  --limit=50

# Real-time logs
gcloud run logs read cyperf-backend \
  --region=$REGION \
  --follow

# Filter by severity
gcloud run logs read cyperf-backend \
  --region=$REGION \
  --filter='severity=ERROR'
```

### Step 2: Monitor Performance

```bash
# View service metrics
gcloud monitoring time-series list \
  --filter='resource.type=cloud_run_revision AND resource.label.service_name=cyperf-backend'

# Get request count
gcloud monitoring read \
  --filter='metric.type=run.googleapis.com/request_count' \
  --start-time='-1h'

# Get latency
gcloud monitoring read \
  --filter='metric.type=run.googleapis.com/request_latencies' \
  --start-time='-1h'
```

### Step 3: Common Issues & Solutions

#### Issue: "Permission denied" accessing database

**Solution:**
```bash
# Ensure VPC Connector is working
gcloud compute networks vpc-access connectors describe cyperf-connector \
  --region=$REGION

# Verify IAM binding
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:cyperf-app@"
```

#### Issue: "Redis connection timeout"

**Solution:**
```bash
# Check Redis instance status
gcloud redis instances describe cyperf-redis --region=$REGION

# Verify network connectivity
gcloud redis instances describe cyperf-redis --region=$REGION \
  --format='value(host,port)'

# Test with redis-cli from a Cloud Shell
redis-cli -h REDIS_HOST -p REDIS_PORT ping
```

#### Issue: "Database connection refused"

**Solution:**
```bash
# Check Cloud SQL instance status
gcloud sql instances describe cyperf-db

# Verify private IP
gcloud sql instances describe cyperf-db --format='value(ipAddresses[0].ipAddress)'

# Check IAM permissions
gcloud sql instances describe cyperf-db \
  --format='value(settings.ipConfiguration.authorizedNetworks)'
```

#### Issue: "Frontend cannot reach backend"

**Solution:**
```bash
# Verify backend URL is correct
echo $BACKEND_URL

# Check CORS configuration
curl -i -X OPTIONS \
  -H "Origin: ${FRONTEND_URL}" \
  "${BACKEND_URL}/api/cve/search"

# Should include: Access-Control-Allow-Origin header
```

---

## Cost Optimization

### Step 1: Use Cloud Run's Free Tier

```
Cloud Run: 2M requests/month FREE
Cloud SQL: 7 days backup, free quota available
Cloud Memorystore: 1GB instance within free tier

Monthly estimated costs:
- Cloud Run: $0 (within free tier)
- Cloud SQL: ~$9-15 (small instance)
- Cloud Memorystore: $0 (within free tier)
- Networking: ~$1-5
───────────────────────────
Total: ~$10-20/month for production-ready setup
```

### Step 2: Optimize Instance Sizes

```bash
# Use smallest tiers for low traffic
# Backend: 256Mi memory, 0.5 CPU
# Frontend: 128Mi memory, 0.25 CPU

gcloud run services update cyperf-backend \
  --region=$REGION \
  --memory=256Mi \
  --cpu=0.5

gcloud run services update cyperf-frontend \
  --region=$REGION \
  --memory=128Mi \
  --cpu=0.25

# Scale down max instances during off-peak
gcloud run services update cyperf-backend \
  --region=$REGION \
  --max-instances=5
```

### Step 3: Monitor Costs

```bash
# Enable Cost Analysis in GCP Console
# Menu → Billing → Reports

# Set budget alerts
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="CyperfBuddy Monthly" \
  --budget-amount=50 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=100

# View cost breakdown by service
gcloud billing accounts list
```

---

## Post-Deployment Checklist

- [ ] Backend service deployed and healthy
- [ ] Frontend service deployed and healthy
- [ ] Database is accessible from backend
- [ ] Redis is accessible from backend
- [ ] Frontend can reach backend API
- [ ] All environment variables are set
- [ ] Secrets are securely stored
- [ ] Health checks pass
- [ ] API endpoints return correct responses
- [ ] Search functionality works end-to-end
- [ ] Contact form submissions work (email sending)
- [ ] Sync scheduled job is running (check logs)
- [ ] Logs are being collected (Cloud Logging)
- [ ] Monitoring alerts are configured
- [ ] SSL/TLS certificates are valid
- [ ] Custom domain is configured (if using)
- [ ] Backups are configured for database
- [ ] Cost alerts are set up

---

## Rollback Procedure

If something goes wrong, rollback to previous version:

```bash
# List previous revisions
gcloud run revisions list --service=cyperf-backend --region=$REGION

# Get previous revision name
export PREVIOUS_REVISION="cyperf-backend-00001-abc"

# Redirect traffic to previous revision
gcloud run services update-traffic cyperf-backend \
  --to-revisions=${PREVIOUS_REVISION}=100 \
  --region=$REGION

# Verify rollback
gcloud run services describe cyperf-backend --region=$REGION
```

---

## Advanced Configurations

### Custom Domain with SSL

```bash
# Map custom domain
gcloud beta run domain-mappings create \
  --service=cyperf-frontend \
  --domain=cyperf.yourdomain.com \
  --region=$REGION

# Update DNS CNAME record in your domain registrar:
# cyperf.yourdomain.com → ghs.googlehosted.com

# Verify certificate is issued
gcloud beta run domain-mappings describe cyperf.yourdomain.com \
  --region=$REGION
```

### Automated Backups

```bash
# Enable automated backups for Cloud SQL
gcloud sql backups create \
  --instance=cyperf-db \
  --description="Manual backup"

# Set automated backup window
gcloud sql instances patch cyperf-db \
  --backup-start-time=03:00 \
  --enable-bin-log

# List backups
gcloud sql backups list --instance=cyperf-db
```

### CI/CD Deployment Pipeline

```bash
# Create Cloud Build configuration
cat > cloudbuild.yaml << 'EOF'
steps:
  # Build backend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/cyperf-backend:$COMMIT_SHA', 'backend/']

  # Push backend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/cyperf-backend:$COMMIT_SHA']

  # Deploy backend
  - name: 'gcr.io/cloud-builders/gke-deploy'
    args: ['run', '--service=cyperf-backend', '--region=us-central1']

  # Build frontend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/cyperf-frontend:$COMMIT_SHA', 'frontend/']

  # Push frontend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/cyperf-frontend:$COMMIT_SHA']

  # Deploy frontend
  - name: 'gcr.io/cloud-builders/gke-deploy'
    args: ['run', '--service=cyperf-frontend', '--region=us-central1']

images:
  - 'gcr.io/$PROJECT_ID/cyperf-backend:$COMMIT_SHA'
  - 'gcr.io/$PROJECT_ID/cyperf-frontend:$COMMIT_SHA'
EOF

# Trigger build
gcloud builds submit --config=cloudbuild.yaml
```

---

## Quick Deploy Script

Save this as `deploy.sh`:

```bash
#!/bin/bash
set -e

PROJECT_ID="cyperf-buddy-prod"
REGION="us-central1"
IMAGE_REGISTRY="gcr.io/${PROJECT_ID}"

echo "=== CyperfBuddy Cloud Run Deployment ==="

# Build and push images
echo "Building and pushing Docker images..."
docker build -t ${IMAGE_REGISTRY}/cyperf-backend:latest backend/
docker push ${IMAGE_REGISTRY}/cyperf-backend:latest

docker build -t ${IMAGE_REGISTRY}/cyperf-frontend:latest frontend/
docker push ${IMAGE_REGISTRY}/cyperf-frontend:latest

# Deploy services
echo "Deploying backend..."
gcloud run deploy cyperf-backend \
  --image=${IMAGE_REGISTRY}/cyperf-backend:latest \
  --region=$REGION \
  --platform=managed \
  --service-account=cyperf-app@${PROJECT_ID}.iam.gserviceaccount.com \
  --vpc-connector=cyperf-connector \
  --vpc-egress=private-ranges-only \
  --memory=512Mi --cpu=1 --timeout=3600 --max-instances=10

echo "Deploying frontend..."
BACKEND_URL=$(gcloud run services describe cyperf-backend \
  --region=$REGION \
  --format='value(status.url)')

gcloud run deploy cyperf-frontend \
  --image=${IMAGE_REGISTRY}/cyperf-frontend:latest \
  --region=$REGION \
  --platform=managed \
  --service-account=cyperf-app@${PROJECT_ID}.iam.gserviceaccount.com \
  --memory=256Mi --cpu=1 --timeout=60 --max-instances=10 \
  --allow-unauthenticated \
  --set-env-vars="VITE_API_URL=${BACKEND_URL}"

# Get URLs
FRONTEND_URL=$(gcloud run services describe cyperf-frontend \
  --region=$REGION \
  --format='value(status.url)')

echo ""
echo "=== Deployment Complete! ==="
echo "Frontend:  ${FRONTEND_URL}"
echo "Backend:   ${BACKEND_URL}"
echo ""
echo "Next steps:"
echo "1. Visit ${FRONTEND_URL}"
echo "2. Configure Keysight endpoint in settings"
echo "3. Trigger a sync"
echo "4. Monitor logs: gcloud run logs read cyperf-backend --region=$REGION --follow"
```

---

## Support & Resources

- **GCP Documentation:** https://cloud.google.com/run/docs
- **Cloud SQL Guide:** https://cloud.google.com/sql/docs
- **Cloud Memorystore:** https://cloud.google.com/memorystore/docs
- **Cloud Run Pricing:** https://cloud.google.com/run/pricing
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment/
- **React Production Build:** https://vitejs.dev/guide/build.html

---

## Version History

| Date | Changes |
|------|---------|
| 2026-02-27 | Initial deployment guide created |

---

**Document Status:** ✅ Complete & Production-Ready

Last updated: 2026-02-27
For updates, see: `/Users/ashwin.joshi/claudeExp/DEPLOYMENT_GUIDE.md`
