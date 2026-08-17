#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# SideQuest Frontend Cloud Run Deployment Script
# Google DevJam 2026 - Agent X Smart City
# ==============================================================================

PROJECT_ID="${GCP_PROJECT_ID:-devjam26aug17tpe-1290}"
REGION="${GCP_REGION:-asia-east1}"
SERVICE_NAME="${SERVICE_NAME:-sidequest-demo}"
REPO_NAME="${REPO_NAME:-sidequest}"
IMAGE_NAME="${IMAGE_NAME:-frontend}"

echo "========================================================"
echo "🚀 Deploying SideQuest Frontend to Google Cloud Run..."
echo "========================================================"
echo "📌 Project ID : ${PROJECT_ID}"
echo "📌 Region     : ${REGION}"
echo "📌 Service    : ${SERVICE_NAME}"

# Step 1: Ensure Artifact Registry repository exists
if ! gcloud artifacts repositories describe "${REPO_NAME}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating Artifact Registry repository '${REPO_NAME}' in ${REGION}..."
  gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="SideQuest Docker Repository" \
    --project="${PROJECT_ID}"
fi

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest"

# Dynamically fetch Browser Key from GCP project if not provided in environment
if [ -z "${VITE_GOOGLE_MAPS_API_KEY:-}" ]; then
  MAPS_API_KEY=$(gcloud services api-keys get-key-string projects/917216410511/locations/global/keys/cf0642bd-628b-4876-ba5c-f1ded5ce9dad --format='value(keyString)' 2>/dev/null || echo "")
else
  MAPS_API_KEY="${VITE_GOOGLE_MAPS_API_KEY}"
fi

# Step 2: Build Container via Cloud Build
echo "🏗️ Building Frontend Docker container via Cloud Build with GCP project configuration..."
gcloud builds submit . \
  --config=cloudbuild.yaml \
  --substitutions="_REGION=${REGION},_REPOSITORY=${REPO_NAME},_MAPS_API_KEY=${MAPS_API_KEY},_API_BASE_URL=/api/v1,_EVENT_SOURCE=api,_AGENT_SOURCE=agent" \
  --project="${PROJECT_ID}"

# Step 3: Deploy to Cloud Run
echo "🚀 Deploying Frontend to Google Cloud Run..."
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
  --project="${PROJECT_ID}"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform=managed --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')

echo "========================================================"
echo "✅ Frontend Deployment Successful!"
echo "🌐 App URL: ${SERVICE_URL}"
echo "========================================================"
