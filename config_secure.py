"""
SECURITY NOTICE: Configuration Secured
=====================================

This configuration file previously contained sensitive information that has been moved to environment variables for security.

For development setup:
1. Copy .env.template to .env
2. Fill in your actual credentials in .env
3. Never commit .env to version control

For production deployment:
1. Set environment variables in your deployment platform
2. Use secure secret management services
3. Never hardcode credentials in source code

Required Environment Variables:
- GOOGLE_API_KEY
- DB_PASSWORD
- ENVIRONMENT (development/testing/production)
"""

import os
from typing import Dict, Any

# Environment detection
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()

# Note: Sensitive configuration details have been moved to environment variables
# This file now contains only non-sensitive structural information

# Basic configuration structure (sensitive values loaded from environment)
if ENVIRONMENT == 'development':
    CONFIG = {
        'environment': 'development',
        'debug': True,
        'gcp_project_id': os.getenv('GCP_PROJECT_ID', 'your-dev-project'),
        # Other non-sensitive config...
    }
elif ENVIRONMENT == 'testing':
    CONFIG = {
        'environment': 'testing', 
        'debug': False,
        'gcp_project_id': os.getenv('GCP_PROJECT_ID', 'your-test-project'),
        # Other non-sensitive config...
    }
else:  # production
    CONFIG = {
        'environment': 'production',
        'debug': False,
        'gcp_project_id': os.getenv('GCP_PROJECT_ID', 'your-prod-project'),
        # Other non-sensitive config...
    }

# Export commonly used values
DEBUG = CONFIG.get('debug', False)
SERVICE_ACCOUNT_KEY_PATH = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
ALLOWED_ORIGINS = ["http://localhost:8000"]  # Configure as needed
LOG_LEVEL = "INFO"
HEALTH_INFO = {"status": "ok"}
DOMAIN = "localhost"
