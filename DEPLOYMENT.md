# Bravo AAC Multi-Environment Setup

This document explains how to set up and deploy the Bravo AAC application across multiple environments.

## Environment Structure

- **Development** (`dev`): `dev.talkwithbravo.com` - For active development
- **Testing** (`test`): `test.talkwithbravo.com` - For UAT and pre-production testing  
- **Production** (`prod`): `talkwithbravo.com` - For end users

## GCP Projects

- `bravo-dev` - Development environment
- `bravo-test` - Testing environment
- `bravo-prod` - Production environment

## Setup Steps

### 1. Service Accounts

For each environment, create a service account with these roles:
- **Cloud Datastore User**: Allows reading/writing to Firestore.
- **Service Account User**: Allows the service account to be used by other services.
- **Cloud Run Invoker**: (Optional, if you need to call it from other services).
- **Firebase Admin**: A broader role that also works if you prefer simplicity over least-privilege.


Download the JSON keys and place them at:
- `/keys/bravo-dev-service-account.json`
- `/keys/bravo-test-service-account.json`
- `/keys/bravo-prod-service-account.json`

### 1.1 Secret Management (for API Keys)

To securely manage secrets like the `GOOGLE_API_KEY`, use Google Cloud Secret Manager.

1.  **Create the secret** in each project:
    ```bash
    gcloud secrets create bravo-google-api-key --replication-policy="automatic" --project=[your-project-id]
    echo -n "YOUR_API_KEY_VALUE" | gcloud secrets versions add bravo-google-api-key --data-file=- --project=[your-project-id]
    ```
2.  **Grant access** to the Cloud Run service account:
    The service account (e.g., `[PROJECT_NUMBER]-compute@developer.gserviceaccount.com`) needs the `Secret Manager Secret Accessor` role.

### 2. Firestore Setup

For each project:
1. Go to Firestore in GCP Console
2. Create database in Native mode
3. Choose your preferred region
4. Set up security rules (start with test mode, tighten later)

### 3. Firebase Setup

For each project:
1. Go to Firebase Console
2. Add Firebase to your GCP project
3. Enable Authentication
4. Download config files and place at:
   - `/keys/bravo-dev-firebase-key.json`
   - `/keys/bravo-test-firebase-key.json`
   - `/keys/bravo-prod-firebase-key.json`

### 4. Domain Setup

Point your domains to the Cloud Run services:
- `dev.talkwithbravo.com` → Development Cloud Run URL
- `test.talkwithbravo.com` → Testing Cloud Run URL  
- `talkwithbravo.com` → Production Cloud Run URL

## Deployment

### Quick Deploy
```bash
# Deploy to development
./deploy.sh dev

# Deploy to testing  
./deploy.sh test

# Deploy to production
./deploy.sh prod
```

### Manual Deploy
```bash
# Set environment variable
export ENVIRONMENT=development  # or testing, production

# Build and deploy
gcloud run deploy bravo-aac-api \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars ENVIRONMENT=$ENVIRONMENT
```

## Environment Variables

The application automatically configures itself based on the `ENVIRONMENT` variable:

- `ENVIRONMENT=development` → Uses bravo-dev project
- `ENVIRONMENT=testing` → Uses bravo-test project  
- `ENVIRONMENT=production` → Uses bravo-prod project

## Health Checks

Each environment exposes a health endpoint:
- `GET /health` - Shows environment info and service status

Example response:
```json
{
  "status": "healthy",
  "environment": "development", 
  "environment_name": "Development",
  "domain": "dev.talkwithbravo.com",
  "gcp_project": "bravo-dev",
  "debug_mode": true,
  "services": {
    "firebase": true,
    "firestore": true,
    "sentence_transformer": true,
    "primary_llm": true,
    "fallback_llm": true,
    "tts": true
  }
}
```

## Testing Flow

1. **Development**: Make changes, test on `dev.talkwithbravo.com`
2. **Testing**: Deploy to testing, run UAT on `test.talkwithbravo.com`  
3. **Production**: Deploy to production, monitor `talkwithbravo.com`

## Troubleshooting

### Check service status
```bash
# Check if service is running
curl https://[your-domain]/health

# View logs
gcloud logs read --project=[project-id] --limit=50
```

### Common Issues

1. **Service account keys not found**: Ensure keys are in `/keys/` directory
2. **CORS errors**: Check `allowed_origins` in config for your domain
3. **Firestore errors**: Verify project ID matches in config
4. **Authentication errors**: Check Firebase config file path

## Security Notes

- Production uses minimal CORS origins
- Debug mode is disabled in testing/production
- Service account keys should be managed securely
- Consider using secret management for production
