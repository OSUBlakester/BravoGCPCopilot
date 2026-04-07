#!/bin/bash
# Restart local development server

set -euo pipefail

PROJECT_ID="bravo-dev-465400"

get_secret_value() {
  local secret_name="$1"
  local value=""

  value="$(gcloud secrets versions access latest --secret="$secret_name" --project="$PROJECT_ID" 2>/dev/null || true)"
  if [ -n "$value" ]; then
    printf '%s' "$value"
    return 0
  fi

  local adc_token=""
  adc_token="$(gcloud auth application-default print-access-token 2>/dev/null || true)"
  if [ -z "$adc_token" ]; then
    return 0
  fi

  value="$(curl -s -H "Authorization: Bearer $adc_token" \
    "https://secretmanager.googleapis.com/v1/projects/$PROJECT_ID/secrets/$secret_name/versions/latest:access" \
    | python3 -c "import sys,json,base64; raw=sys.stdin.read().strip();\
import json as _j;\
data=_j.loads(raw) if raw else {};\
payload=(data.get('payload') or {}).get('data');\
print(base64.b64decode(payload).decode() if payload else '')" 2>/dev/null || true)"

  printf '%s' "$value"
}

# Load local .env values if present (do not overwrite already-exported shell vars)
if [ -f .env ]; then
  set -a
  source .env || true
  set +a
fi

echo "🛑 Stopping existing container..."
docker rm -f bravo-dev 2>/dev/null || true

echo "🔨 Building image..."
if [ "${FORCE_CLEAN_DOCKER_BUILD:-false}" = "true" ]; then
  echo "🧼 FORCE_CLEAN_DOCKER_BUILD=true → building with --no-cache"
  docker build --no-cache -t bravo-local -f Dockerfile.cloudrun .
else
  docker build -t bravo-local -f Dockerfile.cloudrun .
fi

# Load API key from Secret Manager if not already set
GOOGLE_API_KEY="${GOOGLE_API_KEY:-}"
if [ -z "$GOOGLE_API_KEY" ]; then
  echo "🔑 Fetching API key from Secret Manager..."
  GOOGLE_API_KEY="$(get_secret_value "bravo-google-api-key")"
  if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  WARNING: Could not retrieve GOOGLE_API_KEY from Secret Manager!"
    echo "   Run: gcloud secrets versions access latest --secret=\"bravo-google-api-key\" --project=$PROJECT_ID"
  else
    echo "✅ API key retrieved from Secret Manager"
  fi
fi

# Fetch email/OAuth secrets from Secret Manager
echo "🔑 Fetching email/OAuth secrets from Secret Manager..."
GOOGLE_OAUTH_CLIENT_ID="${GOOGLE_OAUTH_CLIENT_ID:-}"
GOOGLE_OAUTH_CLIENT_SECRET="${GOOGLE_OAUTH_CLIENT_SECRET:-}"
EMAIL_OAUTH_STATE_SECRET="${EMAIL_OAUTH_STATE_SECRET:-}"
EMAIL_TOKEN_ENCRYPTION_KEY="${EMAIL_TOKEN_ENCRYPTION_KEY:-}"

[ -z "$GOOGLE_OAUTH_CLIENT_ID" ] && GOOGLE_OAUTH_CLIENT_ID="$(get_secret_value "GOOGLE_OAUTH_CLIENT_ID")"
[ -z "$GOOGLE_OAUTH_CLIENT_SECRET" ] && GOOGLE_OAUTH_CLIENT_SECRET="$(get_secret_value "GOOGLE_OAUTH_CLIENT_SECRET")"
[ -z "$EMAIL_OAUTH_STATE_SECRET" ] && EMAIL_OAUTH_STATE_SECRET="$(get_secret_value "EMAIL_OAUTH_STATE_SECRET")"
[ -z "$EMAIL_TOKEN_ENCRYPTION_KEY" ] && EMAIL_TOKEN_ENCRYPTION_KEY="$(get_secret_value "EMAIL_TOKEN_ENCRYPTION_KEY")"

if [ -z "$GOOGLE_OAUTH_CLIENT_ID" ] || [ -z "$GOOGLE_OAUTH_CLIENT_SECRET" ]; then
  echo "⚠️  WARNING: Could not retrieve Google OAuth secrets. Email feature will be disabled."
  echo "   If using Secret Manager, re-auth first: gcloud auth login && gcloud auth application-default login"
  EMAIL_FEATURE_ENABLED_VAL=false
else
  echo "✅ Email/OAuth secrets retrieved"
  EMAIL_FEATURE_ENABLED_VAL=true
fi

echo "🚀 Starting container..."
docker run -d --name bravo-dev -p 8000:8080 \
  -e ENVIRONMENT=development \
  -e EMAIL_FEATURE_ENABLED="$EMAIL_FEATURE_ENABLED_VAL" \
  -e EMAIL_OAUTH_REDIRECT_URI=http://localhost:8000/api/email/oauth/callback \
  -e GOOGLE_OAUTH_CLIENT_ID="$GOOGLE_OAUTH_CLIENT_ID" \
  -e GOOGLE_OAUTH_CLIENT_SECRET="$GOOGLE_OAUTH_CLIENT_SECRET" \
  -e EMAIL_OAUTH_STATE_SECRET="$EMAIL_OAUTH_STATE_SECRET" \
  -e EMAIL_TOKEN_ENCRYPTION_KEY="$EMAIL_TOKEN_ENCRYPTION_KEY" \
  -e GCP_PROJECT_ID="$PROJECT_ID" \
  -e GOOGLE_CLOUD_PROJECT="$PROJECT_ID" \
  -e GOOGLE_CLOUD_QUOTA_PROJECT="$PROJECT_ID" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  -e GEMINI_PRIMARY_MODEL=gemini-2.5-flash-lite \
  -e GEMINI_FALLBACK_MODEL=gemini-2.0-flash-lite \
  -e K_SERVICE=bravo-aac-api-dev \
  -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
  bravo-local

echo "⏳ Waiting for server to start..."
sleep 3

if ! docker ps --filter "name=^bravo-dev$" --filter "status=running" --format '{{.Names}}' | grep -q '^bravo-dev$'; then
  echo "❌ Container failed to stay running"
  echo "📋 Last logs:"
  docker logs bravo-dev 2>&1 | tail -50
  exit 1
fi

echo "✅ Server logs:"
docker logs bravo-dev 2>&1 | tail -10

echo ""
echo "🌐 Server running at http://localhost:8000"
echo "📋 View logs: docker logs -f bravo-dev"
echo "🛑 Stop server: docker stop bravo-dev"
