#!/bin/bash
# Deploy PiCom Symbol System to Google Cloud Run

echo "🚀 Deploying PiCom Symbol System to Google Cloud Run"

# Set your project ID
PROJECT_ID="bravo-test-465400"  # or your production project
REGION="us-central1"
SERVICE_NAME="bravo-aac-api"

# Build and deploy
echo "📦 Building container..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --timeout 3600 \
  --set-env-vars ENVIRONMENT=testing \
  --max-instances 10

echo "✅ Deployment complete!"
echo "🌐 Your symbol system is now available at:"
gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)'