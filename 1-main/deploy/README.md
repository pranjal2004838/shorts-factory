# Shorts Factory — GCP Deployment (Week 4)

Serverless deployment of the backend on Cloud Run, with Cloud Storage for
uploads and outputs.

## One-time setup

```bash
export PROJECT_ID=your-gcp-project
export REGION=us-central1

# Buckets
gsutil mb -l $REGION gs://$PROJECT_ID-sf-raw
gsutil mb -l $REGION gs://$PROJECT_ID-sf-output
# Auto-expire raw uploads after 24h
gsutil lifecycle set deploy/gcs-lifecycle.json gs://$PROJECT_ID-sf-raw

# Secrets (read by the Cloud Run service)
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
printf '%s' "$GIPHY_API_KEY"  | gcloud secrets create giphy-api-key  --data-file=-
```

## Build & deploy

```bash
gcloud builds submit --config deploy/cloudbuild.yaml \
  --substitutions=_REGION=$REGION
```

The service spec (`cloudrun-service.yaml`) requests 4 vCPU / 8Gi and
disables CPU throttling so FFmpeg + Whisper get full cores during a render.
Scale-to-zero keeps idle cost at ₹0.

## Frontend

Deploy `frontend/` to any Next.js host (Vercel, Cloud Run, etc.) and set
`NEXT_PUBLIC_API_URL` to the deployed Cloud Run URL.
