#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# SideQuest Cloud Run Deployment Script
# Google DevJam 2026 - Agent X Smart City
# ==============================================================================

echo "========================================================"
echo "🚀 Deploying SideQuest Backend to Google Cloud Run..."
echo "========================================================"

# Configuration defaults
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo "")}"
REGION="${GCP_REGION:-asia-east1}"
SERVICE_NAME="${SERVICE_NAME:-sidequest-backend}"
REPO_NAME="${REPO_NAME:-sidequest}"
IMAGE_NAME="${IMAGE_NAME:-backend}"
GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}"

if [ -z "$PROJECT_ID" ]; then
  echo "❌ Error: GCP_PROJECT_ID is not set and no active gcloud project found."
  echo "Please run: export GCP_PROJECT_ID='your-project-id' or gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo "📌 Project ID : ${PROJECT_ID}"
echo "📌 Region     : ${REGION}"
echo "📌 Service    : ${SERVICE_NAME}"

# Step 1: Enable required Google Cloud APIs
echo "🔧 Step 1/4: Enabling required GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  --project="${PROJECT_ID}"

# Step 2: Ensure Artifact Registry repository exists
echo "📦 Step 2/4: Ensuring Artifact Registry repository exists..."
if ! gcloud artifacts repositories describe "${REPO_NAME}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating Artifact Registry repository '${REPO_NAME}' in ${REGION}..."
  gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="SideQuest Docker Repository" \
    --project="${PROJECT_ID}"
else
  echo "Artifact Registry repository '${REPO_NAME}' already exists."
fi

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest"

# Step 3: Build Container via Cloud Build
echo "🏗️ Step 3/4: Building Docker container image via Cloud Build..."
gcloud builds submit . \
  --tag="${IMAGE_URI}" \
  --project="${PROJECT_ID}"

# Step 4: Deploy to Cloud Run
echo "🚀 Step 4/4: Deploying to Google Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE_URI}" \
  --platform=managed \
  --region="${REGION}" \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80 \
  --cpu=1 \
  --memory=512Mi \
  --set-env-vars="ENVIRONMENT=production,DEBUG=false,GCP_PROJECT_ID=${PROJECT_ID},GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}" \
  --project="${PROJECT_ID}"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform=managed --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')

echo "========================================================"
echo "✅ Deployment Successful!"
echo "🌐 Service URL: ${SERVICE_URL}"
echo "📚 Swagger API Docs: ${SERVICE_URL}/docs"
echo "💓 Health Check: ${SERVICE_URL}/healthz"
echo "========================================================"
