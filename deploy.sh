#!/bin/bash

# Deployment script for Bravo AAC Application
# Usage: ./deploy.sh [environment]
# Environments: dev, testing, prod

set -e

# Configuration
ENVIRONMENTS=("dev" "test" "prod")
SERVICE_NAME="bravo-aac-api"
REGION="us-central1"  # Change to your preferred region

# Parse arguments
ENVIRONMENT=${1:-"dev"}

# Validate environment
if [[ ! " ${ENVIRONMENTS[@]} " =~ " ${ENVIRONMENT} " ]]; then
    echo "❌ Invalid environment: $ENVIRONMENT"
    echo "Valid environments: ${ENVIRONMENTS[*]}"
    exit 1
fi

# Map environment to Project ID and full name
case $ENVIRONMENT in
    "dev")
        PROJECT_ID="bravo-dev-465400"
        CUSTOM_DOMAIN="dev.talkwithbravo.com"
        ENV_NAME="development"
        ;;
    "test")
        PROJECT_ID="bravo-test-465400"
        CUSTOM_DOMAIN="test.talkwithbravo.com"
        ENV_NAME="testing"
        ;;
    "prod")
        PROJECT_ID="bravo-prod-465323"
        CUSTOM_DOMAIN="app.talkwithbravo.com"   
        ENV_NAME="production"
        ;;
esac

if [[ -z "$PROJECT_ID" ]]; then
    echo "❌ No project ID found for environment: $ENVIRONMENT"
    exit 1
fi

echo "🚀 Deploying to $ENVIRONMENT environment"
echo "   Project: $PROJECT_ID"
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo ""

# Set the active project
echo "📋 Setting active GCP project..."
gcloud config set project $PROJECT_ID


# Build the Docker image using Cloud Build configuration
echo "🏗️ Building Docker image with cloudbuild.yaml..."
IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"

gcloud builds submit . --config=cloudbuild.yaml --substitutions=_SERVICE_NAME=$SERVICE_NAME,_PROJECT_ID=$PROJECT_ID --region="$REGION"

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
echo "ℹ️ Note: This deployment will preserve existing environment variables"
echo "ℹ️ Updating ENVIRONMENT, GCP_PROJECT_ID, and EMAIL_FEATURE_ENABLED"
EMAIL_FEATURE_ENABLED="false"
gcloud run deploy $SERVICE_NAME \
    --image "$IMAGE_TAG" \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --update-env-vars=ENVIRONMENT=$ENV_NAME,GCP_PROJECT_ID=$PROJECT_ID,EMAIL_FEATURE_ENABLED=$EMAIL_FEATURE_ENABLED \
    --set-secrets=GOOGLE_API_KEY=bravo-google-api-key:latest \
    --memory 2Gi \
    --cpu 1 \
    --max-instances 10 \
    --timeout 300 \
    --port 8080

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')

echo ""
echo "✅ Deployment successful!"
echo "🌐 Service URL: $SERVICE_URL"
echo "🔍 Health check: $SERVICE_URL/health"
echo ""

# Test the health endpoint
echo "🩺 Testing health endpoint..."
HEALTHY=false
MAX_RETRIES=5
RETRY_DELAY=5
for i in $(seq 1 $MAX_RETRIES); do
    if curl -s -f "$SERVICE_URL/health" > /dev/null; then
        echo "✅ Health check passed!"
        HEALTHY=true
        break
    else
        echo "⚠️ Health check attempt $i failed - service may still be starting up. Retrying in $RETRY_DELAY seconds..."
        sleep $RETRY_DELAY
    fi
done

if [ "$HEALTHY" != "true" ]; then echo "❌ Health check failed after $MAX_RETRIES attempts."; fi

echo ""
echo "🎉 Deployment to $ENVIRONMENT environment complete!"

# Show next steps
echo ""
echo "📋 Next steps:"
case $ENVIRONMENT in
    *)
        echo "   • Ensure your custom domain ($CUSTOM_DOMAIN) is correctly mapped to the Cloud Run service."
        echo "   • Test your changes at: https://$CUSTOM_DOMAIN"
        echo "   • The direct service URL is: $SERVICE_URL"
        ;;
esac
