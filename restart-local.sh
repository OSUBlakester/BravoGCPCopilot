#!/bin/bash
# Restart local development server

echo "🛑 Stopping existing container..."
docker rm -f bravo-dev 2>/dev/null || true

echo "🔨 Building image..."
docker build --no-cache -t bravo-local -f Dockerfile.cloudrun .

# Load API key from Secret Manager if not already set
if [ -z "$GOOGLE_API_KEY" ]; then
  echo "🔑 Fetching API key from Secret Manager..."
  GOOGLE_API_KEY=$(gcloud secrets versions access latest --secret="bravo-google-api-key" --project=bravo-dev-465400 2>/dev/null)
  if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  WARNING: Could not retrieve GOOGLE_API_KEY from Secret Manager!"
    echo "   Run: gcloud secrets versions access latest --secret=\"bravo-google-api-key\" --project=bravo-dev-465400"
  else
    echo "✅ API key retrieved from Secret Manager"
  fi
fi

echo "🚀 Starting container..."
docker run -d --name bravo-dev -p 8000:8080 \
  -e ENVIRONMENT=development \
  -e GCP_PROJECT_ID=bravo-dev-465400 \
  -e GOOGLE_CLOUD_PROJECT=bravo-dev-465400 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  -e GEMINI_PRIMARY_MODEL=gemini-2.5-flash-lite \
  -e GEMINI_FALLBACK_MODEL=gemini-2.0-flash-lite \
  -e K_SERVICE=bravo-aac-api-dev \
  -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
  bravo-local

echo "⏳ Waiting for server to start..."
sleep 3

echo "✅ Server logs:"
docker logs bravo-dev 2>&1 | tail -10

echo ""
echo "🌐 Server running at http://localhost:8000"
echo "📋 View logs: docker logs -f bravo-dev"
echo "🛑 Stop server: docker stop bravo-dev"
