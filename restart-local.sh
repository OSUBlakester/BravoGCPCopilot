#!/bin/bash
# Restart local development server

echo "🛑 Stopping existing container..."
docker rm -f bravo-dev 2>/dev/null || true

echo "🔨 Building image..."
docker build --no-cache -t bravo-local -f Dockerfile.cloudrun .

echo "🚀 Starting container..."
docker run -d --name bravo-dev -p 8080:8080 \
  -e ENVIRONMENT=development \
  -e GCP_PROJECT_ID=bravo-dev-465400 \
  -e GOOGLE_CLOUD_PROJECT=bravo-dev-465400 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
  -e GOOGLE_API_KEY=AIzaSyBBvZ7rq2w1bUBzQb4FIjXm_r9zP9c8rE4 \
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
echo "🌐 Server running at http://localhost:8080"
echo "📋 View logs: docker logs -f bravo-dev"
echo "🛑 Stop server: docker stop bravo-dev"
