"""
Environment Configuration for Bravo AAC Application
Supports development, testing, and production environments
"""
import os
from typing import Dict, Any

# Environment detection
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()

# Environment-specific configurations
ENVIRONMENT_CONFIGS = {
    'development': {
        # GCP Project Configuration
        'gcp_project_id': 'bravo-dev-465400',
        'firestore_project': 'bravo-dev-465400',
        'firebase_config_path': '/keys/bravo-dev-firebase-key.json',
        
        # CORS Settings
        'allowed_origins': [
            'http://localhost:3000',
            'http://localhost:8080', 
            'https://dev.talkwithbravo.com'
        ],
        
        # Debug Settings
        'debug': True,
        'log_level': 'DEBUG',
        
        # Service Account Paths
        'service_account_key_path': '/keys/bravo-dev-service-account.json',
        
        # Domain Configuration
        'domain': 'dev.talkwithbravo.com',
        'environment_name': 'Development',
        

        # Client Firebase Configuration
        'client_firebase_config': {
            'apiKey': "AIzaSyDXMsugfCLTMQIlj6Y_uT7iqgK8MTmEZVM",
            'authDomain': "bravo-dev-465400.firebaseapp.com",
            'projectId': "bravo-dev-465400",
            'storageBucket': "bravo-dev-465400.firebasestorage.app",
            'messagingSenderId': "894197055102",
            'appId': "1:894197055102:web:d71bf54b2166ca8aba222f",
            'measurementId': "G-NQKM7HSYHZ"
        }
    },
        
    'testing': {
        # GCP Project Configuration
        'gcp_project_id': 'bravo-test-465400',
        'firestore_project': 'bravo-test-465400',
        'firebase_config_path': '/keys/bravo-test-firebase-key.json',
        
        # CORS Settings
        'allowed_origins': [
            'https://test.talkwithbravo.com'
        ],
        
        # Debug Settings
        'debug': False,
        'log_level': 'INFO',
        
        # Service Account Paths
        'service_account_key_path': '/keys/bravo-test-service-account.json',
        
        # Domain Configuration
        'domain': 'test.talkwithbravo.com',
        'environment_name': 'Testing',

        
        # Client Firebase Configuration
        'client_firebase_config': {
            'apiKey': "AIzaSyDF3dUvhuxSn-uSG81OIdjgGqvwpRmLnrk",
            'authDomain': "bravo-test-465400.firebaseapp.com",
            'projectId': "bravo-test-465400",
            'storageBucket': "bravo-test-465400.firebasestorage.app",
            'messagingSenderId': "22852552488",
            'appId': "1:22852552488:web:e77b29ff19b3b6999ff21d"
        }
    },

    'production': {
        # GCP Project Configuration
        'gcp_project_id': 'bravo-prod-465323',
        'firestore_project': 'bravo-prod-465323',
        'firebase_config_path': '/keys/bravo-prod-firebase-key.json',
        
        # CORS Settings
        'allowed_origins': [
            'https://talkwithbravo.com'
        ],
        
        # Debug Settings
        'debug': False,
        'log_level': 'WARNING',
        
        # Service Account Paths
        'service_account_key_path': '/keys/bravo-prod-service-account.json',
        
        # Domain Configuration
        'domain': 'talkwithbravo.com',
        'environment_name': 'Production',

        # Client Firebase Configuration
        'client_firebase_config': {
            'apiKey': "AIzaSyBpyj24DYSft1cFLWjB_pjzXnndgUJVjhk",
            'authDomain': "bravo-prod-465323.firebaseapp.com",
            'projectId': "bravo-prod-465323",
            'storageBucket':"bravo-prod-465323.firebasestorage.app",
            'messagingSenderId': "222892987413",
            'appId': "1:222892987413:web:b68db62cbdef3089a22a1c"
        }
    }
}

# Get current environment config
def get_config() -> Dict[str, Any]:
    """Get configuration for the current environment"""
    if ENVIRONMENT not in ENVIRONMENT_CONFIGS:
        raise ValueError(f"Unknown environment: {ENVIRONMENT}. Must be one of: {list(ENVIRONMENT_CONFIGS.keys())}")
    
    config = ENVIRONMENT_CONFIGS[ENVIRONMENT].copy()
    config['environment'] = ENVIRONMENT
    
    return config

# Current configuration
CONFIG = get_config()

# Convenience accessors
GCP_PROJECT_ID = CONFIG['gcp_project_id']
FIRESTORE_PROJECT = CONFIG['firestore_project']
FIREBASE_CONFIG_PATH = CONFIG['firebase_config_path']
SERVICE_ACCOUNT_KEY_PATH = CONFIG['service_account_key_path']
ALLOWED_ORIGINS = CONFIG['allowed_origins']
DEBUG = CONFIG['debug']
LOG_LEVEL = CONFIG['log_level']
DOMAIN = CONFIG['domain']
ENVIRONMENT_NAME = CONFIG['environment_name']

# Health check endpoint data
HEALTH_INFO = {
    'environment': ENVIRONMENT,
    'environment_name': ENVIRONMENT_NAME,
    'domain': DOMAIN,
    'gcp_project': GCP_PROJECT_ID,
    'debug_mode': DEBUG
}

print(f"🚀 Bravo AAC Application - {ENVIRONMENT_NAME} Environment")
print(f"   Domain: {DOMAIN}")
print(f"   GCP Project: {GCP_PROJECT_ID}")
print(f"   Debug Mode: {DEBUG}")
