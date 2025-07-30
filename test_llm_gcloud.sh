#!/bin/bash

# LLM Testing with gcloud CLI
# Tests Google Cloud services that your app depends on

echo "🔧 LLM Infrastructure Testing with gcloud CLI"
echo "=============================================="
echo "🕐 Test time: $(date)"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "success") echo -e "${GREEN}✅ $message${NC}" ;;
        "error") echo -e "${RED}❌ $message${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️  $message${NC}" ;;
        "info") echo -e "${BLUE}ℹ️  $message${NC}" ;;
    esac
}

# Function to check command availability
check_command() {
    if command -v $1 &> /dev/null; then
        print_status "success" "$1 is available"
        return 0
    else
        print_status "error" "$1 is not available"
        return 1
    fi
}

# Function to check gcloud authentication
check_gcloud_auth() {
    echo "🔐 Checking gcloud authentication..."
    
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        local active_account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
        print_status "success" "Authenticated as: $active_account"
        return 0
    else
        print_status "error" "No active gcloud authentication found"
        echo "   Run: gcloud auth login"
        return 1
    fi
}

# Function to check current project
check_gcloud_project() {
    echo "📁 Checking gcloud project..."
    
    local current_project=$(gcloud config get-value project 2>/dev/null)
    if [ ! -z "$current_project" ]; then
        print_status "success" "Current project: $current_project"
        return 0
    else
        print_status "error" "No project set"
        echo "   Run: gcloud config set project YOUR_PROJECT_ID"
        return 1
    fi
}

# Function to test AI Platform APIs
test_ai_platform_apis() {
    echo "🤖 Testing AI Platform APIs..."
    
    # Test if AI Platform API is enabled
    local project=$(gcloud config get-value project 2>/dev/null)
    
    if gcloud services list --enabled --filter="name:aiplatform.googleapis.com" --format="value(name)" | grep -q "aiplatform"; then
        print_status "success" "AI Platform API is enabled"
    else
        print_status "warning" "AI Platform API not enabled"
        echo "   To enable: gcloud services enable aiplatform.googleapis.com"
    fi
    
    # Test Generative AI API
    if gcloud services list --enabled --filter="name:generativelanguage.googleapis.com" --format="value(name)" | grep -q "generativelanguage"; then
        print_status "success" "Generative Language API is enabled"
    else
        print_status "warning" "Generative Language API not enabled"
        echo "   To enable: gcloud services enable generativelanguage.googleapis.com"
    fi
}

# Function to test Cloud Run service
test_cloud_run_service() {
    echo "☁️  Testing Cloud Run service..."
    
    local project=$(gcloud config get-value project 2>/dev/null)
    local service_name="bravo-aac-api"
    local region="us-central1"
    
    # Check if service exists
    if gcloud run services describe $service_name --region=$region --format="value(metadata.name)" 2>/dev/null | grep -q "$service_name"; then
        print_status "success" "Cloud Run service '$service_name' exists in $region"
        
        # Get service URL
        local service_url=$(gcloud run services describe $service_name --region=$region --format="value(status.url)" 2>/dev/null)
        print_status "info" "Service URL: $service_url"
        
        # Test health endpoint
        echo "   Testing health endpoint..."
        if curl -f -s "$service_url/health" > /dev/null; then
            print_status "success" "Health endpoint is responding"
        else
            print_status "error" "Health endpoint is not responding"
        fi
        
    else
        print_status "error" "Cloud Run service '$service_name' not found in $region"
    fi
}

# Function to check Cloud Run logs for LLM errors
check_cloud_run_logs() {
    echo "📋 Checking recent Cloud Run logs for LLM errors..."
    
    local service_name="bravo-aac-api"
    local region="us-central1"
    
    # Get recent logs (last 10 minutes)
    echo "   Fetching logs from last 10 minutes..."
    local logs=$(gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$service_name AND timestamp>=\"$(date -u -d '10 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')\"" --limit=50 --format="value(textPayload)" 2>/dev/null)
    
    if [ ! -z "$logs" ]; then
        print_status "info" "Recent logs found, checking for LLM-related errors..."
        
        # Check for specific error patterns
        if echo "$logs" | grep -q "Backend LLM service unavailable"; then
            print_status "error" "Found 'Backend LLM service unavailable' errors"
        fi
        
        if echo "$logs" | grep -q "Primary LLM.*failed"; then
            print_status "error" "Found Primary LLM failure errors"
        fi
        
        if echo "$logs" | grep -q "GOOGLE_API_KEY"; then
            print_status "warning" "Found GOOGLE_API_KEY related messages"
        fi
        
        if echo "$logs" | grep -q "Error.*LLM"; then
            print_status "error" "Found general LLM errors"
        fi
        
        # Show last few log entries
        echo "   Last 5 log entries:"
        echo "$logs" | tail -5 | sed 's/^/      /'
    else
        print_status "warning" "No recent logs found"
    fi
}

# Function to test API key (if available)
test_api_key() {
    echo "🔑 Testing API key configuration..."
    
    if [ ! -z "$GOOGLE_API_KEY" ]; then
        print_status "success" "GOOGLE_API_KEY environment variable is set"
        print_status "info" "API key (first 5 chars): ${GOOGLE_API_KEY:0:5}*****"
    else
        print_status "warning" "GOOGLE_API_KEY environment variable not set locally"
        echo "   This might be set in Cloud Run environment"
    fi
}

# Function to test Cloud Build status
test_cloud_build_status() {
    echo "🏗️  Checking recent Cloud Build status..."
    
    # Get recent builds
    local recent_builds=$(gcloud builds list --limit=3 --format="table(id,status,createTime)" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        print_status "info" "Recent Cloud Build history:"
        echo "$recent_builds" | sed 's/^/   /'
    else
        print_status "warning" "Could not fetch Cloud Build history"
    fi
}

# Function to run all tests
run_all_tests() {
    local all_passed=true
    
    # Basic checks
    check_command "gcloud" || all_passed=false
    check_command "curl" || all_passed=false
    echo ""
    
    # Authentication and project
    check_gcloud_auth || all_passed=false
    check_gcloud_project || all_passed=false
    echo ""
    
    # API and service tests
    test_ai_platform_apis
    echo ""
    
    test_cloud_run_service
    echo ""
    
    test_api_key
    echo ""
    
    check_cloud_run_logs
    echo ""
    
    test_cloud_build_status
    echo ""
    
    echo "=============================================="
    if [ "$all_passed" = true ]; then
        print_status "success" "Infrastructure tests completed"
    else
        print_status "warning" "Some infrastructure issues detected"
    fi
}

# Main execution
run_all_tests
