# Environment Variables Configuration

This document lists the environment variables needed for each deployment environment. These variables should be set in Cloud Run for automated deployments.

## Why Environment Variables?

Firebase client-side credentials (API keys, auth domains, etc.) are not sensitive because they're already exposed in the browser. However, GitHub flags them as potential security issues. Using environment variables keeps these values out of Git while maintaining proper configuration.

## How It Works

[server.py](server.py#L14-L96) uses a try/except pattern:
1. **Try** to import from `config.py` (for local development)
2. **Except** falls back to environment variables (for Cloud Run deployment)

The `ENVIRONMENT` variable controls which configuration section is used:
- `ENVIRONMENT=development` → Development config
- `ENVIRONMENT=testing` → Testing config  
- `ENVIRONMENT=production` → Production config

## Development Environment (bravo-dev-465400)

Set these in Cloud Run service `bravo-aac-api`:

```bash
ENVIRONMENT=development
GCP_PROJECT_ID=bravo-dev-465400

# Firebase Configuration
FIREBASE_API_KEY_DEV=AIzaSyBN3usyIJ25HDEoOgHIU2w71K5iUXB2ANk
FIREBASE_AUTH_DOMAIN_DEV=bravo-dev-465400.firebaseapp.com
FIREBASE_PROJECT_ID_DEV=bravo-dev-465400
FIREBASE_STORAGE_BUCKET_DEV=bravo-dev-465400.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID_DEV=894197055102
FIREBASE_APP_ID_DEV=1:894197055102:web:d71bf54b2166ca8aba222f
FIREBASE_MEASUREMENT_ID_DEV=G-NQKM7HSYHZ

# Optional overrides
DOMAIN=dev.talkwithbravo.com
DEBUG=true
LOG_LEVEL=DEBUG
SERVICE_ACCOUNT_KEY_PATH=/keys/service-account.json
```

## Testing Environment (bravo-test-465400)

Set these in Cloud Run service `bravo-aac-api`:

```bash
ENVIRONMENT=testing
GCP_PROJECT_ID=bravo-test-465400

# Firebase Configuration
FIREBASE_API_KEY_TEST=AIzaSyDYNF8XUPJoY6vPtYhxJ7Z9J8Ue5S3K4E8
FIREBASE_AUTH_DOMAIN_TEST=bravo-test-465400.firebaseapp.com
FIREBASE_PROJECT_ID_TEST=bravo-test-465400
FIREBASE_STORAGE_BUCKET_TEST=bravo-test-465400.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID_TEST=22852552488
FIREBASE_APP_ID_TEST=1:22852552488:web:abc123def456

# Optional overrides
DOMAIN=test.talkwithbravo.com
DEBUG=false
LOG_LEVEL=INFO
SERVICE_ACCOUNT_KEY_PATH=/keys/bravo-test-service-account.json
```

## Production Environment (bravo-prod-465323)

Set these in Cloud Run service `bravo-aac-api`:

```bash
ENVIRONMENT=production
GCP_PROJECT_ID=bravo-prod-465323

# Firebase Configuration
FIREBASE_API_KEY_PROD=<your-prod-api-key>
FIREBASE_AUTH_DOMAIN_PROD=bravo-prod-465323.firebaseapp.com
FIREBASE_PROJECT_ID_PROD=bravo-prod-465323
FIREBASE_STORAGE_BUCKET_PROD=bravo-prod-465323.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID_PROD=<your-prod-sender-id>
FIREBASE_APP_ID_PROD=<your-prod-app-id>

# Optional overrides
DOMAIN=app.talkwithbravo.com
DEBUG=false
LOG_LEVEL=WARNING
SERVICE_ACCOUNT_KEY_PATH=/keys/bravo-prod-service-account.json
```

## Setting Environment Variables in Cloud Run

### Via Cloud Build (Automated)

The [cloudbuild.yaml](cloudbuild.yaml#L40-L46) already sets `ENVIRONMENT` via the `--update-env-vars` flag:

```yaml
- name: 'gcr.io/google.com/cloudsdkinstaller/google-cloud-cli'
  args:
    - gcloud
    - run
    - deploy
    - $_SERVICE_NAME
    - --image=gcr.io/$PROJECT_ID/$_SERVICE_NAME:$COMMIT_SHA
    - --region=$_REGION
    - --platform=managed
    - --allow-unauthenticated
    - --update-env-vars=ENVIRONMENT=$_ENV_NAME,GCP_PROJECT_ID=$PROJECT_ID
    - --set-secrets=GOOGLE_API_KEY=bravo-google-api-key:latest
```

The `$_ENV_NAME` substitution variable is set per trigger:
- **Dev trigger**: `_ENV_NAME=development`
- **Test trigger**: `_ENV_NAME=testing`
- **Prod trigger**: `_ENV_NAME=production`

### Via GCP Console (Manual)

1. Go to Cloud Run → Select service → Edit & Deploy New Revision
2. Under **Variables & Secrets** → **Environment variables**
3. Add the variables listed above for your environment
4. Deploy the new revision

### Via gcloud CLI

```bash
# Development
gcloud run services update bravo-aac-api \
  --region=us-central1 \
  --update-env-vars=ENVIRONMENT=development,GCP_PROJECT_ID=bravo-dev-465400,FIREBASE_API_KEY_DEV=AIzaSyBN3usyIJ25HDEoOgHIU2w71K5iUXB2ANk \
  --project=bravo-dev-465400

# Testing
gcloud run services update bravo-aac-api \
  --region=us-central1 \
  --update-env-vars=ENVIRONMENT=testing,GCP_PROJECT_ID=bravo-test-465400,FIREBASE_API_KEY_TEST=AIzaSyDYNF8XUPJoY6vPtYhxJ7Z9J8Ue5S3K4E8 \
  --project=bravo-test-465400
```

## Local Development

For local development, create a `config.py` file (gitignored) with your Firebase credentials. See the existing `config.py` as a template. The file will be ignored by Git but available for local testing.

Alternatively, create a `.env` file (also gitignored) with the environment variables above, and they'll be loaded by `load_dotenv()` in [server.py](server.py#L6).

## Verification

After deploying, check the logs to confirm the correct environment loaded:

```bash
gcloud run services logs read bravo-aac-api --region=us-central1 --project=bravo-dev-465400
```

Look for log lines like:
```
🚀 Bravo AAC Application - Development Environment
   Environment: development
   Domain: dev.talkwithbravo.com
   Debug Mode: True
```

Or check the `/health` endpoint:
```bash
curl https://dev.talkwithbravo.com/health
```

Should return:
```json
{
  "environment": "development",
  "environment_name": "Development",
  "domain": "dev.talkwithbravo.com",
  "gcp_project": "bravo-dev-465400",
  "status": "healthy"
}
```

## Current Status

✅ **cloudbuild.yaml** already sets `ENVIRONMENT` and `GCP_PROJECT_ID` automatically via substitution variables  
✅ **server.py** has complete fallback logic for all environments  
✅ **Firebase credentials** can now be passed via environment variables  
⚠️ **Additional Firebase env vars** need to be added to Cloud Run services manually (or via updated cloudbuild.yaml)

## Next Steps

**Option 1: Keep It Simple (Recommended)**
- Cloud Run deployments will use server.py's hardcoded fallback values in the except block
- This works because Firebase client credentials are not sensitive
- No changes needed to Cloud Build or Cloud Run

**Option 2: Full Environment Variable Configuration**
- Add all Firebase env vars to each Cloud Run service via GCP Console or gcloud CLI
- Update cloudbuild.yaml to pass additional env vars if desired
- More secure and explicit but requires more configuration

For now, Option 1 is sufficient since the fallback values in server.py match your actual Firebase projects.
