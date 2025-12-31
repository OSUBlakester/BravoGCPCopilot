## Summary

**Your Git-centric workflow is now active!** 🎉

The automated Cloud Build trigger is working correctly. Here's what happens:

1. You (or your collaborator) push code to `main` branch
2. Cloud Build automatically triggers
3. Builds Docker image from `Dockerfile.cloudrun`
4. Pushes to Container Registry
5. Deploys to `bravo-aac-api` service

**Important Notes:**
- ✅ Automated deployments update **code only** - they preserve existing service configuration
- ✅ Environment variables, secrets, memory, CPU settings are **NOT changed** by automated deployments
- ⚠️ **First deployment to a new environment MUST use `./deploy.sh`** to set all env vars and secrets
- ⚠️ **Configuration changes** (env vars, memory, secrets) should be done via `./deploy.sh` or GCP Console

## When to Use Each Method

### Use Automated Deployment (Git Push) For:
- Code changes (new features, bug fixes)
- UI updates
- Static file changes
- Database schema changes (code-side)
- Most day-to-day development

### Use Manual Deployment (`./deploy.sh`) For:
- **First-time setup** of a new environment
- Changing environment variables
- Updating secrets
- Changing memory/CPU allocation
- Changing service configuration (timeout, min instances, etc.)

## Current Status

✅ **Dev Environment** - Trigger configured and working
- Service: `bravo-aac-api`
- Project: `bravo-dev-465400`
- Custom Domain: https://dev.talkwithbravo.com
- Trigger: Watches `main` branch

⏸️ **Test Environment** - Not configured yet
⏸️ **Prod Environment** - Not configured yet

---

# Original Setup Instructions Below

This guide will help you set up automated deployments from GitHub to Google Cloud Platform.

## Overview

Once configured, the workflow will be:
1. Developer creates a feature branch
2. Makes changes and pushes to GitHub
3. Opens a Pull Request for review
4. After approval, merges to `main`
5. **Cloud Build automatically deploys to Cloud Run**

## One-Time Setup

### Step 1: Connect GitHub to Cloud Build

Run these commands to set up the Cloud Build trigger:

```bash
# Set your GCP project ID
export PROJECT_ID="your-gcp-project-id"

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com \
  cloudrun.googleapis.com \
  artifactregistry.googleapis.com \
  --project=$PROJECT_ID

# Give Cloud Build permission to deploy to Cloud Run
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Create Cloud Build trigger for main branch
gcloud builds triggers create github \
  --name="deploy-to-cloud-run" \
  --repo-name="BravoGCPCopilot" \
  --repo-owner="OSUBlakester" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --substitutions="_SERVICE_NAME=bravogcpcopilot,_REGION=us-central1" \
  --project=$PROJECT_ID
```

**Note:** The first time you run this, you'll need to authorize Cloud Build to access your GitHub repository through the GCP Console.

### Step 2: Configure GitHub Repository Settings

1. Go to your GitHub repository: https://github.com/OSUBlakester/BravoGCPCopilot
2. Click **Settings** > **Branches**
3. Under "Branch protection rules", click **Add rule**
4. Configure the `main` branch protection:
   - Branch name pattern: `main`
   - ✅ Require a pull request before merging
   - ✅ Require approvals (1)
   - ✅ Dismiss stale pull request approvals when new commits are pushed
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - Click **Create** or **Save changes**

This ensures no one (including you) can push directly to `main` without a PR and review.

### Step 3: Alternative - GitHub Actions (Optional)

If you prefer GitHub Actions over Cloud Build, create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main

env:
  PROJECT_ID: your-gcp-project-id
  SERVICE_NAME: bravogcpcopilot
  REGION: us-central1

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1

      - name: Build and push Docker image
        run: |
          gcloud builds submit --config cloudbuild.yaml

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy $SERVICE_NAME \
            --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
            --region $REGION \
            --platform managed \
            --allow-unauthenticated
```

## Daily Workflow

### For You (Repository Owner)

1. **Create a feature branch:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/my-new-feature
   ```

2. **Make changes and commit:**
   ```bash
   git add .
   git commit -m "Add new feature"
   git push origin feature/my-new-feature
   ```

3. **Open Pull Request on GitHub**
   - Go to GitHub repository
   - Click "Compare & pull request"
   - Fill out the PR template
   - Request review from your collaborator

4. **After approval, merge:**
   - Click "Merge pull request" on GitHub
   - Deployment to Cloud Run happens automatically
   - Monitor progress: GCP Console > Cloud Build > History

### For Your Collaborator

1. **Clone the repository (first time only):**
   ```bash
   git clone https://github.com/OSUBlakester/BravoGCPCopilot.git
   cd BravoGCPCopilot
   ```

2. **Set up local development:**
   ```bash
   # Copy configuration files
   cp config.py.template config.py
   # (You'll need to share secure credentials separately)
   
   # Start local development with Minikube
   skaffold dev --profile cloud-run-dev-internal
   ```

3. **Follow the same workflow:**
   - Create feature branch
   - Make changes
   - Push and open PR
   - Wait for your review

## Branch Protection Benefits

- ✅ Prevents accidental direct pushes to `main`
- ✅ Ensures code review before deployment
- ✅ Maintains clean git history
- ✅ Facilitates knowledge sharing
- ✅ Catches issues before production

## Monitoring Deployments

### Cloud Build Dashboard
```bash
# Open Cloud Build console
gcloud builds list --limit=10
```

Or visit: https://console.cloud.google.com/cloud-build/builds

### Cloud Run Dashboard
```bash
# Check service status
gcloud run services describe bravogcpcopilot --region=us-central1

# View recent revisions
gcloud run revisions list --service=bravogcpcopilot --region=us-central1
```

Or visit: https://console.cloud.google.com/run

## Rollback Procedure

If a deployment causes issues:

```bash
# Option 1: Revert the merge commit
git revert <merge-commit-hash>
git push origin main
# This triggers a new deployment with the revert

# Option 2: Roll back to previous Cloud Run revision
gcloud run services update-traffic bravogcpcopilot \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=us-central1
```

## Troubleshooting

### Build Fails
1. Check Cloud Build logs in GCP Console
2. Common issues:
   - Missing environment variables
   - Docker build errors
   - Permission issues

### Deployment Fails
1. Check Cloud Run logs
2. Verify service account permissions
3. Check resource limits (memory, CPU)

### Need to Deploy Manually
```bash
# Emergency manual deployment (avoid if possible)
./deploy.sh
```

## Security Best Practices

1. **Never commit secrets** - Use Google Secret Manager
2. **Review all PRs** - Even your own
3. **Use short-lived branches** - Merge within 1-2 days
4. **Keep main stable** - Always deployable
5. **Test locally first** - Don't rely on Cloud Build for testing

## Next Steps

1. Run the setup commands above
2. Commit and push the new workflow files:
   ```bash
   git add CONTRIBUTING.md WORKFLOW_SETUP.md .github/pull_request_template.md cloudbuild.yaml
   git commit -m "Add Git-centric workflow and automated deployment"
   git push origin main
   ```
3. Share `CONTRIBUTING.md` with your collaborator
4. Practice the workflow with a small test PR

---

**Questions?** Refer to CONTRIBUTING.md or check existing PRs for examples.
