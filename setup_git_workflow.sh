#!/bin/bash

# Quick Setup Script for Git-Centric Workflow
# Run this once to configure Cloud Build automated deployments

set -e

echo "🚀 Setting up Git-centric workflow for Bravo AAC Application"
echo ""

# Configuration from deploy.sh
SERVICE_NAME="bravo-aac-api"
REGION="us-central1"

# Prompt for environment
echo "Select environment to configure automated deployments:"
echo "  1) dev (bravo-dev-465400)"
echo "  2) test (bravo-test-465400)"
echo "  3) prod (bravo-prod-465323)"
echo "  4) All environments"
read -p "Enter choice (1-4): " ENV_CHOICE

case $ENV_CHOICE in
    1)
        ENVIRONMENTS=("dev")
        ;;
    2)
        ENVIRONMENTS=("test")
        ;;
    3)
        ENVIRONMENTS=("prod")
        ;;
    4)
        ENVIRONMENTS=("dev" "test" "prod")
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "📋 Configuration:"
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo "   Environments: ${ENVIRONMENTS[*]}"
echo ""
read -p "Continue with setup? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Setup cancelled"
    exit 0
fi

# Loop through each environment
for ENV in "${ENVIRONMENTS[@]}"; do
    # Map environment to Project ID
    case $ENV in
        "dev")
            PROJECT_ID="bravo-dev-465400"
            ENV_NAME="development"
            ;;
        "test")
            PROJECT_ID="bravo-test-465400"
            ENV_NAME="testing"
            ;;
        "prod")
            PROJECT_ID="bravo-prod-465323"
            ENV_NAME="production"
            ;;
    esac

    echo ""
    echo "========================================="
    echo "Setting up $ENV environment ($PROJECT_ID)"
    echo "========================================="

    echo ""
    echo "1️⃣ Setting active project..."
    gcloud config set project $PROJECT_ID

    echo ""
    echo "2️⃣ Enabling required GCP APIs..."
    gcloud services enable cloudbuild.googleapis.com \
      run.googleapis.com \
      containerregistry.googleapis.com \
      --project=$PROJECT_ID || echo "⚠️  APIs may already be enabled"

    echo ""
    echo "3️⃣ Granting Cloud Build permissions..."
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
    CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

    gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:${CLOUD_BUILD_SA}" \
      --role="roles/run.admin" || echo "⚠️  Permission may already exist"

    gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:${CLOUD_BUILD_SA}" \
      --role="roles/iam.serviceAccountUser" || echo "⚠️  Permission may already exist"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:${CLOUD_BUILD_SA}" \
      --role="roles/secretmanager.secretAccessor" || echo "⚠️  Permission may already exist"

    echo ""
    echo "4️⃣ Creating Cloud Build trigger for main branch..."
    TRIGGER_NAME="deploy-${ENV}-main"
    
    # Check if trigger already exists
    if gcloud builds triggers describe $TRIGGER_NAME --project=$PROJECT_ID &>/dev/null; then
        echo "⚠️  Trigger $TRIGGER_NAME already exists. Updating..."
        gcloud builds triggers delete $TRIGGER_NAME --project=$PROJECT_ID --quiet
    fi
    
    gcloud builds triggers create github \
      --name="$TRIGGER_NAME" \
      --repo-name="BravoGCPCopilot" \
      --repo-owner="OSUBlakester" \
      --branch-pattern="^main$" \
      --build-config="cloudbuild.yaml" \
      --substitutions="_SERVICE_NAME=$SERVICE_NAME,_REGION=$REGION,_ENV=$ENV,_ENV_NAME=$ENV_NAME" \
      --project=$PROJECT_ID || echo "⚠️  Manual GitHub connection may be needed"

    echo "✅ Setup complete for $ENV environment"
done

echo ""
echo "========================================="
echo "✅ All setup complete!"
echo "========================================="
echo ""
echo "📝 Next steps:"
echo "1. Connect GitHub to Cloud Build (first time only):"
echo "   Visit: https://console.cloud.google.com/cloud-build/triggers"
echo "   Click on any trigger and connect your GitHub account"
echo ""
echo "2. Configure branch protection on GitHub:"
echo "   Visit: https://github.com/OSUBlakester/BravoGCPCopilot/settings/branches"
echo "   Protect 'main' branch (require PR reviews)"
echo ""
echo "3. Test the workflow:"
echo "   - Create a feature branch"
echo "   - Make changes and push"
echo "   - Open a PR and merge to main"
echo "   - Watch automatic deployment in Cloud Build!"
echo ""
echo "4. Share CONTRIBUTING.md with your collaborator"
echo ""
echo "🎉 Automated deployments are ready!"
echo ""
echo "⚠️  Note: You can still use ./deploy.sh for manual deployments if needed"
