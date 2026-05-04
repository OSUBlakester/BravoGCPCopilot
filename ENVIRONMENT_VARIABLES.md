# Environment Variables Configuration

This document lists the environment variables needed for each deployment environment. Set these in your Cloud Run service, or in a local `.env` file for development.

## How It Works

`server.py` uses a try/except pattern:
1. **Try** to import from `config.py` (for local development)
2. **Except** falls back to environment variables (for Cloud Run deployment)

The `ENVIRONMENT` variable controls which configuration section is used:
- `ENVIRONMENT=development` → Development config
- `ENVIRONMENT=testing` → Testing config
- `ENVIRONMENT=production` → Production config

## Required Variables

### Core

```bash
ENVIRONMENT=development          # development | testing | production
GCP_PROJECT_ID=<your-project-id>
```

### Gemini LLM (required — no defaults)

```bash
GEMINI_PRIMARY_MODEL=gemini-2.5-flash-lite
GEMINI_FALLBACK_MODEL=gemini-1.5-flash-latest
GEMINI_FAST_WORDS_MODEL=gemini-2.5-flash-lite   # optional, defaults to primary
```

### Firebase (suffix matches ENVIRONMENT value)

```bash
# For ENVIRONMENT=development, use _DEV suffix:
FIREBASE_API_KEY_DEV=<your-firebase-api-key>
FIREBASE_AUTH_DOMAIN_DEV=<your-project-id>.firebaseapp.com
FIREBASE_PROJECT_ID_DEV=<your-project-id>
FIREBASE_STORAGE_BUCKET_DEV=<your-project-id>.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID_DEV=<your-sender-id>
FIREBASE_APP_ID_DEV=<your-app-id>
FIREBASE_MEASUREMENT_ID_DEV=<your-measurement-id>   # optional

# For ENVIRONMENT=testing, use _TEST suffix:
FIREBASE_API_KEY_TEST=<your-firebase-api-key>
# ... same pattern with _TEST suffix

# For ENVIRONMENT=production, use _PROD suffix:
FIREBASE_API_KEY_PROD=<your-firebase-api-key>
# ... same pattern with _PROD suffix
```

Your Firebase credentials are found in the Firebase console under **Project Settings → General → Your apps → SDK setup and configuration**.

### GCP Service Account

```bash
SERVICE_ACCOUNT_KEY_PATH=/keys/service-account.json
```

For Cloud Run, mount the service account key as a secret or use Workload Identity instead.

### Google API Key (Gemini)

Store this in GCP Secret Manager and reference it in `cloudbuild.yaml`:

```bash
GOOGLE_API_KEY=<your-gemini-api-key>
```

### Optional

```bash
DOMAIN=<your-app-domain>
DEBUG=true                  # true | false
LOG_LEVEL=DEBUG             # DEBUG | INFO | WARNING | ERROR
```

### Email Feature (only required if EMAIL_FEATURE_ENABLED=true)

```bash
EMAIL_FEATURE_ENABLED=true
GOOGLE_OAUTH_CLIENT_ID=<your-oauth-client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<your-oauth-client-secret>
EMAIL_OAUTH_STATE_SECRET=<random-secret-string>
EMAIL_TOKEN_ENCRYPTION_KEY=<fernet-key>    # generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Setting Variables in Cloud Run

### Via GCP Console

1. Cloud Run → Select service → **Edit & Deploy New Revision**
2. **Variables & Secrets** → **Environment variables**
3. Add variables and deploy

### Via gcloud CLI

```bash
gcloud run services update <your-service-name> \
  --region=us-central1 \
  --update-env-vars=ENVIRONMENT=development,GCP_PROJECT_ID=<your-project-id> \
  --project=<your-project-id>
```

### Via Cloud Build (Automated)

`cloudbuild.yaml` sets `ENVIRONMENT` and `GCP_PROJECT_ID` automatically via substitution variables. Sensitive values (Gemini API key) are injected from Secret Manager via `--set-secrets`.

## Local Development

1. Copy `config.py.template` to `config.py` and fill in your Firebase credentials, **or**
2. Copy `.env.template` to `.env` and set the environment variables above

Both files are gitignored and will never be committed.

## Verification

After deploying, check the `/health` endpoint:

```bash
curl https://<your-domain>/health
```

Or check Cloud Run logs:

```bash
gcloud run services logs read <your-service-name> --region=us-central1 --project=<your-project-id>
```
