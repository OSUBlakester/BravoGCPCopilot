#!/bin/bash
#
# Local Development Script - Connect to Production Firestore for Testing
# ========================================================================
# 
# This script runs the local development server but connects it to the
# PRODUCTION Firestore/Firebase project to test with real user data.
#
# ⚠️  WARNING: This reads from production but does NOT write to it by default
# ⚠️  Any cache changes WILL be written to production Firestore
#
# Usage:
#   ./test-local-with-prod.sh
#

echo "🧪 Starting Local Development Server with Production Firestore Connection"
echo "=========================================================================="
echo ""
echo "⚠️  WARNING: Connecting to PRODUCTION data"
echo "   - Reads: FROM production Firestore (bravo-prod-465323)"
echo "   - Writes: TO production Firestore (including cache metadata)"
echo "   - Server: Running locally on http://localhost:8080"
echo ""
echo "This is safe for testing READ operations and cache optimization."
echo "Cache writes will update production cache metadata (designed for this)."
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Cancelled."
    exit 1
fi

# Set environment to development (local) but point to prod Firestore
export ENVIRONMENT=development
export GCP_PROJECT_ID=bravo-prod-465323

# Override service account path to use prod credentials
# You need to download the prod service account key and place it in your project
export SERVICE_ACCOUNT_KEY_PATH="./bravo-prod-service-account-key.json"

# Check if prod service account key exists
if [ ! -f "$SERVICE_ACCOUNT_KEY_PATH" ]; then
    echo "❌ ERROR: Production service account key not found"
    echo ""
    echo "To download the production service account key:"
    echo "1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts?project=bravo-prod-465323"
    echo "2. Find the service account used by your application"
    echo "3. Click Actions → Manage Keys → Add Key → Create New Key → JSON"
    echo "4. Save it as: bravo-prod-service-account-key.json in this directory"
    echo ""
    echo "⚠️  SECURITY: Add this file to .gitignore to prevent committing!"
    exit 1
fi

echo "✅ Production service account key found"
echo ""
echo "Starting server with configuration:"
echo "  - Environment: development (local mode)"
echo "  - GCP Project: bravo-prod-465323"
echo "  - Firestore: Production database"
echo "  - Service Account: $SERVICE_ACCOUNT_KEY_PATH"
echo "  - Server URL: http://localhost:8080"
echo ""
echo "📊 Testing Cache Optimization:"
echo "  - Monitor cache drift detection in logs"
echo "  - Check lazy invalidation triggers"
echo "  - Verify message counts in cache metadata"
echo ""

# Stop any existing container
echo "Stopping existing container..."
docker stop bravo-dev 2>/dev/null || true
docker rm bravo-dev 2>/dev/null || true

# Build and run
echo "Building Docker image..."
docker build -t bravo-dev -f Dockerfile.cloudrun .

echo ""
echo "Starting container..."
docker run -d \
  --name bravo-dev \
  -p 8080:8080 \
  -e ENVIRONMENT=development \
  -e GCP_PROJECT_ID=bravo-prod-465323 \
  -e SERVICE_ACCOUNT_KEY_PATH=/app/bravo-prod-service-account-key.json \
  -v "$(pwd)/bravo-prod-service-account-key.json:/app/bravo-prod-service-account-key.json:ro" \
  -v "$(pwd):/app" \
  bravo-dev

echo ""
echo "✅ Server starting..."
echo ""
echo "View logs with: docker logs -f bravo-dev"
echo "Stop server with: docker stop bravo-dev"
echo ""
echo "Access the application at: http://localhost:8080"
echo ""
echo "🔍 Look for these log messages to confirm cache drift detection:"
echo "   - '📊 Cache snapshot contains X messages'"
echo "   - '✅ Including Y new messages in delta'"
echo "   - '♻️ Cache drift (Z messages) exceeds threshold'"
echo ""
