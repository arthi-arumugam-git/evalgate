#!/bin/sh
# Deploy HelpDesk to Google Cloud Run (eligible for the +0.2 Google Cloud bonus).
# CI variables: GCP_PROJECT_ID, GCP_REGION (default asia-south1), GCP_SA_KEY (file var, roles/run.admin + artifactregistry.writer + iam.serviceAccountUser).
# Builds from source with Cloud Build, so no registry wiring is needed.
set -eu
SERVICE="${1:-helpdesk}"
REGION="${GCP_REGION:-asia-south1}"
gcloud auth activate-service-account --key-file="$GCP_SA_KEY"
gcloud config set project "$GCP_PROJECT_ID"
gcloud run deploy "$SERVICE" --source . --region "$REGION" --allow-unauthenticated \
  --min-instances 0 --max-instances 2 --memory 512Mi \
  --set-env-vars "EVALGATE_MOCK=${EVALGATE_MOCK:-1},APP_VERSION=${CI_COMMIT_SHORT_SHA:-manual}"
gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)'
