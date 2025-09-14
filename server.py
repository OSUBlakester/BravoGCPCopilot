import os
import sys

# Security: Remove debug prints of sensitive environment variables
# print("DEBUG: GOOGLE_API_KEY =", os.environ.get("GOOGLE_API_KEY"))
# print("DEBUG: GOOGLE_APPLICATION_CREDENTIALS =", os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
print("DEBUG: HOME =", os.environ.get("HOME")) # Also check HOME

# Import environment configuration
try:
    from config import CONFIG, SERVICE_ACCOUNT_KEY_PATH, ALLOWED_ORIGINS, DEBUG, LOG_LEVEL, HEALTH_INFO, DOMAIN
    print("✅ Loaded configuration from config.py")
except ImportError:
    # Fallback to environment variables when config.py is not available (e.g., in deployment)
    import os
    print("⚠️  config.py not found, using environment variables")
    
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'testing').lower()
    
    if ENVIRONMENT == 'testing':
        CONFIG = {
            'gcp_project_id': os.getenv('GCP_PROJECT_ID', 'bravo-test-465400'),
            'environment_name': 'Testing',
            'client_firebase_config': {
                'apiKey': os.getenv('FIREBASE_API_KEY_TEST', ''),
                'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN_TEST', 'bravo-test-465400.firebaseapp.com'),
                'projectId': os.getenv('FIREBASE_PROJECT_ID_TEST', 'bravo-test-465400'),
                'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET_TEST', 'bravo-test-465400.firebasestorage.app'),
                'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID_TEST', ''),
                'appId': os.getenv('FIREBASE_APP_ID_TEST', '')
            }
        }
        SERVICE_ACCOUNT_KEY_PATH = os.getenv('SERVICE_ACCOUNT_KEY_PATH', '/keys/bravo-test-service-account.json')
        ALLOWED_ORIGINS = [
            'https://test.talkwithbravo.com',
            'https://bravo-aac-api-946502488848.us-central1.run.app'
        ]
        DOMAIN = os.getenv('DOMAIN', 'test.talkwithbravo.com')
    elif ENVIRONMENT == 'production':
        CONFIG = {
            'gcp_project_id': os.getenv('GCP_PROJECT_ID', 'bravo-prod-project'),
            'environment_name': 'Production',
            'client_firebase_config': {
                'apiKey': os.getenv('FIREBASE_API_KEY_PROD', ''),
                'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN_PROD', 'bravo-prod-project.firebaseapp.com'),
                'projectId': os.getenv('FIREBASE_PROJECT_ID_PROD', 'bravo-prod-project'),
                'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET_PROD', 'bravo-prod-project.firebasestorage.app'),
                'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID_PROD', ''),
                'appId': os.getenv('FIREBASE_APP_ID_PROD', '')
            }
        }
        SERVICE_ACCOUNT_KEY_PATH = os.getenv('SERVICE_ACCOUNT_KEY_PATH', '/keys/bravo-prod-service-account.json')
        ALLOWED_ORIGINS = ['https://app.talkwithbravo.com']
        DOMAIN = os.getenv('DOMAIN', 'app.talkwithbravo.com')
    else:  # development
        CONFIG = {
            'gcp_project_id': os.getenv('GCP_PROJECT_ID', 'bravo-test-465400'),
            'environment_name': 'Development',
            'client_firebase_config': {
                'apiKey': os.getenv('FIREBASE_API_KEY_DEV', ''),
                'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN_DEV', 'bravo-test-465400.firebaseapp.com'),
                'projectId': os.getenv('FIREBASE_PROJECT_ID_DEV', 'bravo-test-465400'),
                'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET_DEV', 'bravo-test-465400.firebasestorage.app'),
                'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID_DEV', ''),
                'appId': os.getenv('FIREBASE_APP_ID_DEV', '')
            }
        }
        SERVICE_ACCOUNT_KEY_PATH = os.getenv('SERVICE_ACCOUNT_KEY_PATH', '/keys/service-account.json')
        ALLOWED_ORIGINS = [
            'http://localhost:3000',
            'http://localhost:8080',
            'http://localhost:8000'
        ]
        DOMAIN = os.getenv('DOMAIN', 'localhost:8000')
    
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    HEALTH_INFO = {
        'environment': ENVIRONMENT,
        'environment_name': CONFIG['environment_name'],
        'domain': DOMAIN,
        'gcp_project': CONFIG['gcp_project_id'],
        'debug_mode': DEBUG
    }
    
    print(f"🚀 Bravo AAC Application - {CONFIG['environment_name']} Environment")
    print(f"   Environment: {ENVIRONMENT}")
    print(f"   Domain: {DOMAIN}")
    print(f"   Debug Mode: {DEBUG}")


from fastapi import FastAPI, Request, HTTPException, Body, Path, Response, Header, Depends
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import google.generativeai as genai
from google.generativeai import caching
import json
import logging
import time
import datetime
import holidays
import calendar # For calculating floating observances
from datetime import date, timedelta, datetime as dt # Alias datetime to avoid conflict
from fastapi.middleware.cors import CORSMiddleware
import re
from sentence_transformers import SentenceTransformer
from jinja2 import Environment, FileSystemLoader
import urllib.parse
import http.client  # Import the http.client module
import requests  # Import the requests library (though http.client is used)
from bs4 import BeautifulSoup
import random
import aiohttp
import asyncio
from urllib.parse import urljoin, urlparse
import uuid
from pydantic import BaseModel, Field, field_validator, validator, conint # Import field_validator
from pydantic_core.core_schema import ValidationInfo # For more complex V2 validators if needed
from typing import List, Optional, Dict, Any, Union, Literal, Annotated
import google.api_core.exceptions # For specific error handling with LLM
from google.cloud import texttospeech as google_tts # Import Google Cloud Text-to-Speech with an alias
from contextlib import asynccontextmanager # Import for lifespan
import re # For regular expressions (used in model filtering)
from collections import Counter # Add this import at the top with other collections imports

import firebase_admin
from firebase_admin import credentials, auth, firestore
from firebase_admin._auth_utils import EmailAlreadyExistsError
from google.oauth2 import service_account # Import service_account
import openai # Add OpenAI import
# SERVICE_ACCOUNT_KEY_PATH is now imported from config.py

from google.cloud.firestore_v1 import Client as FirestoreClient # Alias to avoid conflict if other Client classes are imported
oauth2_scheme = HTTPBearer()

# Mood update tracking to prevent race conditions
mood_update_timestamps = {}  # Format: {account_id/aac_user_id: timestamp}

app = FastAPI()


# CORS middleware FIRST - Now uses environment-specific allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Environment-specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization", "X-User-ID", "Content-Type"],
)

@app.middleware("http")
async def debug_options_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        print(f"DEBUG: OPTIONS request received at {request.url}")
    response = await call_next(request)
    if request.method == "OPTIONS":
        print(f"DEBUG: OPTIONS response status: {response.status_code}")
        print(f"DEBUG: OPTIONS response headers: {dict(response.headers)}")
    return response


@app.post("/test-cors")
async def test_cors():
    return JSONResponse(content={"ok": True})

@app.get("/health")
async def health_check():
    """Health check endpoint with environment information"""
    return JSONResponse(content={
        **HEALTH_INFO,
        "status": "healthy",
        "services": {
            "firebase": firebase_app is not None,
            "firestore": firestore_db is not None,
            "sentence_transformer": sentence_transformer_model is not None,
            "primary_llm": primary_llm_model_instance is not None,
            "fallback_llm": fallback_llm_model_instance is not None,
            "openai": openai_client is not None,
            "tts": tts_client is not None
        }
    })

@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get cache performance statistics for monitoring"""
    try:
        basic_stats = cache_manager.get_cache_stats()
        ttl_stats = cache_manager.get_cache_ttl_stats()
        
        return JSONResponse(content={
            "status": "success",
            "cache_stats": basic_stats,
            "ttl_stats": ttl_stats,
            "performance_notes": {
                "token_reduction": "72.7% token reduction achieved",
                "cost_optimization": "4-hour TTL policy for Gemini cache cost control",
                "cache_strategy": "COMBINED cache approach for 512+ token threshold compliance"
            },
            "timestamp": dt.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error getting cache stats: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )


# NEW: Endpoint to provide frontend with the correct Firebase config
@app.get("/api/frontend-config")
async def get_frontend_config():
    """Provides the necessary client-side Firebase configuration."""
    try:
        client_config = CONFIG.get('client_firebase_config', {})
        
        # Validate that we have some configuration
        if not client_config:
            logging.warning("No client_firebase_config found in CONFIG")
            # Return a minimal valid config to prevent frontend errors
            client_config = {
                'apiKey': '',
                'authDomain': '',
                'projectId': CONFIG.get('gcp_project_id', ''),
                'storageBucket': '',
                'messagingSenderId': '',
                'appId': ''
            }
        
        # Log the config being served for debugging
        logging.info(f"Serving frontend config with projectId: {client_config.get('projectId', 'unknown')}")
        logging.info(f"Config keys: {list(client_config.keys())}")
        logging.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
        
        # Return Firebase config directly at root level (as original auth system expects)
        return JSONResponse(content=client_config)
        
    except Exception as e:
        logging.error(f"Error serving frontend config: {e}", exc_info=True)
        # Return minimal valid config as fallback
        return JSONResponse(content={
                'apiKey': '',
                'authDomain': '',
                'projectId': CONFIG.get('gcp_project_id', ''),
                'storageBucket': '',
                'messagingSenderId': '',
                'appId': '',
                'error': 'Configuration temporarily unavailable'
        })


# NEW: Files that should be copied for a new user, relative to the user's data directory.
# This list is used by the _initialize_new_aac_user_profile helper function.
template_user_data_paths = {
    "user_info.txt": "Default user info.",
    "user_current.txt": "Location: Unknown\nPeople Present: None\nActivity: Idle",
    "settings.json": json.dumps({
        "scanDelay": 3500,
        "wakeWordInterjection": "hey",
        "wakeWordName": "bravo",
        "CountryCode": "US",
        "llm_provider": "gemini",  # New field: "gemini" or "chatgpt"
        "speech_rate": 180,
        "LLMOptions": 10,
        "FreestyleOptions": 20,
        "ScanningOff": False,
        "SummaryOff": False,
        "selected_tts_voice_name": "en-US-Neural2-A",
        "gridColumns": 10,
        "lightColorValue": 4294659860,
        "darkColorValue": 4278198852,
        "toolbarPIN": "1234",  # Default PIN for toolbar
        "autoClean": False,  # Default Auto Clean setting for freestyle (automatic cleanup on Speak Display)
        "enablePictograms": False  # Default AAC pictograms disabled
    }, indent=4),
    "birthdays.json": json.dumps({"userBirthdate": None, "friendsFamily": []}, indent=4),
    "user_diary.json": json.dumps([], indent=4),
    "chat_history.json": json.dumps([], indent=4),
    "user_favorites.json": json.dumps({ # Updated for new favorites system
        "buttons": []  # New structure: list of topic buttons with scraping configs
    }, indent=4),
    "audio_config.json": json.dumps({"personal_device": None, "system_device": None}, indent=4),
    "button_activity_log.json": json.dumps([], indent=4),
    "pages.json": json.dumps([
    {
        "name": "home",
        "displayName": "Home",
        "buttons": [
            {"row": 0,"col": 0,"text": "Greetings", "LLMQuery": "", "targetPage": "greetings", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 1,"text": "Going On", "LLMQuery": "", "targetPage": "goingon", "queryType": "", "speechPhrase": "Let's talk about things that are going on", "hidden": False},
            {"row": 0,"col": 2,"text": "Describe", "LLMQuery": "", "targetPage": "describe", "queryType": "", "speechPhrase": "Here's what I think", "hidden": False},
            {"row": 0,"col": 3,"text": "Favorite Topics", "LLMQuery": "", "targetPage": "!favorites", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 4,"text": "About Me", "LLMQuery": "Based on the details provided in the context, generate #LLMOptions different statements about the user.  The statements should be in first person, as if the user was telling someone about the user.  Statements can include information like age, family, disability and favorites.  The statements should also be conversational, not just presenting a fact.", "targetPage": "", "queryType": "options", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 5,"text": "Help", "LLMQuery": "Refer to the user info for most common physical issues and needs that can impact the user. Also include general physical issues that could be impacting someone with a similar condition to the user. Create up to #LLMOptions different statements that the user would announce if one of these physical issues was making the user uncomfortable or needing something addressed.  Each statement should be formed as if they are coming from the user and letting someone close by that the user is physically uncomfortable or needing something.  If there is a simple resolution for the issue, include it in the phrase with politely, including words like Please and Thank You, asking for the resolution.", "targetPage": "", "queryType": "options", "speechPhrase": "I need some help", "hidden": False},
            {"row": 0,"col": 6,"text": "Questions", "targetPage": "questions", "queryType": "", "speechPhrase": "I have a question", "hidden": False},
            {"row": 0,"col": 7,"text": "Free Style", "targetPage": "!freestyle", "queryType": "", "speechPhrase": "I'm picking my words.  Give me a minute:", "hidden": False},
            {"row": 0,"col": 8,"text": "Open Thread", "targetPage": "!threads", "queryType": "", "speechPhrase": "", "hidden": False},
            {"row": 0,"col": 9,"text": "Food", "LLMQuery": "Generate #LLMOptions related to food preferences, types of food, or meal times.", "targetPage": "", "queryType": "options", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 10,"text": "Drink", "LLMQuery": "Generate #LLMOptions related to drink preferences, types of drink.", "targetPage": "", "queryType": "options", "speechPhrase": None, "hidden": False},
        ]
    },
    {
        "name": "greetings",
        "displayName": "Greetings",
        "buttons": [
            {"row": 0,"col": 0,"text": "Home", "LLMQuery": "", "targetPage": "home", "queryType": "", "speechPhrase": "", "hidden": False},
            {"row": 0,"col": 1,"text": "Generic Greetings", "LLMQuery": "Generate #LLMOptions generic but expressive greetings, goodbyes or conversation starters.  Each item should be a single sentence and have varying levels of energy, creativity and engagement.  The greetings, goodbye or conversation starter should be in first person from the user.", "targetPage": "home", "queryType": "", "speechPhrase": "", "hidden": False},
            {"row": 0,"col": 2,"text": "Current Location", "LLMQuery": "Using the 'People Present' values from context, generate #LLMOptions expressive greetings.  Each item should be a single sentence and be very energetic and engaging.  The greetings should be in first person from the user, as if the user was speaking to someone in the room or a general greeting.  If there is information about one of the People Present in the user data, use that information to craft a more personal greeting.", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 3,"text": "Jokes", "LLMQuery": "Generate #LLMOptions completely unique, creative jokes or comedic observations. CRITICAL: Review the chat history thoroughly and absolutely DO NOT repeat any jokes, punchlines, or similar setups that have been used before. Each joke must be completely original and different from previous ones. Mix different comedy styles: observational humor, wordplay, puns, absurd situations, unexpected twists, or clever one-liners. Draw inspiration from current events, everyday situations, or creative scenarios. Each joke should include both the question and punchline together in the format 'Question? Punchline!' OR be a complete one-liner statement. Prioritize creativity and uniqueness over everything else.", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 4,"text": "Would you rather", "LLMQuery": "Generate #LLMOptions creative and fun would-you-rather type questions that could be used to start a conversation.  The more obscure comparison, the better.  Begin each option with Would you rather...", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 5,"text": "Did you know", "LLMQuery": "Generate #LLMOptions random, creative and possibly obscure trivia facts that can be used start a conversation.  You can user some of the user context select most of the trivia topics, but do not limit the topics on just the user's context.  The funnier that trivia fact, the better.'", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 6,"text": "Affirmations", "LLMQuery": "Generate #LLMOptions positive affirmations for the user to share with everyone around", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
        ]

    },
    {
        "name": "goingon",
        "displayName": "Going On",
        "buttons": [
            {"row": 0,"col": 0,"text": "Home", "LLMQuery": "", "targetPage": "home", "queryType": "", "speechPhrase": "", "hidden": False},
            {"row": 0,"col": 1,"text": "My Recent Activities", "LLMQuery": "Using the user diary and the current date, generate #LLMOptions  statements based on the most recent activities.  Each statement should be phrased conversationally as if they are coming from the user and telling someone nearby what the user has done recently.", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 2,"text": "My Upcoming Plans", "LLMQuery": "Based on the user diary and the current date, generate #LLMOptions statements based ONLY on diary entries with dates AFTER today's date. COMPLETELY IGNORE all entries from today or earlier dates. Only include future planned activities scheduled for dates later than today. Each statement should be phrased conversationally as if they are coming from the user and telling someone nearby what the user is planning to do or has coming up in the future.", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 3,"text": "You lately", "LLMQuery": "", "targetPage": "home", "queryType": "", "speechPhrase": "What have you been up to recently?", "hidden": False},
            {"row": 0,"col": 4,"text": "Any plans?", "LLMQuery": "", "targetPage": "home", "queryType": "", "speechPhrase": "Do you have any fun plans coming up?", "hidden": False}
        ]
    },
    {
        "name": "describe",
        "displayName": "Describe",
        "buttons": [
            {"row": 0,"col": 0,"text": "Home", "LLMQuery": "", "targetPage": "home", "queryType": "", "speechPhrase": "", "hidden": False},
            {"row": 0,"col": 1,"text": "Positive", "LLMQuery": "Provide up to #LLMOptions creative, with different levels of intensity,  and descriptive words or short phrases to describe something positive, as if someone was very excited", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 2,"text": "Negative", "LLMQuery": "Provide up to #LLMOptions creative, with different levels of intensity,  and descriptive words or short phrases to describe something negative, as if someone was very upset", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 3,"text": "Strange", "LLMQuery": "Provide up to #LLMOptions creative, with different levels of intensity,  and descriptive words or short phrases to describe something the user just heard or saw that was strange, odd or weird, as if someone was very excited.", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 4,"text": "Funny", "LLMQuery": "Provide up to #LLMOptions creative, with different levels of intensity, and descriptive words or short phrases to describe something the user just heard or saw that was funny as if someone was very excited.", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 5,"text": "Scary", "LLMQuery": "Provide up to #LLMOptions creative, with different levels of intensity, and descriptive words or short phrases the user could use to describe something the user just heard or saw that was scary, as if someone was very excited.", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 6,"text": "Sad", "LLMQuery": "Provide up to #LLMOptions creative, with different levels of intensity, and descriptive words or short phrases the user could use to describe something the user just heard or saw that was sad.", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
            [{"row": 0,"col": 7,"text": "Beautiful", "LLMQuery": "Provide up to #LLMOptions creative, with different levels of intensity, and descriptive words or short phrases the user could use to describe something the user just heard or saw that was beautiful, as if someone was very excited.", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},]
        ]
    },
    {
        "name": "questions",
        "displayName": "Questions",
        "buttons": [
            {"row": 0,"col": 0,"text": "Home", "LLMQuery": "", "targetPage": "home", "queryType": "", "speechPhrase": "", "hidden": False},
            {"row": 0,"col": 1,"text": "What?", "LLMQuery": "Generate #LLMOptions generic, basic questions, starting with what, for the user to ask someone nearby.  Include questions with different levels of inquiry, from simple to very simple. As simple as What is That?  Phrase each question as if it was asked by the user. All options must begin with What...", "targetPage": "home", "queryType": "", "speechPhrase": "", "hidden": False},
            {"row": 0,"col": 2,"text": "Who?", "LLMQuery": "Generate #LLMOptions generic, basic questions, starting with who, for the user to ask someone nearby.  Include questions with different levels of inquiry, from simple to very simple. As simple as Who is that?  Phrase each question as if it was asked by the user. All options must begin with Who...", "targetPage": "home", "queryType": "", "speechPhrase": "", "hidden": False},
            {"row": 0,"col": 3,"text": "Where?", "LLMQuery": "Generate #LLMOptions generic, basic questions, starting with where, for the user to ask someone nearby.  Include questions with different levels of inquiry, from simple to very simple. As simple as Where is that?  Phrase each question as if it was asked by the user. All options must begin with Where...", "targetPage": "home", "queryType": "", "speechPhrase": "", "hidden": False},
            {"row": 0,"col": 4,"text": "When?", "LLMQuery": "Generate #LLMOptions generic, basic questions, starting with when, for the user to ask someone nearby.  Include questions with different levels of inquiry, from simple to very simple. As simple as When is that?  Phrase each question as if it was asked by the user. All options must begin with When...", "targetPage": "home", "queryType": "", "speechPhrase": "", "hidden": False},
            {"row": 0,"col": 5,"text": "Why?", "LLMQuery": "Generate #LLMOptions generic, basic questions, starting with why, for the user to ask someone nearby.  Include questions with different levels of inquiry, from simple to very simple. As simple as Why is that?  Phrase each question as if it was asked by the user. All options must begin with Why...", "targetPage": "home", "queryType": "", "speechPhrase": "", "hidden": False},
            {"row": 0,"col": 6,"text": "How?", "LLMQuery": "Generate #LLMOptions generic, basic questions, starting with how, for the user to ask someone nearby.  Include questions with different levels of inquiry, from simple to very simple. As simple as How is that?  Phrase each question as if it was asked by the user. All options must begin with How...", "targetPage": "home", "queryType": "", "speechPhrase": "", "hidden": False}
        ]
    }
], indent=4),
}



# NEW: Simplified token verification dependency for initial registration
async def verify_firebase_token_only(
    token: Annotated[HTTPAuthorizationCredentials, Depends(oauth2_scheme)]
) -> Dict[str, str]:
    global firebase_app
    if not firebase_app:
        raise HTTPException(status_code=503, detail="Authentication service unavailable.")
    try:
        decoded_token = await asyncio.to_thread(auth.verify_id_token, token.credentials)
        # Return Firebase UID and email from the token
        return {"account_id": decoded_token['uid'], "email": decoded_token.get('email')}
    except auth.InvalidIdTokenError:
        logging.warning("Invalid Firebase ID token received during token-only verification.")
        raise HTTPException(status_code=401, detail="Invalid authentication token.")
    except auth.ExpiredIdTokenError:
        logging.warning("Expired Firebase ID token received during token-only verification.")
        raise HTTPException(status_code=401, detail="Authentication token expired. Please log in again.")
    except Exception as e:
        logging.error(f"Error during token-only verification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authentication error during token verification: {e}")



async def get_current_account_and_user_ids(
    token: Annotated[HTTPAuthorizationCredentials, Depends(oauth2_scheme)],
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_admin_target_account: str = Header(None, alias="X-Admin-Target-Account")  # NEW: Optional admin target account
) -> Dict[str, str]:
    global firebase_app, firestore_db

    if not firebase_app:
        logging.error("Firebase Admin SDK not initialized.")
        raise HTTPException(status_code=503, detail="Authentication service unavailable.")
    if not firestore_db:
        logging.error("Firestore DB client not initialized.")
        raise HTTPException(status_code=503, detail="Database service unavailable.")

    try:
        # 1. Verify Firebase ID Token
        decoded_token = await asyncio.to_thread(auth.verify_id_token, token.credentials)
        account_id = decoded_token['uid'] # This is the Firebase UID of the logged-in account

        # 2. Fetch Account details from Firestore
        account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id)
        account_doc = await asyncio.to_thread(account_doc_ref.get)

        if not account_doc.exists:
            logging.warning(f"Account (Firebase UID: {account_id}) not found in Firestore. Possibly deleted or corrupted.")
            raise HTTPException(status_code=401, detail="Account not found.")

        account_data = account_doc.to_dict()
        
        # NEW: Demo mode detection (non-breaking for Flutter)
        user_email = account_data.get("email", "")
        # Only demoreadonly is restricted, demo@ can make changes for content creation
        is_demo_account = user_email in ["demoreadonly@talkwithbravo.com"]
        
        # NEW: Handle admin/therapist context
        target_account_id = account_id  # Default to the authenticated account
        if x_admin_target_account:
            # Admin/therapist is trying to access another account
            user_email = account_data.get("email", "")
            is_admin = user_email == "admin@talkwithbravo.com"
            is_therapist = account_data.get("is_therapist", False)
            
            if not is_admin and not is_therapist:
                logging.warning(f"User {user_email} attempted admin access without permissions")
                raise HTTPException(status_code=403, detail="Access denied: Not an admin or therapist")
            
            # Verify access to target account
            target_account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(x_admin_target_account)
            target_account_doc = await asyncio.to_thread(target_account_doc_ref.get)
            
            if not target_account_doc.exists:
                logging.warning(f"Target account {x_admin_target_account} not found")
                raise HTTPException(status_code=404, detail="Target account not found")
            
            target_account_data = target_account_doc.to_dict()
            
            # Check permissions
            has_access = False
            if is_admin and target_account_data.get("allow_admin_access", True):
                has_access = True
            elif is_therapist and target_account_data.get("therapist_email") == user_email:
                has_access = True
            
            if not has_access:
                logging.warning(f"Access denied to account {x_admin_target_account} for user {user_email}")
                raise HTTPException(status_code=403, detail="Access denied to target account")
            
            target_account_id = x_admin_target_account
            logging.info(f"Admin/therapist {user_email} accessing account {target_account_id}")

        # 3. Authorize access to the specific AAC user_id (x_user_id)
        # Check if the requested x_user_id exists under the target account
        aac_user_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(target_account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION).document(x_user_id)
        aac_user_doc = await asyncio.to_thread(aac_user_doc_ref.get)

        if not aac_user_doc.exists:
            # Check if this is an authorized therapist/admin accessing a *different* account's user
            # This logic needs to be robust. For now, we assume x_user_id belongs to the `target_account_id`.
            logging.warning(f"AAC user_id '{x_user_id}' not found under account '{target_account_id}'.")
            raise HTTPException(status_code=403, detail="Access denied to this user profile.")

        # 4. Check Subscription Status (Basic check for POC/Trial) - use target account data
        target_account_data = account_data  # Default to authenticated account data
        if target_account_id != account_id:
            # Get target account data for subscription check
            target_account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(target_account_id)
            target_account_doc = await asyncio.to_thread(target_account_doc_ref.get)
            if target_account_doc.exists:
                target_account_data = target_account_doc.to_dict()
        
        if not target_account_data.get("is_active"):
            if target_account_data.get("promo_status") == "TRIALING":
                trial_end = dt.fromisoformat(target_account_data["trial_ends_at"])
                if dt.now() > trial_end:
                    logging.warning(f"Account {target_account_id} trial expired.")
                    # In a real app, you'd trigger Chargebee webhook to update is_active to False
                    # and potentially disable user access.
                    raise HTTPException(status_code=403, detail="Target account trial has expired.")
            elif target_account_data.get("promo_status") == "POC_FREE":
                # Always allow if POC_FREE
                pass
            else:
                logging.warning(f"Account {target_account_id} is not active and not on trial/POC.")
                raise HTTPException(status_code=403, detail="Target account not active.")

        # Warm user cache if needed.
        # This will block the first request for a user until the cache is ready.
        try:
            await cache_manager.warm_up_user_cache_if_needed(target_account_id, x_user_id)
        except Exception as e:
            # Log if cache warming fails, but don't block the user from proceeding.
            # The request will proceed without a cache, resulting in higher token usage for this call.
            logging.error(f"Error during cache warming for {target_account_id}/{x_user_id}: {e}")

        return {
            "account_id": target_account_id, 
            "aac_user_id": x_user_id,
            "is_demo_mode": is_demo_account  # Optional field for web frontend, Flutter can ignore
        }

    except auth.InvalidIdTokenError:
        logging.warning("Invalid Firebase ID token received.")
        raise HTTPException(status_code=401, detail="Invalid authentication token.")
    except auth.ExpiredIdTokenError:
        logging.warning("Expired Firebase ID token received.")
        raise HTTPException(status_code=401, detail="Authentication token expired. Please log in again.")
    except HTTPException as e:
        # Re-raise explicit HTTPExceptions
        raise e
    except Exception as e:
        logging.error(f"Error during token verification or user authorization: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authentication/Authorization error: {e}")





# Logging setup is now centralized at the top of the file.


static_file_path = os.path.join(os.getcwd(), "static")
app.mount("/static", StaticFiles(directory=static_file_path), name="static")
env = Environment(loader=FileSystemLoader('.'))



class AddUserToAccountRequest(BaseModel):
    display_name: str = Field(..., min_length=1)

class EditUserDisplayNameRequest(BaseModel):
    aac_user_id: str = Field(..., min_length=1)
    new_display_name: str = Field(..., min_length=1, max_length=50)

class DeleteUserRequest(BaseModel):
    aac_user_id: str = Field(..., min_length=1)

class CopyUserRequest(BaseModel):
    source_aac_user_id: str = Field(..., min_length=1)
    new_display_name: str = Field(..., min_length=1, max_length=50)

# --- Favorites System Models ---
class ScrapingConfig(BaseModel):
    url: str = Field(..., description="Website URL to scrape")
    headline_selector: str = Field(..., description="CSS selector for headlines")
    url_selector: str = Field(..., description="CSS selector for article links")
    url_attribute: str = Field(default="href", description="Attribute containing the URL")
    url_prefix: str = Field(default="", description="Prefix to add to relative URLs")
    keywords: List[str] = Field(default=[], description="Keywords to filter content")

class FavoriteButton(BaseModel):
    row: int = Field(..., ge=0, description="Grid row position")
    col: int = Field(..., ge=0, description="Grid column position")
    text: str = Field(..., min_length=1, max_length=50, description="Button display text")
    speechPhrase: Optional[str] = Field(None, description="Optional speech phrase before scraping")
    scraping_config: ScrapingConfig = Field(..., description="Web scraping configuration")
    hidden: bool = Field(default=False, description="Whether button is hidden")

class FavoritesData(BaseModel):
    buttons: List[FavoriteButton] = Field(default=[], description="List of favorite topic buttons")

class CreateFavoriteButtonRequest(BaseModel):
    button: FavoriteButton

class UpdateFavoriteButtonRequest(BaseModel):
    old_row: int
    old_col: int
    button: FavoriteButton

class DeleteFavoriteButtonRequest(BaseModel):
    row: int
    col: int

class TestScrapingRequest(BaseModel):
    scraping_config: ScrapingConfig


@app.get("/")
async def root():
    return RedirectResponse(url="/static/auth.html")



    

@app.get("/api/account/users")
async def get_aac_user_profiles(token_info: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]):
    """
    Returns a list of individual AAC user profiles associated with the authenticated account.
    This endpoint does NOT require an X-User-ID header as it lists users *for* the account.
    """
    account_id = token_info["account_id"] # Get account_id from the verified token

    global firestore_db
    if not firestore_db:
        raise HTTPException(status_code=503, detail="Firestore DB client not initialized.")

    try:
        users_collection_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
        
        docs = await asyncio.to_thread(users_collection_ref.stream)
        
        user_profiles = []
        for doc in docs:
            profile_data = doc.to_dict()
            if profile_data:
                user_profiles.append({
                    "aac_user_id": doc.id,
                    "display_name": profile_data.get("display_name", doc.id),
                })
        
        logging.info(f"Fetched {len(user_profiles)} AAC user profiles for account {account_id}.")
        return JSONResponse(content=user_profiles)

    except Exception as e:
        logging.error(f"Error fetching AAC user profiles for account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user profiles: {e}")


# Load pages from pages.json
async def load_pages_from_file(account_id: str, aac_user_id: str): # ADD user_id
    """
    Loads the list of pages from Firestore for a specific user.
    """
    default_pages_json_str = template_user_data_paths["pages.json"]
    default_pages_list = json.loads(default_pages_json_str)
    # Wrap default_pages_list in a dictionary for load_firestore_document
    default_document_data = {"pages": default_pages_list} # Prepare default as a dict

    # load_firestore_document will return a dictionary, e.g., {"pages": [...]}
    loaded_document = await load_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="config/pages_list", # The subpath under the AAC user document
        default_data=default_document_data # Pass the dictionary as default
    )

    # Extract the list of pages from the loaded dictionary
    return loaded_document.get("pages", []) # <--- CRITICAL FIX: Extract the list from the dict


# Save pages to pages.json
async def save_pages_to_file(account_id: str, aac_user_id: str, pages: List[Dict]): # ADD user_id
  """
  Saves the list of pages to Firestore for a specific user.
  """
  # Firestore documents store key-value pairs (dictionaries).
  # To store a list, put it as a field within a dictionary.
  document_data = {"pages": pages} # <--- CRITICAL FIX: Wrap the list in a dictionary
  return await save_firestore_document(
    account_id=account_id,
    aac_user_id=aac_user_id,
    doc_subpath="config/pages_list", # The subpath under the AAC user document
    data_to_save=document_data # Now sending a dictionary
  )

@app.get("/pages")
async def get_pages(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]): # ADD user_id
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    pages_data = await load_pages_from_file(account_id, aac_user_id) # Pass user_id
    return pages_data


@app.post("/pages") # For creating new pages
async def create_page(page: dict, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    try:
        account_id = current_ids["account_id"]
        aac_user_id = current_ids["aac_user_id"]
        pages = await load_pages_from_file(account_id, aac_user_id) # Ensure this is 'await'ed

        # Convert incoming page name to lowercase
        page["name"] = page["name"].lower()

        if any(p["name"] == page["name"] for p in pages):
            raise HTTPException(status_code=400, detail="Page with this name already exists")
        
        # Lowercase targetPage in buttons for the new page
        if "buttons" in page and isinstance(page["buttons"], list):
            for button in page["buttons"]:
                if isinstance(button, dict) and "targetPage" in button and button["targetPage"]:
                    button["targetPage"] = button["targetPage"].lower()

        pages.append(page)
        await save_pages_to_file(account_id, aac_user_id, pages) # ADD 'await' here
        
        # Invalidate caches that might be affected by page changes
        await cache_manager.invalidate_cache(account_id, aac_user_id)
        
        return {"message": "Page created successfully"}
    except Exception as e:
        logging.error(f"Error creating page for account {account_id} and user {aac_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/pages") # For updating existing pages
async def update_page(request: Request, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    try:
        # incoming_payload is the data sent from the frontend
        incoming_payload = await request.json()
        # The 'name' field is used to identify the page.
        # 'originalName' should be the name as it was loaded (which will be lowercase)
        original_page_name_from_client = incoming_payload.pop("originalName", None)
        current_page_name_to_find = original_page_name_from_client.lower() if original_page_name_from_client else None

        # Lowercase the new name if provided
        if "name" in incoming_payload and incoming_payload["name"]:
            incoming_payload["name"] = incoming_payload["name"].lower()

        if not current_page_name_to_find:
            raise HTTPException(status_code=400, detail="originalName is required for updates")

        # Load the ENTIRE list of pages for the user from Firestore
        aac_user_id = current_ids["aac_user_id"]
        account_id = current_ids["account_id"]
        all_pages_for_user = await load_pages_from_file(account_id, aac_user_id)

        found = False
        for i, p in enumerate(all_pages_for_user): # Iterate through the full list of pages
            if p["name"] == current_page_name_to_find: # p["name"] is already lowercase from DB
                # Found the page to update.
                # Merge the incoming update data with the existing page data.
                # This ensures fields not sent by the frontend (e.g., if a field wasn't edited) are preserved.
                updated_page_data = p.copy() # Make a copy of the existing page data
                updated_page_data.update(incoming_payload) # Apply updates from frontend

                # 'name' in updated_page_data is already lowercased if it came from incoming_payload
                if updated_page_data["name"] != current_page_name_to_find: # Check if name changed
                    logging.info(f"Page '{current_page_name_to_find}' is being renamed to '{updated_page_data['name']}' for account {account_id} and user {aac_user_id}.")
                    # If name changed, we also need to confirm the new name doesn't conflict
                    if any(existing_p["name"] == updated_page_data["name"] for existing_p in all_pages_for_user if existing_p["name"] != current_page_name_to_find):
                         raise HTTPException(status_code=400, detail=f"Page with new name '{updated_page_data['name']}' already exists.")

                # Lowercase targetPage in buttons for the updated page
                if "buttons" in updated_page_data and isinstance(updated_page_data["buttons"], list):
                    for button in updated_page_data["buttons"]:
                        if isinstance(button, dict) and "targetPage" in button and button["targetPage"]:
                            button["targetPage"] = button["targetPage"].lower()

                all_pages_for_user[i] = updated_page_data # Replace the old page with the merged data
                found = True
                break

        if not found:
            raise HTTPException(status_code=404, detail=f"Page with name '{current_page_name_to_find}' not found for account {account_id} and user {aac_user_id}.")

        # Save the ENTIRE updated list of pages back to Firestore
        # The save_pages_to_file wraps this list in a dictionary, which is what Firestore expects.
        await save_pages_to_file(account_id, aac_user_id, all_pages_for_user)
        
        # Invalidate caches that might be affected by page changes
        await cache_manager.invalidate_cache(account_id, aac_user_id)
        
        return {"message": "Page updated successfully"}
    except Exception as e:
        logging.error(f"Error updating page for user {aac_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/pages/{page_name}")
async def delete_page(page_name: str, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]): # ADD user_id
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    page_name_lower = page_name.lower() # Convert incoming page_name to lowercase
    pages_data = await load_pages_from_file(account_id, aac_user_id) # Load for this user
    # Prevent deletion of the 'home' page
    if page_name_lower == "home":
        raise HTTPException(status_code=400, detail="The 'home' page cannot be deleted.")

    initial_len = len(pages_data)
    pages_data = [p for p in pages_data if p["name"].lower() != page_name_lower] # Compare with lowercase
    if len(pages_data) < initial_len:
        await save_pages_to_file(account_id, aac_user_id, pages_data) # Save for this user
        
        # Invalidate caches that might be affected by page deletion
        await cache_manager.invalidate_cache(account_id, aac_user_id)
        
        return {"message": f"Page '{page_name}' deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail=f"Page with name '{page_name}' not found")
    



class UserCurrentState(BaseModel):
    location: Optional[str] = ""
    people: Optional[str] = "" # Renamed from People Present for consistency
    activity: Optional[str] = ""
    loaded_at: Optional[str] = None  # NEW: ISO timestamp when favorite was loaded
    favorite_name: Optional[str] = None  # NEW: Name of the favorite that was loaded
    saved_at: Optional[str] = None  # NEW: ISO timestamp when data was manually saved

class UserCurrentFavorite(BaseModel):
    name: str
    location: str
    people: str
    activity: str
    loaded_at: Optional[str] = None  # NEW: ISO timestamp when favorite was loaded

class UserCurrentFavoritesData(BaseModel):
    favorites: List[UserCurrentFavorite] = []

class FavoriteRequest(BaseModel):
    name: str
    location: str
    people: str
    activity: str

class ManageFavoriteRequest(BaseModel):
    action: str  # "edit" or "delete"
    old_name: Optional[str] = None  # For editing, the current name
    favorite: Optional[UserCurrentFavorite] = None  # For editing, the new data



@app.get("/get-user-current", response_model=UserCurrentState)
async def get_user_current_endpoint(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]): # ADD user_id
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    try:
        user_current_content_dict = await load_firestore_document( # Use the Firestore helper
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_state", # Back to current_state for existing accounts
            default_data=DEFAULT_USER_CURRENT.copy() # Use your default dictionary
        )
        # Return the full state including favorite tracking fields
        return JSONResponse(content={
            "location": user_current_content_dict.get("location", ""),
            "people": user_current_content_dict.get("people", ""),
            "activity": user_current_content_dict.get("activity", ""),
            "loaded_at": user_current_content_dict.get("loaded_at"),
            "favorite_name": user_current_content_dict.get("favorite_name"),
            "saved_at": user_current_content_dict.get("saved_at")
        })
    except Exception as e:
        logging.error(f"Error in /get-user-current for account {account_id} and user {aac_user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/user_current")
async def update_user_current_endpoint(payload: UserCurrentState, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    location = payload.location or ""
    people = payload.people or ""
    activity = payload.activity or ""
    loaded_at = payload.loaded_at  # Timestamp when favorite was loaded
    favorite_name = payload.favorite_name  # Name of the favorite that was loaded
    provided_saved_at = payload.saved_at  # Timestamp when data was saved (may be provided for favorite loads)
    
    # The content to embed for current state should be a single string for LLM context
    current_state_content = f"Location: {location}\nPeople Present: {people}\nActivity: {activity}"
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    
    # Use provided saved_at timestamp if available (for favorite loads), otherwise generate new timestamp
    from datetime import datetime, timezone
    if provided_saved_at:
        saved_at = provided_saved_at  # Use the timestamp from the client (favorite load)
    else:
        saved_at = datetime.now(timezone.utc).isoformat()  # Generate new timestamp (manual save)
    
    data_to_save = {
        "location": location, 
        "people": people, 
        "activity": activity,
        "saved_at": saved_at  # Always update saved_at when manually saving
    }
    
    # If this is loading a favorite (loaded_at provided), preserve favorite info
    if loaded_at and favorite_name:
        data_to_save["loaded_at"] = loaded_at
        data_to_save["favorite_name"] = favorite_name
    else:
        # If manually saving without loading a favorite, clear favorite status
        # This ensures that manually changing location invalidates any previously loaded favorite
        data_to_save["loaded_at"] = None
        data_to_save["favorite_name"] = None
        
    success = await save_firestore_document(
        account_id = account_id,
        aac_user_id = aac_user_id,
        doc_subpath="info/current_state",
        data_to_save=data_to_save
    )
    
    # Cache invalidation for user current state changes (location, people, activity)
    if success:
        # Update USER_PROFILE cache with new current state
        try:
            # Get user info to maintain complete cache structure
            user_info_content_dict = await load_firestore_document(
                account_id, aac_user_id, "info/user_narrative"
            )
            user_info_content = user_info_content_dict.get("narrative", "") if user_info_content_dict else ""
            
            # Invalidate cache since user context changed
            await cache_manager.invalidate_cache(account_id, aac_user_id)
            logging.info(f"Invalidated cache due to current state change for account {account_id} and user {aac_user_id}")
        except Exception as cache_error:
            logging.error(f"Failed to update USER_PROFILE cache with current state for account {account_id} and user {aac_user_id}: {cache_error}")
            # Don't fail the entire operation due to cache update failure
    
    return {"success": success}

# --- User Current Favorites Endpoints ---

@app.get("/api/user-current-favorites", response_model=UserCurrentFavoritesData)
async def get_user_current_favorites(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """Get all user current location favorites"""
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    
    try:
        favorites_data = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_favorites",
            default_data={"favorites": []}
        )
        return UserCurrentFavoritesData(**favorites_data)
    except Exception as e:
        logging.error(f"Error loading user current favorites: {e}")
        return UserCurrentFavoritesData(favorites=[])

@app.post("/api/user-current-favorites")
async def save_user_current_favorite(payload: FavoriteRequest, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """Save a new user current location favorite"""
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    
    try:
        # Load existing favorites
        favorites_data = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_favorites",
            default_data={"favorites": []}
        )
        
        # Check if name already exists
        favorites_list = favorites_data.get("favorites", [])
        for favorite in favorites_list:
            if favorite.get("name", "").lower() == payload.name.lower():
                return {"success": False, "message": "A favorite with this name already exists"}
        
        # Add new favorite
        new_favorite = {
            "name": payload.name,
            "location": payload.location,
            "people": payload.people,
            "activity": payload.activity
        }
        favorites_list.append(new_favorite)
        
        # Save back to Firestore
        success = await save_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_favorites",
            data_to_save={"favorites": favorites_list}
        )
        
        if success:
            return {"success": True, "message": "Favorite saved successfully"}
        else:
            return {"success": False, "message": "Failed to save favorite"}
            
    except Exception as e:
        logging.error(f"Error saving user current favorite: {e}")
        return {"success": False, "message": "Error saving favorite"}

@app.post("/api/user-current-favorites/manage")
async def manage_user_current_favorite(payload: ManageFavoriteRequest, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """Edit or delete a user current location favorite"""
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    
    try:
        # Load existing favorites
        favorites_data = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_favorites",
            default_data={"favorites": []}
        )
        
        favorites_list = favorites_data.get("favorites", [])
        
        if payload.action == "delete":
            # Find and remove the favorite
            favorites_list = [f for f in favorites_list if f.get("name") != payload.old_name]
            message = "Favorite deleted successfully"
            
        elif payload.action == "edit" and payload.favorite:
            # Find and update the favorite
            for i, favorite in enumerate(favorites_list):
                if favorite.get("name") == payload.old_name:
                    favorites_list[i] = {
                        "name": payload.favorite.name,
                        "location": payload.favorite.location,
                        "people": payload.favorite.people,
                        "activity": payload.favorite.activity
                    }
                    break
            message = "Favorite updated successfully"
        else:
            return {"success": False, "message": "Invalid action or missing data"}
        
        # Save back to Firestore
        success = await save_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_favorites",
            data_to_save={"favorites": favorites_list}
        )
        
        if success:
            return {"success": True, "message": message}
        else:
            return {"success": False, "message": "Failed to save changes"}
            
    except Exception as e:
        logging.error(f"Error managing user current favorite: {e}")
        return {"success": False, "message": "Error managing favorite"}


# --- AI Prompt Generation Endpoint ---

class GeneratePromptRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)

@app.post("/api/generate-llm-prompt")
async def generate_llm_prompt(payload: GeneratePromptRequest, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """Generate an optimized LLM prompt from a user's natural language description"""
    try:
        user_description = payload.description.strip()
        
        # Create a prompt to generate an optimized LLM query
        meta_prompt = f"""
You are an expert at creating prompts for language models in AAC (Augmentative and Alternative Communication) applications.

A user wants to create a button that will use AI to generate options. They described what they want as: "{user_description}"

Create a clear, specific prompt that will generate useful options for an AAC user. The prompt should:
1. Be clear and specific about what to generate
2. Include "#LLMOptions" as a placeholder for the number of options
3. Ensure options are appropriate for AAC communication
4. Make options actionable and easy to select
5. Use first-person perspective when appropriate

Examples of good prompts:
- "Generate #LLMOptions common greetings and conversation starters in first person that are warm and friendly."
- "Generate #LLMOptions different ways to express being hungry or wanting food, suitable for various social situations."
- "Generate #LLMOptions questions I can ask to start a conversation about current events or news."

Generate ONLY the prompt text, nothing else:"""

        # Use the LLM to generate the optimized prompt
        response_text = await _generate_gemini_content_with_fallback(meta_prompt)
        
        if response_text:
            # Clean up the response - remove any extra quotes or formatting
            cleaned_prompt = response_text.strip().strip('"').strip("'")
            return {"success": True, "prompt": cleaned_prompt}
        else:
            # Fallback: create a basic prompt
            fallback_prompt = f"Generate #LLMOptions options related to {user_description}. Each option should be clear and actionable for AAC communication."
            return {"success": True, "prompt": fallback_prompt}
            
    except Exception as e:
        logging.error(f"Error generating LLM prompt: {e}")
        # Return a simple fallback prompt
        fallback_prompt = f"Generate #LLMOptions options for {payload.description}."
        return {"success": True, "prompt": fallback_prompt}


# --- Configuration ---
SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2" # Model for generating embeddings

# LLM Model Configuration - Environment Variables
# Gemini Models
GEMINI_PRIMARY_MODEL = os.environ.get("GEMINI_PRIMARY_MODEL", "models/gemini-1.5-flash-latest")
GEMINI_FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "models/gemini-pro")

# ChatGPT Models - GPT-5 requires: max_completion_tokens, temperature=1.0 (default only)
# GPT-4o/4o-mini use: max_tokens, adjustable temperature
CHATGPT_PRIMARY_MODEL = os.environ.get("CHATGPT_PRIMARY_MODEL", "gpt-4o-mini")
CHATGPT_FALLBACK_MODEL = os.environ.get("CHATGPT_FALLBACK_MODEL", "gpt-4o")

# Keep legacy defaults for backward compatibility
DEFAULT_PRIMARY_LLM_MODEL_NAME = GEMINI_PRIMARY_MODEL
DEFAULT_FALLBACK_LLM_MODEL_NAME = GEMINI_FALLBACK_MODEL

CONTEXT_N_RESULTS = 5 # Number of context documents to retrieve from ChromaDB


CONTEXT_N_RESULTS = 5 # Increased context results
MAX_CHAT_HISTORY = 50 # Max number of chat entries to keep
MAX_DIARY_CONTEXT = 5 # Max number of recent/future diary entries for LLM
MAX_CHAT_CONTEXT = 5 # Max number of recent chat turns for LLM


DEFAULT_COUNTRY_CODE = 'US'
DEFAULT_SPEECH_RATE = 180 
DEFAULT_TTS_VOICE = "en-US-Neural2-A" # A good quality default Google TTS voice
DEFAULT_LLM_OPTIONS = 10 # Default LLM Options
DEFAULT_WAKE_WORD_INTERJECTION = "Hey" # Default interjection
DEFAULT_WAKE_WORD_NAME = "Friend" # Default name

DEFAULT_USER_INFO = {
    "narrative": "Welcome to Bravo! This is your personal communication assistant. As you use the app, this section will contain information about you, your interests, communication preferences, and important personal details that help customize your experience. You can update this information anytime through the user info settings to make your communication more personalized and effective.",
    "currentMood": None
}
DEFAULT_USER_CURRENT = {"location": "Unknown", "people": "None", "activity": "Idle", "loaded_at": None, "favorite_name": None, "saved_at": None}
DEFAULT_COLUMNS = 10 # Default number of columns in the grid
DEFAULT_LIGHT_COLOR = 4294659860 # Default light color
DEFAULT_DARK_COLOR = 4278198852 # Default dark color

# --- Updated Defaults to include wake word parts ---
DEFAULT_SETTINGS = {
    "scanDelay": 3500,
    "wakeWordInterjection": DEFAULT_WAKE_WORD_INTERJECTION, # Default interjection
    "wakeWordName": DEFAULT_WAKE_WORD_NAME,      # Default name
    "CountryCode": DEFAULT_COUNTRY_CODE,          # Default Country US
    "llm_provider": "gemini", # New setting: "gemini" or "chatgpt"
    "speech_rate": DEFAULT_SPEECH_RATE,            # Default speech rate in WPM
    "LLMOptions": DEFAULT_LLM_OPTIONS,           # Default LLM Options
    "FreestyleOptions": 20,  # Default Freestyle Options
    "ScanningOff": False, # Default scanning off
    "SummaryOff": False, # Default summary off
    "selected_tts_voice_name": DEFAULT_TTS_VOICE, # Default TTS voice
    "gridColumns": DEFAULT_COLUMNS, # Default grid columns
    "lightColorValue": DEFAULT_LIGHT_COLOR, # Default light color
    "darkColorValue": DEFAULT_DARK_COLOR, # Default dark color
    "scanLoopLimit": 0, # Default scan loop limit (0 = unlimited)
    "toolbarPIN": "1234",  # Default PIN for toolbar
    "autoClean": False,  # Default Auto Clean setting for freestyle (automatic cleanup on Speak Display)
    "displaySplash": False,  # Default splash screen display setting
    "displaySplashTime": 3000,  # Default splash screen duration (3 seconds)
    "enableMoodSelection": True,  # Default mood selection enabled
    "enablePictograms": False  # Default AAC pictograms disabled
}


# --- Default Birthday Structure ---
DEFAULT_BIRTHDAYS = {
    "userBirthdate": None, # Expects "YYYY-MM-DD" string or None
    "friendsFamily": []    # List of {"name": "...", "monthDay": "MM-DD"}
}

# --- Default Friends & Family Structure ---
DEFAULT_RELATIONSHIPS = [
    "Parent", "Child", "Sibling", "Grandparent", "Grandchild", "Spouse", "Partner", 
    "Cousin", "Aunt", "Uncle", "Best Friend", "Close Friend", "Friend", "Acquaintance", 
    "Therapist", "Doctor", "Caregiver", "Teacher", "Coworker", "Boss", "Neighbor", 
    "Group Member", "Other"
]

DEFAULT_FRIENDS_FAMILY = []  # List of friends and family entries

DEFAULT_DIARY: List[Dict] = [] # Diary is a list of entries
DEFAULT_CHAT_HISTORY: List[Dict] = [] # Chat history is a list of entries
DEFAULT_BUTTON_ACTIVITY_LOG: List[Dict] = [] # For button clicks

# Legacy scraping config (kept for migration)
DEFAULT_SCRAPING_CONFIG = {
    "news_sources": [],
    "sports_sources": [],
    "entertainment_sources": []
}

# New favorites structure - grid of topic buttons with scraping configs

# === CACHE MANAGER SERVICE ===
class GeminiCacheManager:
    """
    Manages Gemini context caching to optimize token usage and performance.
    This manager creates a single, combined cache per user that includes all
    relevant context (user info, settings, diary, etc.).
    """
    def __init__(self, ttl_hours: int = 4):
        # Stores the name of the created Gemini CachedContent object for each user.
        # Format: { "account_id_aac_user_id": "cachedContents/..." }
        self._user_cache_map = {}
        # Stores the creation timestamp of the cache to manage its lifecycle.
        # Format: { "account_id_aac_user_id": 1678886400.0 }
        self._cache_creation_times = {}
        self.ttl_seconds = ttl_hours * 3600
        logging.info(f"Cache Manager initialized with a {ttl_hours}-hour TTL.")

    def _get_user_key(self, account_id: str, aac_user_id: str) -> str:
        """Generates a unique key for a user to manage their cache."""
        return f"{account_id}_{aac_user_id}"

    async def _is_cache_valid(self, user_key: str) -> bool:
        """Checks if a user's cache exists and is within its TTL."""
        if user_key not in self._user_cache_map:
            return False
        
        creation_time = self._cache_creation_times.get(user_key, 0)
        is_expired = (dt.now().timestamp() - creation_time) > self.ttl_seconds
        
        if is_expired:
            logging.warning(f"Cache for user '{user_key}' has expired. TTL: {self.ttl_seconds}s.")
            # Clean up expired cache entry
            self._user_cache_map.pop(user_key, None)
            self._cache_creation_times.pop(user_key, None)
            return False
            
        return True

    async def _build_combined_context_string(self, account_id: str, aac_user_id: str, query_hint: str = "") -> str:
        """
        Fetches all user-related data from Firestore and compiles it into a single
        string formatted for the LLM prompt.
        """
        logging.info(f"Building combined context string for {account_id}/{aac_user_id}...")
        
        # Fetch all data concurrently
        tasks = {
            "user_info": load_firestore_document(account_id, aac_user_id, "info/user_narrative", DEFAULT_USER_INFO),
            "user_current": load_firestore_document(account_id, aac_user_id, "info/current_state", DEFAULT_USER_CURRENT),
            "settings": load_settings_from_file(account_id, aac_user_id),
            "birthdays": load_birthdays_from_file(account_id, aac_user_id),
            "diary": load_diary_entries(account_id, aac_user_id),
            "chat_history": load_chat_history(account_id, aac_user_id),
            "pages": load_pages_from_file(account_id, aac_user_id),
            "friends_family": load_firestore_document(account_id, aac_user_id, "info/friends_family", {"friends_family": []}),
        }
        results = await asyncio.gather(*tasks.values())
        context_data = dict(zip(tasks.keys(), results))

        # System prompt providing instructions to the LLM
        system_prompt = """You are Bravo, an AI communication assistant for AAC users. Your role is to generate relevant response options based on the user's context.

IMPORTANT: Always prioritize the User Profile information as your PRIMARY source. The user's personal details, family, interests, and disability information should be the foundation of your responses. Use the current situation and recent activity as SECONDARY context to personalize responses, but never let them overshadow the core user profile.

🔊 CRITICAL SPEECH RULE: When creating summary fields for response options, NEVER include the user's personal name. The summary field is what gets spoken aloud to the user, so it should use generic language like "I am", "I feel", "I want" instead of "John is", "John feels", "John wants". Personal names should only appear in the full option text if necessary, never in summaries.

Format responses as a JSON array of objects, each with "option" and "summary" keys.
Analyze the provided context to create helpful, personalized suggestions."""

        # Assemble the context string with USER PROFILE FIRST and EMPHASIZED
        context_parts = [f"--- SYSTEM PROMPT ---\n{system_prompt}\n"]

        # PRIORITIZE USER PROFILE - This should be the PRIMARY focus for all responses
        if context_data["user_info"]:
            user_narrative = context_data['user_info'].get('narrative', 'Not available')
            context_parts.append(f"=== PRIMARY USER PROFILE (MOST IMPORTANT) ===\n{user_narrative}\n\n⚠️  REMEMBER: This user profile should be the foundation for ALL responses. Personal details, family, interests, and characteristics mentioned here are the most important context.\n")
        
        # MOOD - High Priority Context (Level 1.5) - Mood should immediately influence response tone and style
        if context_data["user_info"]:
            current_mood = context_data['user_info'].get('currentMood', 'Not set')
            print(f"🎭 MOOD CONTEXT: Building context for {account_id}/{aac_user_id} - mood from data: '{current_mood}'")
            logging.info(f"🎭 Building context for {account_id}/{aac_user_id} - mood from data: '{current_mood}'")
            if current_mood and current_mood != 'Not set' and current_mood != 'None':
                print(f"🎯 MOOD PRIORITY: Adding HIGH PRIORITY mood section: {current_mood}")
                logging.info(f"🎯 Adding HIGH PRIORITY mood section: {current_mood}")
                context_parts.append(f"=== CURRENT MOOD (HIGH PRIORITY) ===\nUser's Current Mood: {current_mood}\n\n🎭 IMPORTANT: This mood should significantly influence the tone, energy, and style of your response. Let this mood guide how you express the user's personality.\n")
            else:
                print(f"⚠️ MOOD WARNING: No valid mood found - mood was: '{current_mood}'")
                logging.info(f"⚠️ No valid mood found - mood was: '{current_mood}'")
        
        # Secondary context - current situation (use sparingly, don't let it dominate user profile)
        if context_data["user_current"]:
            current_parts = []
            current_parts.extend([
                f"Location: {context_data['user_current'].get('location', 'Unknown')}",
                f"People Present: {context_data['user_current'].get('people', 'None')}",
                f"Activity: {context_data['user_current'].get('activity', 'Idle')}"
            ])
            context_parts.append(f"--- Current Situation (Secondary Context) ---\n{chr(10).join(current_parts)}\n")
        
        # Additional supporting context (least priority)
        if context_data["friends_family"]:
            context_parts.append(f"--- Friends & Family (Supporting Context) ---\n{json.dumps(context_data['friends_family'], indent=2)}\n")
        if context_data["settings"]:
            context_parts.append(f"--- User Settings (Supporting Context) ---\n{json.dumps(context_data['settings'], indent=2)}\n")
        if context_data["birthdays"] and (context_data["birthdays"].get("userBirthdate") or context_data["birthdays"].get("friendsFamily")):
            context_parts.append(f"--- Birthdays (Supporting Context) ---\n{json.dumps(context_data['birthdays'], indent=2)}\n")
        
        # Add current date right before diary entries so LLM can interpret entry dates correctly
        from datetime import datetime
        current_date_str = datetime.now().strftime('%Y-%m-%d')
        context_parts.append(f"--- TODAY'S DATE (CRITICAL FOR DIARY CONTEXT) ---\n{current_date_str}\n⚠️ IMPORTANT: Use this date to determine if diary entries are recent (past), current (today), or future events. Generate responses accordingly.\n")
        
        if context_data["diary"]:
            # Detect if this is a query about upcoming/future plans for enhanced filtering guidance
            is_upcoming_query = any(keyword in query_hint.lower() for keyword in [
                "upcoming", "future", "plans", "planning", "coming up", "scheduled", 
                "dates after today", "after today's date", "planned activities"
            ])
            
            # PRE-FILTER diary entries for upcoming queries to eliminate confusion
            if is_upcoming_query:
                # Only include diary entries with dates AFTER today
                future_entries = [
                    entry for entry in context_data['diary'] 
                    if entry.get('date', '') > current_date_str
                ]
                
                if future_entries:
                    diary_context = f"""--- Future Diary Entries (UPCOMING PLANS ONLY) ---
📅 TODAY'S DATE: {current_date_str}
✅ PRE-FILTERED: Only showing entries with dates AFTER {current_date_str}
🎯 THESE ARE CONFIRMED FUTURE EVENTS - use these for upcoming plans

Future Diary Entries ({len(future_entries)} entries found):
{json.dumps(future_entries[:10], indent=2)}
"""
                else:
                    diary_context = f"""--- Future Diary Entries (UPCOMING PLANS ONLY) ---
📅 TODAY'S DATE: {current_date_str}
❌ NO FUTURE ENTRIES FOUND: No diary entries with dates after {current_date_str}
💡 RESPONSE GUIDANCE: Since no future diary entries exist, respond that no upcoming plans are currently scheduled.
"""
            else:
                diary_context = f"""--- Diary Entries (Background Context) ---
📅 TODAY'S DATE: {current_date_str}
⚠️ CRITICAL INSTRUCTIONS FOR DIARY INTERPRETATION:
- Entries with dates BEFORE {current_date_str} = PAST events (use past tense: "I did", "I went", "I had")
- Entries with date {current_date_str} = TODAY'S events (use present tense: "I am", "I'm doing")  
- Entries with dates AFTER {current_date_str} = FUTURE events (use future tense: "I will", "I'm going to", "I have planned")

Diary Entries (most recent 15, sorted newest to oldest):
{json.dumps(context_data['diary'][:15], indent=2)}
"""
            context_parts.append(diary_context)
        if context_data["chat_history"]:
            # For joke generation, pass more history to prevent repetition
            history_count = 10 if "joke" in query_hint.lower() else 3
            context_parts.append(f"--- Recent Chat History (Background Context) ---\n{json.dumps(context_data['chat_history'][-history_count:], indent=2)}\n")
        if context_data["pages"]:
            context_parts.append(f"--- User-Defined Pages (Background Context) ---\n{json.dumps(context_data['pages'], indent=2)}\n")

        combined_string = "\n".join(context_parts)
        logging.info(f"Combined context for {account_id}/{aac_user_id} is {len(combined_string)} chars long.")
        return combined_string

    async def warm_up_user_cache_if_needed(self, account_id: str, aac_user_id: str) -> None:
        """
        Checks if a valid cache exists for the user. If not, it builds the
        combined context and creates a new Gemini CachedContent object.
        """
        logging.info(f"🔥 warm_up_user_cache_if_needed called for account_id={account_id}, aac_user_id={aac_user_id}")
        user_key = self._get_user_key(account_id, aac_user_id)
        logging.info(f"🔑 Generated user_key: {user_key}")
        if await self._is_cache_valid(user_key):
            logging.info(f"Cache for user '{user_key}' is already warm and valid.")
            return

        logging.info(f"Cache for user '{user_key}' is cold or invalid. Warming up...")
        try:
            combined_context = await self._build_combined_context_string(account_id, aac_user_id)

            # Gemini requires a minimum of 1,024 tokens to create a cache for Gemini 1.5/2.0 Flash.
            # Use a more accurate token estimation: roughly 3.5 chars per token for English text
            estimated_tokens = len(combined_context) // 3.5
            min_tokens_required = 1024
            
            logging.info(f"Context for user '{user_key}': {len(combined_context)} chars, ~{int(estimated_tokens)} tokens")
            
            if estimated_tokens < min_tokens_required:
                logging.warning(f"Context for user '{user_key}' has {int(estimated_tokens)} tokens < {min_tokens_required} minimum. Skipping cache creation.")
                return
            
            logging.info(f"Creating cache for user '{user_key}' with {int(estimated_tokens)} tokens (above {min_tokens_required} minimum)")

            # Create the cache using the Gemini API
            cache_display_name = f"user_cache_{user_key}_{int(dt.now().timestamp())}"
            
            # The model used for caching must match the model used for generation.
            cached_content = await asyncio.to_thread(
                caching.CachedContent.create,
                model=GEMINI_PRIMARY_MODEL,
                display_name=cache_display_name,
                contents=[{'role': 'user', 'parts': [{'text': combined_context}]}],
                ttl=timedelta(seconds=self.ttl_seconds)
            )

            self._user_cache_map[user_key] = cached_content.name
            self._cache_creation_times[user_key] = dt.now().timestamp()
            logging.info(f"Successfully warmed up cache for user '{user_key}'. Cache Name: {cached_content.name}")

        except Exception as e:
            logging.error(f"Failed to warm up cache for user '{user_key}': {e}", exc_info=True)
            # Ensure partial state is cleaned up on failure
            self._user_cache_map.pop(user_key, None)
            self._cache_creation_times.pop(user_key, None)

    async def get_cached_content_reference(self, account_id: str, aac_user_id: str) -> Optional[str]:
        """
        Returns the Gemini cache name (e.g., 'cachedContents/...') for the user
        if a valid cache exists.
        """
        user_key = self._get_user_key(account_id, aac_user_id)
        if await self._is_cache_valid(user_key):
            cache_name = self._user_cache_map.get(user_key)
            logging.info(f"Found valid cache reference for user '{user_key}': {cache_name}")
            return cache_name
        logging.warning(f"No valid cache reference found for user '{user_key}'.")
        return None

    async def invalidate_cache(self, account_id: str, aac_user_id: str) -> None:
        """Invalidates and deletes the cache for a specific user."""
        user_key = self._get_user_key(account_id, aac_user_id)
        cache_name = self._user_cache_map.pop(user_key, None)
        self._cache_creation_times.pop(user_key, None)

        if cache_name:
            try:
                # Get the cached content object first, then delete it.
                cache_to_delete = caching.CachedContent(name=cache_name)
                await asyncio.to_thread(cache_to_delete.delete)
                logging.info(f"Successfully invalidated and deleted cache '{cache_name}' for user '{user_key}'.")
            except Exception as e:
                logging.error(f"Error deleting Gemini cache '{cache_name}': {e}", exc_info=True)
        else:
            logging.info(f"No cache to invalidate for user '{user_key}'.")

    def get_cache_debug_info(self, account_id: str, aac_user_id: str) -> Dict:
        """Provides debugging information about a user's cache."""
        user_key = self._get_user_key(account_id, aac_user_id)
        cache_name = self._user_cache_map.get(user_key)
        creation_time = self._cache_creation_times.get(user_key)

        if not cache_name or not creation_time:
            return {"status": "No active cache found."}

        age_seconds = dt.now().timestamp() - creation_time
        time_left_seconds = self.ttl_seconds - age_seconds
        is_valid = time_left_seconds > 0

        return {
            "status": "Active" if is_valid else "Expired",
            "user_key": user_key,
            "cache_name": cache_name,
            "created_at": dt.fromtimestamp(creation_time).isoformat(),
            "expires_at": dt.fromtimestamp(creation_time + self.ttl_seconds).isoformat(),
            "age_minutes": round(age_seconds / 60, 2),
            "time_left_minutes": round(time_left_seconds / 60, 2),
            "is_valid": is_valid
        }

# Initialize global cache manager
cache_manager = GeminiCacheManager()

# === END CACHE MANAGER SERVICE ===
DEFAULT_FAVORITES_CONFIG = {
    "buttons": []  # List of favorite topic buttons
}


DEFAULT_HOME_PAGE_CONTENT = [
    {
        "name": "home",
        "displayName": "Home",
        "buttons": [
            {"row": 0,"col": 0,"text": "Greetings", "LLMQuery": "Generate #LLMOptions generic but expressive greetings, goodbyes or conversation starters. Each item should be a single sentence and have varying levels of energy, creativity and engagement. The greetings, goodbye or conversation starter should be in first person from the user.", "targetPage": "", "queryType": "options", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 1,"text": "Feelings", "LLMQuery": "Generate #LLMOptions common feelings or emotions to express, ranging from happy to sad, excited to calm.", "targetPage": "", "queryType": "options", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 2,"text": "Needs", "LLMQuery": "Generate #LLMOptions common personal needs to express, like needing help, food, water, rest, or a break.", "targetPage": "", "queryType": "options", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 3,"text": "Questions", "LLMQuery": "Generate #LLMOptions some general spoken questions that an AAC user might ask to lead to further options, e.g. 'Can I ask a question?' or 'Tell me about something'.", "targetPage": "", "queryType": "options", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 4,"text": "About Me", "LLMQuery": "Generate #LLMOptions common facts or personal details about myself, my likes, dislikes, or interests, suitable for sharing in conversation.", "targetPage": "", "queryType": "options", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 5,"text": "My Day", "LLMQuery": "Generate #LLMOptions common activities or events that might occur during my day, e.g., work, therapy, social events, meals.", "targetPage": "", "queryType": "options", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 6,"text": "Current Events", "targetPage": "!currentevents", "queryType": "currentevents", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 7,"text": "Favorites", "targetPage": "!favorites", "queryType": "favorites", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 8,"text": "Food", "LLMQuery": "Generate #LLMOptions related to food preferences, types of food, or meal times.", "targetPage": "", "queryType": "options", "speechPhrase": None, "hidden": False},
            {"row": 0,"col": 9,"text": "Drink", "LLMQuery": "Generate #LLMOptions related to drink preferences, types of drink.", "targetPage": "", "queryType": "options", "speechPhrase": None, "hidden": False},
        ]
    }
]


# Firestore paths and constants for new account structure
FIRESTORE_ACCOUNTS_COLLECTION = "accounts"
FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION = "users"
POC_PROMO_CODE = "POC4NOW"
FREE_TRIAL_PROMO_CODE = "FREETRIAL1M" # Define your 1-month trial code


RoutingTarget = Literal["personal", "system", "default"] # 'default' for fallback or if not specified

# --- Init$ialize ChromaDB ---
#collection = None # Initialize collection variable
# chroma_client = None # Initialize client variable


# Keep the global sentence_transformer_model, primary_llm_model_instance, fallback_llm_model_instance, tts_client.
# NO, let's move the actual initialization of sentence_transformer, llm, tts into initialize_backend_services
# as they are large objects. Define them globally as None and initialize in lifespan.

collection = None # (This will be removed later, still a global variable)
chroma_client_global = None # NEW: Keep a global chroma client for static db if needed, but per-user client is key.
sentence_transformer_model: Optional[SentenceTransformer] = None # Global instance
primary_llm_model_instance: Optional[genai.GenerativeModel] = None # Global instance
fallback_llm_model_instance: Optional[genai.GenerativeModel] = None # Global instance
openai_client: Optional[openai.OpenAI] = None # OpenAI client instance
tts_client: Optional[google_tts.TextToSpeechClient] = None # Global instance
firestore_db: Optional[FirestoreClient] = None
firebase_app: Optional[firebase_admin.App] = None # NEW



# --- Initialize Sentence Transformer ---
# DISABLED: Sentence Transformer is causing startup failures due to Hugging Face download issues
# We're not currently using RAG/ChromaDB functionality, so this is safe to disable
sentence_transformer_model = "DISABLED"  # Set to non-None to pass the initialization check
logging.info("Sentence Transformer initialization disabled (not currently used for LLM functionality)")

# sentence_transformer_model = None # Initialize variable
# try:
#     # Use the variable name consistently
#     sentence_transformer_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL, device="cpu") # Specify device if needed
#     logging.info(f"Sentence Transformer model '{SENTENCE_TRANSFORMER_MODEL}' loaded.")
# except Exception as e:
#     logging.error(f"Error initializing Sentence Transformer: {e}", exc_info=True)
#     sentence_transformer_model = None # Ensure model is None if setup fails

logging.info("Initializing Gemini API and models...")
api_key = os.environ.get("GOOGLE_API_KEY")
    
# Add explicit check and log for the API key value *before* using it
if not api_key:
    logging.error("GOOGLE_API_KEY environment variable NOT set or is empty. Gemini initialization will fail.")
    raise ValueError("GOOGLE_API_KEY environment variable not set.") # Re-raise immediately if critical
else:
    logging.info(f"DEBUG: GOOGLE_API_KEY successfully retrieved (first 5 chars): {api_key[:5]}*****") # Log partial key for security

    try:
        genai.configure(api_key=api_key)
        logging.info("Gemini API configured successfully.") # NEW CONFIRMATION LOG

        primary_model_name_from_settings = DEFAULT_PRIMARY_LLM_MODEL_NAME
        try:
            primary_llm_model_instance = genai.GenerativeModel(primary_model_name_from_settings)
            logging.info(f"Primary Gemini model '{primary_llm_model_instance.model_name}' initialized.")
        except Exception as e_primary:
            logging.error(f"Error initializing primary Gemini model '{primary_model_name_from_settings}': {e_primary}", exc_info=True)
            primary_llm_model_instance = None
        
        try:
            fallback_llm_model_instance = genai.GenerativeModel(DEFAULT_FALLBACK_LLM_MODEL_NAME)
            logging.info(f"Fallback Gemini model '{fallback_llm_model_instance.model_name}' initialized.")
        except Exception as e_fallback:
            logging.error(f"Error initializing fallback Gemini model '{DEFAULT_FALLBACK_LLM_MODEL_NAME}': {e_fallback}", exc_info=True)
            fallback_llm_model_instance = None
    except Exception as e_genai_config: # Catch any error from genai.configure itself
        logging.error(f"Fatal error during Gemini API configuration: {e_genai_config}", exc_info=True)
        # Ensure models are None if configuration fails
        primary_llm_model_instance = None
        fallback_llm_model_instance = None

# --- Initialize OpenAI Client ---
logging.info("Initializing OpenAI client...")
openai_api_key = os.environ.get("OPENAI_API_KEY")

if not openai_api_key:
    logging.warning("OPENAI_API_KEY environment variable not set. OpenAI functionality will be disabled.")
    openai_client = None
else:
    try:
        openai_client = openai.OpenAI(api_key=openai_api_key)
        logging.info(f"OpenAI client initialized successfully (API key first 5 chars): {openai_api_key[:5]}*****")
        
        # Test the connection with a simple API call
        try:
            models = openai_client.models.list()
            logging.info("OpenAI API connection verified successfully.")
        except Exception as e_test:
            logging.warning(f"OpenAI API test call failed: {e_test}")
            
    except Exception as e_openai:
        logging.error(f"Error initializing OpenAI client: {e_openai}", exc_info=True)
        openai_client = None

# --- Initialize Google Cloud Text-to-Speech Client ---
tts_client = None
try:
    tts_client = google_tts.TextToSpeechClient()
    logging.info("Google Cloud Text-to-Speech client initialized.")
except Exception as e:
    logging.error(f"Error initializing Google Cloud Text-to-Speech client: {e}", exc_info=True)
    # The application can still run, but Google TTS features will fail.


# New Pydantic model for adding an AAC user (already defined in previous response)
# class AddUserToAccountRequest(BaseModel):
#     display_name: str = Field(..., min_length=1)

@app.post("/api/account/add-aac-user")
async def add_aac_user_to_account(
    request_data: AddUserToAccountRequest,
    token_info: Annotated[Dict[str, str], Depends(verify_firebase_token_only)] # Use the simpler dependency
):
    account_id = token_info["account_id"] # Get account_id from the token
    user_email = token_info.get("email", "")
    
    # Demo mode restriction (non-breaking for Flutter)
    # Only demoreadonly is restricted, demo@ can make changes for content creation
    is_demo_account = user_email in ["demoreadonly@talkwithbravo.com"]
    if is_demo_account:
        raise HTTPException(status_code=403, detail="Cannot add users in demo mode.")

    global firestore_db

    if not firestore_db:
        raise HTTPException(status_code=503, detail="Firestore DB client not initialized.")

    try:
        # 1. Get current account data
        account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id)
        account_doc = await asyncio.to_thread(account_doc_ref.get)
        if not account_doc.exists:
            raise HTTPException(status_code=404, detail="Account not found.")

        account_data = account_doc.to_dict()
        num_users_allowed = account_data.get("num_users_allowed", 1)

        # Count existing AAC users under this account
        users_collection_ref = account_doc_ref.collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
        existing_users = await asyncio.to_thread(users_collection_ref.stream)
        current_user_count = len(list(existing_users))

        # 2. Auto-upgrade if limit reached (increment by 1)
        if current_user_count >= num_users_allowed:
            new_user_limit = num_users_allowed + 1
            await asyncio.to_thread(account_doc_ref.update, {
                "num_users_allowed": new_user_limit,
                "last_updated": dt.now().isoformat()
            })
            logging.info(f"Auto-upgraded account '{account_id}' user limit from {num_users_allowed} to {new_user_limit}.")

        # 3. Generate a new unique ID for the AAC user
        new_aac_user_id = str(uuid.uuid4())

        # 3. Initialize the new AAC user's profile
        await _initialize_new_aac_user_profile(
            account_id=account_id,
            aac_user_id=new_aac_user_id,
            display_name=request_data.display_name
        )

        logging.info(f"New AAC user '{new_aac_user_id}' ('{request_data.display_name}') added to account '{account_id}'.")
        return JSONResponse(content={
            "message": "New AAC user added successfully.",
            "aac_user_id": new_aac_user_id,
            "display_name": request_data.display_name
        }, status_code=201)

    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error adding new AAC user to account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add AAC user: {e}")


@app.put("/api/account/edit-user-display-name")
async def edit_user_display_name(
    request_data: EditUserDisplayNameRequest,
    token_info: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]
):
    account_id = token_info["account_id"]
    user_email = token_info.get("email", "")
    
    # Demo mode restriction (non-breaking for Flutter)
    # Only demoreadonly is restricted, demo@ can make changes for content creation
    is_demo_account = user_email in ["demoreadonly@talkwithbravo.com"]
    if is_demo_account:
        raise HTTPException(status_code=403, detail="Cannot edit users in demo mode.")
    
    global firestore_db
    if not firestore_db:
        raise HTTPException(status_code=503, detail="Firestore DB client not initialized.")

    try:
        # Check if the AAC user exists under this account
        aac_user_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION).document(request_data.aac_user_id)
        aac_user_doc = await asyncio.to_thread(aac_user_doc_ref.get)

        if not aac_user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found in this account.")

        # Update the display name
        await asyncio.to_thread(aac_user_doc_ref.update, {
            "display_name": request_data.new_display_name,
            "last_updated": dt.now().isoformat()
        })

        logging.info(f"Updated display name for AAC user '{request_data.aac_user_id}' to '{request_data.new_display_name}' under account '{account_id}'.")
        
        return JSONResponse(content={
            "message": "Display name updated successfully.",
            "aac_user_id": request_data.aac_user_id,
            "new_display_name": request_data.new_display_name
        })

    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error updating display name for AAC user {request_data.aac_user_id} under account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update display name: {e}")


@app.delete("/api/account/delete-user")
async def delete_user_account(
    request_data: DeleteUserRequest,
    token_info: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]
):
    account_id = token_info["account_id"]
    user_email = token_info.get("email", "")
    
    # Demo mode restriction (non-breaking for Flutter)
    # Only demoreadonly is restricted, demo@ can make changes for content creation
    is_demo_account = user_email in ["demoreadonly@talkwithbravo.com"]
    if is_demo_account:
        raise HTTPException(status_code=403, detail="Cannot delete users in demo mode.")
    
    global firestore_db
    if not firestore_db:
        raise HTTPException(status_code=503, detail="Firestore DB client not initialized.")

    try:
        # 1. Check if the AAC user exists under this account
        aac_user_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION).document(request_data.aac_user_id)
        aac_user_doc = await asyncio.to_thread(aac_user_doc_ref.get)

        if not aac_user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found in this account.")

        # 2. Check if this is the last user (prevent deletion of last user)
        users_collection_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
        existing_users = await asyncio.to_thread(users_collection_ref.stream)
        current_user_count = len(list(existing_users))

        if current_user_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last user account. At least one user must remain.")

        # 3. Delete all data for this AAC user
        # Delete all subcollections under the AAC user document
        await asyncio.to_thread(_delete_collection, aac_user_doc_ref.collection('config'))
        await asyncio.to_thread(_delete_collection, aac_user_doc_ref.collection('info'))
        await asyncio.to_thread(_delete_collection, aac_user_doc_ref.collection('diary_entries'))
        await asyncio.to_thread(_delete_collection, aac_user_doc_ref.collection('chat_history'))
        await asyncio.to_thread(_delete_collection, aac_user_doc_ref.collection('button_activity_log'))
        
        # Delete the AAC user document itself
        await asyncio.to_thread(aac_user_doc_ref.delete)

        logging.info(f"Deleted AAC user '{request_data.aac_user_id}' and all associated data under account '{account_id}'.")
        
        return JSONResponse(content={
            "message": "User account deleted successfully.",
            "deleted_aac_user_id": request_data.aac_user_id
        })

    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error deleting AAC user {request_data.aac_user_id} under account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete user account: {e}")


@app.post("/api/account/copy-user")
async def copy_user_account(
    request_data: CopyUserRequest,
    token_info: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]
):
    account_id = token_info["account_id"]
    user_email = token_info.get("email", "")
    
    # Demo mode restriction (non-breaking for Flutter)
    # Only demoreadonly is restricted, demo@ can make changes for content creation
    is_demo_account = user_email in ["demoreadonly@talkwithbravo.com"]
    if is_demo_account:
        raise HTTPException(status_code=403, detail="Cannot copy users in demo mode.")
    
    global firestore_db
    if not firestore_db:
        raise HTTPException(status_code=503, detail="Firestore DB client not initialized.")

    try:
        # 1. Verify the source user exists
        source_user_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION).document(request_data.source_aac_user_id)
        source_user_doc = await asyncio.to_thread(source_user_doc_ref.get)

        if not source_user_doc.exists:
            raise HTTPException(status_code=404, detail="Source user not found in this account.")

        # 2. Check and auto-upgrade user limit if needed (same as add-aac-user)
        account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id)
        account_doc = await asyncio.to_thread(account_doc_ref.get)
        
        if not account_doc.exists:
            raise HTTPException(status_code=404, detail="Account not found.")

        account_data = account_doc.to_dict()
        num_users_allowed = account_data.get("num_users_allowed", 1)

        # Count existing AAC users under this account
        users_collection_ref = account_doc_ref.collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
        existing_users = await asyncio.to_thread(users_collection_ref.stream)
        current_user_count = len(list(existing_users))

        # Auto-upgrade if limit reached (increment by 1)
        if current_user_count >= num_users_allowed:
            new_user_limit = num_users_allowed + 1
            await asyncio.to_thread(account_doc_ref.update, {
                "num_users_allowed": new_user_limit,
                "last_updated": dt.now().isoformat()
            })
            logging.info(f"Auto-upgraded account '{account_id}' user limit from {num_users_allowed} to {new_user_limit} for user copy.")

        # 3. Generate a new unique ID for the copied AAC user
        new_aac_user_id = str(uuid.uuid4())

        # 4. Initialize the new AAC user's profile (this creates the basic structure)
        await _initialize_new_aac_user_profile(
            account_id=account_id,
            aac_user_id=new_aac_user_id,
            display_name=request_data.new_display_name
        )

        # 5. Copy all data from source user to new user
        await _copy_user_data(account_id, request_data.source_aac_user_id, new_aac_user_id)

        logging.info(f"Copied AAC user '{request_data.source_aac_user_id}' to new user '{new_aac_user_id}' ('{request_data.new_display_name}') under account '{account_id}'.")
        
        return JSONResponse(content={
            "message": "User profile copied successfully.",
            "new_aac_user_id": new_aac_user_id,
            "new_display_name": request_data.new_display_name,
            "source_aac_user_id": request_data.source_aac_user_id
        }, status_code=201)

    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error copying AAC user {request_data.source_aac_user_id} under account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to copy user account: {e}")


async def _copy_user_data(account_id: str, source_user_id: str, target_user_id: str):
    """Copy all user data from source user to target user using the helper functions"""
    global firestore_db
    
    # Use the existing helper functions to load and save data properly
    # This ensures we use the same logic as the rest of the application
    
    try:
        # 1. Copy settings (config/app_settings)
        source_settings = await load_settings_from_file(account_id, source_user_id)
        await save_settings_to_file(account_id, target_user_id, source_settings)
        logging.info(f"Copied settings from {source_user_id} to {target_user_id}")
        
        # 2. Copy birthdays (info/birthdays)
        source_birthdays = await load_birthdays_from_file(account_id, source_user_id)
        await save_birthdays_to_file(account_id, target_user_id, source_birthdays)
        logging.info(f"Copied birthdays from {source_user_id} to {target_user_id}")
        
        # 3. Copy pages (config/pages_list)
        source_pages = await load_pages_from_file(account_id, source_user_id)
        await save_pages_to_file(account_id, target_user_id, source_pages)
        logging.info(f"Copied pages from {source_user_id} to {target_user_id}")
        
        # 4. Copy user info narrative (info/user_narrative)
        source_user_info = await load_firestore_document(
            account_id=account_id,
            aac_user_id=source_user_id,
            doc_subpath="info/user_narrative",
            default_data={"narrative": ""}
        )
        await save_firestore_document(
            account_id=account_id,
            aac_user_id=target_user_id,
            doc_subpath="info/user_narrative",
            data_to_save=source_user_info
        )
        logging.info(f"Copied user narrative from {source_user_id} to {target_user_id}")
        
        # 5. Copy current state (info/current_state)
        source_current_state = await load_firestore_document(
            account_id=account_id,
            aac_user_id=source_user_id,
            doc_subpath="info/current_state",
            default_data=DEFAULT_USER_CURRENT.copy()
        )
        await save_firestore_document(
            account_id=account_id,
            aac_user_id=target_user_id,
            doc_subpath="info/current_state",
            data_to_save=source_current_state
        )
        logging.info(f"Copied current state from {source_user_id} to {target_user_id}")
        
        # 6. Copy scraping config (config/scraping_config)
        source_scraping_config = await load_firestore_document(
            account_id=account_id,
            aac_user_id=source_user_id,
            doc_subpath="config/scraping_config",
            default_data={"news_sources": [], "sports_sources": [], "entertainment_sources": []}
        )
        await save_firestore_document(
            account_id=account_id,
            aac_user_id=target_user_id,
            doc_subpath="config/scraping_config",
            data_to_save=source_scraping_config
        )
        logging.info(f"Copied scraping config from {source_user_id} to {target_user_id}")
        
        # 6.5. Copy new favorites config (config/favorites_config)
        source_favorites_config = await load_firestore_document(
            account_id=account_id,
            aac_user_id=source_user_id,
            doc_subpath="config/favorites_config",
            default_data=DEFAULT_FAVORITES_CONFIG.copy()
        )
        await save_firestore_document(
            account_id=account_id,
            aac_user_id=target_user_id,
            doc_subpath="config/favorites_config",
            data_to_save=source_favorites_config
        )
        logging.info(f"Copied favorites config from {source_user_id} to {target_user_id}")
        
        # 7. Copy audio config (config/audio_config)
        source_audio_config = await load_firestore_document(
            account_id=account_id,
            aac_user_id=source_user_id,
            doc_subpath="config/audio_config",
            default_data={"personal_device": None, "system_device": None}
        )
        await save_firestore_document(
            account_id=account_id,
            aac_user_id=target_user_id,
            doc_subpath="config/audio_config",
            data_to_save=source_audio_config
        )
        logging.info(f"Copied audio config from {source_user_id} to {target_user_id}")
        
        # 8. Copy diary entries (diary_entries collection)
        source_diary_entries = await load_diary_entries(account_id, source_user_id)
        if source_diary_entries:
            await save_diary_entries(account_id, target_user_id, source_diary_entries)
            logging.info(f"Copied {len(source_diary_entries)} diary entries from {source_user_id} to {target_user_id}")
        
        # 9. Copy chat history (chat_history collection)
        source_chat_history = await load_chat_history(account_id, source_user_id)
        if source_chat_history:
            await save_chat_history(account_id, target_user_id, source_chat_history)
            logging.info(f"Copied {len(source_chat_history)} chat history entries from {source_user_id} to {target_user_id}")
        
        # 10. Copy button activity log (button_activity_log collection)
        source_activity_log = await load_button_activity_log(account_id, source_user_id)
        if source_activity_log:
            await save_button_activity_log(account_id, target_user_id, source_activity_log)
            logging.info(f"Copied {len(source_activity_log)} button activity entries from {source_user_id} to {target_user_id}")
        
        logging.info(f"Successfully copied ALL user data from '{source_user_id}' to '{target_user_id}'")
        
    except Exception as e:
        logging.error(f"Error copying user data from {source_user_id} to {target_user_id}: {e}", exc_info=True)
        raise Exception(f"Failed to copy user data: {e}")


async def _copy_user_data_cross_account(source_account_id: str, source_user_id: str, target_account_id: str, target_user_id: str):
    """Copy all user data from source user in one account to target user in another account"""
    global firestore_db
    
    try:
        # 1. Copy settings (config/app_settings)
        source_settings = await load_settings_from_file(source_account_id, source_user_id)
        await save_settings_to_file(target_account_id, target_user_id, source_settings)
        logging.info(f"Copied settings from {source_account_id}/{source_user_id} to {target_account_id}/{target_user_id}")
        
        # 2. Copy birthdays (info/birthdays)
        source_birthdays = await load_birthdays_from_file(source_account_id, source_user_id)
        await save_birthdays_to_file(target_account_id, target_user_id, source_birthdays)
        logging.info(f"Copied birthdays from {source_account_id}/{source_user_id} to {target_account_id}/{target_user_id}")
        
        # 3. Copy user info (info/user_narrative) - corrected path
        source_user_info = await load_firestore_document(
            account_id=source_account_id,
            aac_user_id=source_user_id,
            doc_subpath="info/user_narrative",
            default_data=DEFAULT_USER_INFO.copy()
        )
        await save_firestore_document(
            account_id=target_account_id,
            aac_user_id=target_user_id,
            doc_subpath="info/user_narrative",
            data_to_save=source_user_info
        )
        logging.info(f"Copied user info from {source_account_id}/{source_user_id} to {target_account_id}/{target_user_id}")
        
        # 5. Copy current state (info/current_state)
        source_current_state = await load_firestore_document(
            account_id=source_account_id,
            aac_user_id=source_user_id,
            doc_subpath="info/current_state",
            default_data=DEFAULT_USER_CURRENT.copy()
        )
        await save_firestore_document(
            account_id=target_account_id,
            aac_user_id=target_user_id,
            doc_subpath="info/current_state",
            data_to_save=source_current_state
        )
        logging.info(f"Copied current state from {source_account_id}/{source_user_id} to {target_account_id}/{target_user_id}")
        
        # 6. Copy scraping config (config/scraping_config)
        source_scraping_config = await load_firestore_document(
            account_id=source_account_id,
            aac_user_id=source_user_id,
            doc_subpath="config/scraping_config",
            default_data={"news_sources": [], "sports_sources": [], "entertainment_sources": []}
        )
        await save_firestore_document(
            account_id=target_account_id,
            aac_user_id=target_user_id,
            doc_subpath="config/scraping_config",
            data_to_save=source_scraping_config
        )
        logging.info(f"Copied scraping config from {source_account_id}/{source_user_id} to {target_account_id}/{target_user_id}")
        
        # 6.5. Copy favorites config (config/favorites_config)
        source_favorites_config = await load_firestore_document(
            account_id=source_account_id,
            aac_user_id=source_user_id,
            doc_subpath="config/favorites_config",
            default_data=DEFAULT_FAVORITES_CONFIG.copy()
        )
        await save_firestore_document(
            account_id=target_account_id,
            aac_user_id=target_user_id,
            doc_subpath="config/favorites_config",
            data_to_save=source_favorites_config
        )
        logging.info(f"Copied favorites config from {source_account_id}/{source_user_id} to {target_account_id}/{target_user_id}")
        
        # 7. Copy audio config (config/audio_config)
        source_audio_config = await load_firestore_document(
            account_id=source_account_id,
            aac_user_id=source_user_id,
            doc_subpath="config/audio_config",
            default_data={"personal_device": None, "system_device": None}
        )
        await save_firestore_document(
            account_id=target_account_id,
            aac_user_id=target_user_id,
            doc_subpath="config/audio_config",
            data_to_save=source_audio_config
        )
        logging.info(f"Copied audio config from {source_account_id}/{source_user_id} to {target_account_id}/{target_user_id}")
        
        # 8. Copy diary entries (diary_entries collection)
        source_diary_entries = await load_diary_entries(source_account_id, source_user_id)
        if source_diary_entries:
            await save_diary_entries(target_account_id, target_user_id, source_diary_entries)
            logging.info(f"Copied {len(source_diary_entries)} diary entries from {source_account_id}/{source_user_id} to {target_account_id}/{target_user_id}")
        
        # 9. Copy chat history (chat_history collection)
        source_chat_history = await load_chat_history(source_account_id, source_user_id)
        if source_chat_history:
            await save_chat_history(target_account_id, target_user_id, source_chat_history)
            logging.info(f"Copied {len(source_chat_history)} chat history entries from {source_account_id}/{source_user_id} to {target_account_id}/{target_user_id}")
        
        # 10. Copy button activity log (button_activity_log collection)
        source_activity_log = await load_button_activity_log(source_account_id, source_user_id)
        if source_activity_log:
            await save_button_activity_log(target_account_id, target_user_id, source_activity_log)
            logging.info(f"Copied {len(source_activity_log)} button activity entries from {source_account_id}/{source_user_id} to {target_account_id}/{target_user_id}")
        
        logging.info(f"Successfully copied ALL user data from '{source_account_id}/{source_user_id}' to '{target_account_id}/{target_user_id}'")
        
    except Exception as e:
        logging.error(f"Error copying user data from {source_account_id}/{source_user_id} to {target_account_id}/{target_user_id}: {e}", exc_info=True)
        raise Exception(f"Failed to copy user data: {e}")



@app.post("/api/user-data/delete-aac-user-profile") # Renamed endpoint for clarity
async def delete_aac_user_profile_endpoint(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    
    # Demo mode restriction (non-breaking for Flutter)
    is_demo_mode = current_ids.get("is_demo_mode", False)
    if is_demo_mode:
        raise HTTPException(status_code=403, detail="Cannot delete user profiles in demo mode.")

    logging.info(f"Request received to delete AAC user profile: {aac_user_id} under account: {account_id}.")

    global firestore_db

    if not firestore_db:
        raise HTTPException(status_code=503, detail="Firestore DB client not initialized.")

    try:
        # 1. Delete ALL Firestore data for this AAC user
        # Path for this individual AAC user's data
        user_base_path_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION).document(aac_user_id)

        # Delete all subcollections under the AAC user document and then the document itself
        await asyncio.to_thread(_delete_collection, user_base_path_ref.collection('config'))
        await asyncio.to_thread(_delete_collection, user_base_path_ref.collection('info'))
        await asyncio.to_thread(_delete_collection, user_base_path_ref.collection('diary_entries'))
        await asyncio.to_thread(_delete_collection, user_base_path_ref.collection('chat_history'))
        await asyncio.to_thread(_delete_collection, user_base_path_ref.collection('button_activity_log'))
        # Delete the AAC user document itself
        await asyncio.to_thread(user_base_path_ref.delete)
        logging.info(f"ALL Firestore data for AAC user '{aac_user_id}' under account '{account_id}' deleted successfully.")

    except Exception as e:
        logging.error(f"Error deleting Firestore data for AAC user {aac_user_id} under account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete Firestore data: {str(e)}")



# --- ADD THIS HELPER FUNCTION if you don't have it somewhere ---
# This is needed for deleting subcollections (Firestore client library doesn't have a direct recursive delete)
async def _delete_collection(coll_ref, batch_size=50):
    docs = await asyncio.to_thread(coll_ref.limit(batch_size).stream)
    deleted = 0
    for doc in docs:
        await asyncio.to_thread(doc.reference.delete)
        deleted = deleted + 1
    if deleted >= batch_size:
        # If there are more documents to delete, call the function recursively
        await _delete_collection(coll_ref, batch_size)


# --- OpenAI Helper Functions ---
async def _generate_openai_content(prompt_text: str, model: str = None) -> str:
    """Generate content using OpenAI API"""
    global openai_client
    
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI client not available.")
    
    if not model:
        model = CHATGPT_PRIMARY_MODEL
    
    try:
        logging.info(f"Sending request to OpenAI model: {model}")
        
        # Determine if this is a GPT-5 model (which has different parameter requirements)
        # GPT-5 models: use max_completion_tokens, temperature fixed at 1.0 (omit parameter)
        # GPT-4o/older: use max_tokens, temperature adjustable (0-2)
        model_lower = model.lower()
        is_gpt5_model = 'gpt-5' in model_lower
        uses_completion_tokens = is_gpt5_model  # GPT-5 models use max_completion_tokens
        
        # Build the base request parameters
        request_params = {
            "model": model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a helpful assistant that generates responses in valid JSON format as requested by the user. Always respond with properly formatted JSON."
                },
                {
                    "role": "user", 
                    "content": prompt_text
                }
            ],
            "response_format": {"type": "json_object"}
        }
        
        # Handle temperature parameter based on model type
        if is_gpt5_model:
            # GPT-5 models only support temperature=1.0 (default), so we omit it
            logging.info(f"GPT-5 model detected: {model} - omitting temperature parameter (defaults to 1.0)")
        else:
            # Older models support adjustable temperature
            request_params["temperature"] = 0.7
            logging.info(f"Using temperature=0.7 for model: {model}")
        
        # Add the appropriate token limit parameter
        if uses_completion_tokens:
            request_params["max_completion_tokens"] = 2000
            logging.info(f"Using max_completion_tokens for GPT-5 model: {model}")
        else:
            request_params["max_tokens"] = 2000
            logging.info(f"Using max_tokens for model: {model}")
        
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            **request_params
        )
        
        # Log full response for debugging
        logging.info(f"OpenAI API response: {response}")
        
        # Check if we have choices and content
        if not response.choices:
            logging.error("OpenAI response has no choices")
            raise Exception("OpenAI response has no choices")
        
        choice = response.choices[0]
        content = choice.message.content
        
        # Check for empty or None content
        if not content:
            logging.error(f"OpenAI returned empty content. Choice: {choice}")
            logging.error(f"Finish reason: {choice.finish_reason}")
            raise Exception("OpenAI returned empty content")
        
        logging.info(f"OpenAI response received (length: {len(content)})")
        return content
        
    except Exception as e:
        logging.error(f"OpenAI API error with model {model}: {e}")
        raise

async def _generate_openai_content_with_fallback(prompt_text: str) -> str:
    """Generate content using OpenAI with fallback to secondary model"""
    try:
        # Try primary ChatGPT model first
        return await _generate_openai_content(prompt_text, CHATGPT_PRIMARY_MODEL)
    except Exception as e:
        logging.warning(f"Primary OpenAI model failed: {e}. Trying fallback...")
        try:
            # Try fallback ChatGPT model
            return await _generate_openai_content(prompt_text, CHATGPT_FALLBACK_MODEL)
        except Exception as e2:
            logging.error(f"Both OpenAI models failed. Primary: {e}, Fallback: {e2}")
            raise HTTPException(status_code=503, detail="OpenAI service unavailable.")

# --- Helper function for Gemini LLM with Context Caching ---
async def _generate_gemini_content_with_caching(
    account_id: str, 
    aac_user_id: str, 
    prompt_text: str, 
    generation_config: Optional[Dict] = None,
    cache_manager: GeminiCacheManager = None,
    user_query_only: Optional[str] = None
) -> str:
    """Generate content using Gemini with context caching and conversation sessions for token savings"""
    
    if not cache_manager:
        # Fallback to non-cached generation
        return await _generate_gemini_content_with_fallback(prompt_text, generation_config)
    
    try:
        # Try to get or create conversation session with cached context
        chat_session = await cache_manager.get_or_create_conversation_session(account_id, aac_user_id)
        
        if chat_session and hasattr(chat_session, 'send_message'):
            # Use conversation session for generation (maintains chat history)
            logging.info(f"Using Gemini chat session for {account_id}/{aac_user_id}")
            
            # CRITICAL: Use user_query_only for token savings when chat session has cached content
            if user_query_only:
                # Add validation for empty user_query_only
                if not user_query_only or not user_query_only.strip():
                    logging.error(f"Empty user_query_only provided for {account_id}/{aac_user_id}")
                    raise ValueError("Empty user query provided")
                
                # Calculate token savings
                full_prompt_tokens = len(prompt_text.split())  # Rough estimate
                user_query_tokens = len(user_query_only.split())  # Rough estimate
                token_savings = full_prompt_tokens - user_query_tokens
                token_savings_percent = (token_savings / full_prompt_tokens) * 100 if full_prompt_tokens > 0 else 0
                
                logging.info(f"TOKEN SAVINGS: Using chat session with cached content for {account_id}/{aac_user_id}")
                logging.info(f"TOKEN SAVINGS: Full context would be ~{full_prompt_tokens} tokens, sending only ~{user_query_tokens} tokens")
                logging.info(f"TOKEN SAVINGS: Estimated savings: ~{token_savings} tokens ({token_savings_percent:.1f}% reduction)")
                logging.info(f"TOKEN SAVINGS: User query preview: {user_query_only[:200]}...")
                
                # Send only the user query - context is cached in the session
                response = await asyncio.to_thread(chat_session.send_message, user_query_only)
            else:
                # Fallback: send full prompt if no user_query_only provided
                logging.info(f"No user_query_only provided, sending full prompt to chat session for {account_id}/{aac_user_id}")
                logging.info(f"Full prompt preview: {prompt_text[:200]}...")
                response = await asyncio.to_thread(chat_session.send_message, prompt_text)
            
            # Update message count
            user_key = cache_manager._get_user_key(account_id, aac_user_id)
            if user_key in cache_manager.conversation_sessions:
                cache_manager.conversation_sessions[user_key]["message_count"] += 1
            
            return response.text.strip()
            
        else:
            # Fallback: Check for cached content references to use with direct model call
            cached_refs = await cache_manager.build_cached_context_references(account_id, aac_user_id)
            
            if cached_refs and user_query_only:
                # Use model with cached content - ONLY send user query for token savings
                try:
                    # Get the cached content reference
                    cached_content_name = cached_refs[0]
                    
                    # Get cached content object and create model with it
                    cached_content = caching.CachedContent.get(cached_content_name)
                    model = genai.GenerativeModel.from_cached_content(cached_content)
                    
                    # Calculate token savings
                    full_prompt_tokens = len(prompt_text.split()) if prompt_text else 100  # Rough estimate
                    user_query_tokens = len(user_query_only.split())  # Rough estimate
                    token_savings = full_prompt_tokens - user_query_tokens
                    token_savings_percent = (token_savings / full_prompt_tokens) * 100 if full_prompt_tokens > 0 else 0
                    
                    logging.info(f"TOKEN SAVINGS: Using cached content for {account_id}/{aac_user_id}")
                    logging.info(f"TOKEN SAVINGS: Full context would be ~{full_prompt_tokens} tokens, sending only ~{user_query_tokens} tokens")
                    logging.info(f"TOKEN SAVINGS: Estimated savings: ~{token_savings} tokens ({token_savings_percent:.1f}% reduction)")
                    
                    # Use the cached content reference in the generation config
                    generation_config_with_cache = generation_config or {}
                    
                    # Try using the cached content name directly in the request
                    response = await asyncio.to_thread(
                        model.generate_content, 
                        user_query_only, 
                        generation_config=generation_config_with_cache
                    )
                    return response.text.strip()
                    
                except Exception as cache_error:
                    logging.warning(f"Failed to use cached content, falling back to regular generation: {cache_error}")
                    return await _generate_gemini_content_with_fallback(prompt_text, generation_config)
            else:
                # No cached content available or no user query provided, use regular generation
                if not user_query_only:
                    logging.info(f"No user_query_only provided, using full prompt for {account_id}/{aac_user_id}")
                else:
                    logging.info(f"No cached content available, using full prompt for {account_id}/{aac_user_id}")
                return await _generate_gemini_content_with_fallback(prompt_text, generation_config)
                
    except Exception as e:
        logging.error(f"Error in cached Gemini generation for {account_id}/{aac_user_id}: {e}")
        # Fallback to non-cached generation
        return await _generate_gemini_content_with_fallback(prompt_text, generation_config)

# --- Helper function for Gemini LLM content generation with fallback ---

async def _generate_gemini_content_with_fallback(prompt_text: str, generation_config: Optional[Dict] = None, account_id: str = "unknown", aac_user_id: str = "unknown") -> str: # <--- THIS LINE IS CRITICAL
    global primary_llm_model_instance, fallback_llm_model_instance

    if not primary_llm_model_instance:
        logging.error("Primary LLM model instance is not initialized.")
        raise HTTPException(status_code=503, detail="Primary LLM not available.")

    async def get_text_from_response(response_obj):
        if hasattr(response_obj, 'text'): return response_obj.text
        if hasattr(response_obj, 'parts') and isinstance(response_obj.parts, list) and response_obj.parts:
            full_content = "".join(part.text for part in response_obj.parts if hasattr(part, 'text'))
            return full_content
        logging.warning(f"Unexpected LLM response structure: {type(response_obj)}. Attempting str().")
        return str(response_obj)

    try:
        # Add validation to ensure prompt_text is not empty
        if not prompt_text or not prompt_text.strip():
            logging.error("Empty or whitespace-only prompt provided to Gemini")
            raise HTTPException(status_code=400, detail="Empty prompt provided to LLM")
        
        logging.info(f"Attempting LLM generation with primary model: {primary_llm_model_instance.model_name}")
        logging.info(f"Prompt length: {len(prompt_text)} characters")
        response = await asyncio.to_thread(primary_llm_model_instance.generate_content, prompt_text, generation_config=generation_config) # <--- THIS CALL
        response_text = (await get_text_from_response(response)).strip()
        
        # Log detailed token usage for non-cached requests
        log_token_usage(response, "NON_CACHED", account_id, aac_user_id)
        
        # Add validation for empty response
        if not response_text:
            logging.error("LLM returned empty response")
            raise HTTPException(status_code=500, detail="LLM returned empty response")
        
        return response_text
    except (google.api_core.exceptions.ResourceExhausted, google.api_core.exceptions.ServiceUnavailable) as e_primary:
        logging.warning(f"Primary LLM ({primary_llm_model_instance.model_name}) failed with {type(e_primary).__name__}: {e_primary}. Attempting fallback.")
        if fallback_llm_model_instance:
            try:
                logging.info(f"Attempting LLM generation with fallback model: {fallback_llm_model_instance.model_name}")
                response_fallback = await asyncio.to_thread(fallback_llm_model_instance.generate_content, prompt_text, generation_config=generation_config) # <--- THIS CALL
                fallback_response_text = (await get_text_from_response(response_fallback)).strip()
                
                # Log detailed token usage for fallback requests
                log_token_usage(response_fallback, "FALLBACK", account_id, aac_user_id)
                
                return fallback_response_text
            except Exception as e_fallback:
                logging.error(f"Fallback LLM ({fallback_llm_model_instance.model_name}) also failed: {e_fallback}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"LLM generation failed with primary and fallback models: {e_fallback}")
        else:
            logging.error("Primary LLM failed and no fallback model configured.", exc_info=True)
            raise HTTPException(status_code=503, detail=f"Primary LLM failed and no fallback available: {e_primary}")
    except Exception as e_other_primary:
        logging.error(f"An unexpected error occurred with primary LLM ({primary_llm_model_instance.model_name}): {e_other_primary}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {e_other_primary}")


@app.options("/llm")
async def options_llm(request: Request):
    print("OPTIONS /llm HEADERS:", dict(request.headers))
    return Response(status_code=200)


@app.get("/api/debug/cache")
async def get_cache_debug_info_endpoint(
    current_ids: Dict[str, str] = Depends(get_current_account_and_user_ids)
):
    """Get detailed cache debug information for the current user."""
    global cache_manager
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    
    debug_info = cache_manager.get_cache_debug_info(account_id, aac_user_id)
    
    return JSONResponse(content={
        "success": True,
        "debug_info": debug_info,
        "timestamp": dt.now().isoformat()
    })


@app.post("/api/cache/refresh")
async def refresh_user_cache(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """Manually invalidates and deletes the cache for the current user."""
    global cache_manager
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    
    await cache_manager.invalidate_cache(account_id, aac_user_id)
    
    return JSONResponse(content={"message": f"Cache invalidated for user {aac_user_id}."})


async def build_full_prompt_for_non_cached_llm(account_id: str, aac_user_id: str, user_query: str) -> str:
    """
    Builds the complete LLM prompt from scratch by fetching all context data.
    This is used as a fallback when a cache is not available.
    """
    # This function reuses the same logic as the cache manager's context builder
    # to ensure consistency between cached and non-cached prompts.
    global cache_manager
    full_context_string = await cache_manager._build_combined_context_string(account_id, aac_user_id, user_query)
    
    # Add advanced randomization prompt for joke generation
    if "joke" in user_query.lower():
        import time
        import hashlib
        
        # Create session-based creativity seeds
        session_id = hashlib.md5(f"{account_id}_{aac_user_id}_{int(time.time() // 300)}".encode()).hexdigest()[:8]
        creativity_seed = hash(f"{session_id}_{time.time()}") % 10000
        
        randomization_prompt = f"""
--- ADVANCED RANDOMIZATION INSTRUCTIONS ---
SESSION_ID: {session_id}
CREATIVITY_SEED: {creativity_seed}

STRICT UNIQUENESS REQUIREMENTS:
1. Analyze the chat history above for ANY previously used jokes, punchlines, or setups
2. Generate jokes that are COMPLETELY different from anything in the chat history
3. Use these 14 diversified comedy focus areas randomly: observational humor, wordplay, puns, absurd situations, unexpected twists, clever one-liners, dad jokes, anti-jokes, surreal comedy, self-deprecating humor, topical humor, physical comedy references, animal humor, and technology humor
4. Each response must use a different comedy style than the previous ones
5. Avoid any similarity to previous content - different topics, different structures, different punchlines

CREATIVITY BOOSTERS:
- Combine unrelated concepts unexpectedly
- Use surprising perspective shifts
- Include contemporary references
- Mix serious and silly elements
- Create unexpected connections between ideas

RESPONSE FORMAT: Generate exactly the requested number of completely unique jokes. Each should be self-contained with setup and punchline, or be a complete one-liner.
"""
        
        full_context_string += randomization_prompt
    
    # Append the specific user query to the full context
    return f"{full_context_string}\n\n--- USER QUERY ---\n{user_query}"


def log_token_usage(response, request_type: str, account_id: str, aac_user_id: str):
    """
    Logs detailed token usage information from Gemini API response.
    This helps track cached vs non-cached token usage for billing analysis.
    """
    try:
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            
            # Extract key metrics
            prompt_tokens = getattr(usage, 'prompt_token_count', 0)
            cached_tokens = getattr(usage, 'cached_content_token_count', 0)
            candidates_tokens = getattr(usage, 'candidates_token_count', 0)
            total_tokens = getattr(usage, 'total_token_count', 0)
            
            # Calculate billable tokens
            new_prompt_tokens = prompt_tokens - cached_tokens
            
            # Calculate savings if using cache
            if cached_tokens > 0:
                cache_savings_percent = (cached_tokens / prompt_tokens) * 100 if prompt_tokens > 0 else 0
                
                logging.info(f"🎯 TOKEN USAGE [{request_type}] - {account_id}/{aac_user_id}:")
                logging.info(f"  📊 Total Request: {prompt_tokens:,} tokens")
                logging.info(f"  🔄 From Cache: {cached_tokens:,} tokens (75% discount)")
                logging.info(f"  💰 New Billable: {new_prompt_tokens:,} tokens (standard rate)")
                logging.info(f"  📝 Response Generated: {candidates_tokens:,} tokens")
                logging.info(f"  📈 Cache Savings: {cache_savings_percent:.1f}% of prompt tokens")
                logging.info(f"  🔢 Total Call: {total_tokens:,} tokens")
            else:
                logging.info(f"🎯 TOKEN USAGE [{request_type}] - {account_id}/{aac_user_id}:")
                logging.info(f"  📊 Prompt: {prompt_tokens:,} tokens (NO CACHE - full billing)")
                logging.info(f"  📝 Response: {candidates_tokens:,} tokens")
                logging.info(f"  🔢 Total: {total_tokens:,} tokens")
                
        else:
            logging.warning(f"No usage_metadata available in response for {account_id}/{aac_user_id}")
            
    except Exception as e:
        logging.error(f"Error logging token usage for {account_id}/{aac_user_id}: {e}")



class LLMRequest(BaseModel):
    prompt: str

# --- LLM Endpoint (MODIFIED RAG Context Processing for user-specificity) ---
@app.post("/llm")
async def get_llm_response_endpoint(
    request_data: LLMRequest, 
    current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]
):
    global cache_manager
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    user_prompt_content = request_data.prompt

    # Get user's settings to determine LLM provider and options
    user_settings = await load_settings_from_file(account_id, aac_user_id)
    llm_provider = user_settings.get("llm_provider", "gemini").lower()
    llm_options_value = user_settings.get("LLMOptions", DEFAULT_LLM_OPTIONS)

    # Check if mood was recently updated and add small delay to prevent race conditions
    global mood_update_timestamps
    user_key = f"{account_id}/{aac_user_id}"
    if user_key in mood_update_timestamps:
        time_since_mood_update = time.time() - mood_update_timestamps[user_key]
        if time_since_mood_update < 2.0:  # Less than 2 seconds ago
            delay_time = 2.0 - time_since_mood_update
            logging.info(f"⏱️ Mood recently updated {time_since_mood_update:.1f}s ago, waiting {delay_time:.1f}s for cache consistency")
            await asyncio.sleep(delay_time)
            # Clear the timestamp after delay
            del mood_update_timestamps[user_key]

    # Replace placeholder in the prompt
    if "#LLMOptions" in user_prompt_content:
        user_prompt_content = user_prompt_content.replace("#LLMOptions", str(llm_options_value))

    # Add randomization for joke generation to increase variety
    if "joke" in user_prompt_content.lower() or "humor" in user_prompt_content.lower():
        import random
        from datetime import datetime
        
        # Create randomization seeds for more variety
        random_seed = random.randint(1, 1000)
        time_seed = datetime.now().strftime("%H%M")
        
        randomization_prompt = f"""
ADVANCED JOKE UNIQUENESS SYSTEM:
- Session ID: {random_seed} - This session must generate completely different jokes from previous sessions
- Time-based creativity seed: {time_seed} - Use this to inspire fresh perspectives and angles
- STRICT RULE: Analyze the chat history thoroughly and absolutely AVOID repeating any:
  * Similar joke setups or premises
  * Punchlines with the same structure or wordplay
  * Topics or subjects already covered recently
  * Comedy styles used in the last several interactions

COMEDY DIVERSITY REQUIREMENTS:
- Session {random_seed} focus: {random.choice(['wordplay and puns', 'observational humor about technology', 'absurd everyday situations', 'clever unexpected twists', 'witty riddles and brain teasers', 'dad joke reversals', 'pop culture mashups', 'scientific humor', 'food-related comedy', 'animal behavior jokes', 'weather and seasons', 'social media humor', 'travel mishaps', 'household object personification'])}
- Secondary style: {random.choice(['anti-jokes', 'meta-humor', 'historical anachronisms', 'minimalist one-liners', 'question-answer format', 'story-based humor', 'comparison comedy', 'hypothetical scenarios'])}
- Avoid these overused topics: knock-knock jokes, chicken crossing roads, lightbulb jokes, doctor/lawyer stereotypes

CREATIVITY BOOSTERS:
- Combine unexpected elements (e.g., medieval knights + modern technology)
- Use current year context (2025) for relevant references
- Create original scenarios rather than rehashing classic setups
- Experiment with timing and surprise elements
- Adapt humor style to be inclusive and engaging for all audiences

"""
        user_prompt_content = randomization_prompt + user_prompt_content

    # Define generation config and add JSON formatting instructions  
    generation_config = {"response_mime_type": "application/json", "temperature": 0.9}  # Increased temperature for more creativity
    json_format_instructions = """
CRITICAL: Format your response as a JSON list where each item has "option" and "summary" keys.
If the generated option is more than 5 words, the "summary" key should be a 3-5 word abbreviation of each option, including the exact key words from the option. If the option is 5 words or less, the "summary" key should contain the exact same FULL text as the "option" key.
The "option" key should contain the FULL option text.
IMPORTANT FOR JOKES: If generating jokes, ALWAYS include both the question AND punchline in the SAME "option". Format them as: "Question? Punchline!"

⚠️ CRITICAL SUMMARY RULE: NEVER include the user's name in the "summary" field. The summary is what the user will hear when the option is spoken aloud. Remove any personal names from summaries and use generic language instead. For example, if the option is "Jon is excited to learn", the summary should be "Excited to learn", not "Jon excited to learn".

Return ONLY valid JSON - no other text before or after the JSON array."""
    final_user_query = f"{user_prompt_content}\n\n{json_format_instructions}"

    llm_response_json_str = ""

    # --- Route to appropriate LLM ---
    if llm_provider == "chatgpt":
        logging.info(f"Using OpenAI for {account_id}/{aac_user_id}. Building full prompt manually.")
        full_prompt_for_openai = await build_full_prompt_for_non_cached_llm(account_id, aac_user_id, final_user_query)
        llm_response_json_str = await _generate_openai_content_with_fallback(full_prompt_for_openai)
    else:
        # --- Gemini Cache-First Approach ---
        logging.info(f"Using Gemini with caching for {account_id}/{aac_user_id}.")
        cached_content_ref = await cache_manager.get_cached_content_reference(account_id, aac_user_id)

        if cached_content_ref:
            try:
                model = genai.GenerativeModel.from_cached_content(cached_content_ref)
                response = await asyncio.to_thread(
                    model.generate_content, final_user_query, generation_config=generation_config
                )
                llm_response_json_str = response.text.strip()
                
                # Log detailed token usage for cached requests
                log_token_usage(response, "CACHED", account_id, aac_user_id)
                
                logging.info(f"Successfully generated content using cached reference for {account_id}/{aac_user_id}.")
            except Exception as e:
                logging.error(f"Error using cached content for {account_id}/{aac_user_id}: {e}. Falling back.")
                full_prompt = await build_full_prompt_for_non_cached_llm(account_id, aac_user_id, final_user_query)
                llm_response_json_str = await _generate_gemini_content_with_fallback(full_prompt, generation_config, account_id, aac_user_id)
        else:
            logging.warning(f"No valid cache found for {account_id}/{aac_user_id}. Attempting to warm up cache...")
            
            # Try to warm up cache before falling back to full prompt
            try:
                await cache_manager.warm_up_user_cache_if_needed(account_id, aac_user_id)
                
                # Check if cache was created
                cached_content_ref = await cache_manager.get_cached_content_reference(account_id, aac_user_id)
                
                if cached_content_ref:
                    # Cache was successfully created, use it
                    model = genai.GenerativeModel.from_cached_content(cached_content_ref)
                    response = await asyncio.to_thread(
                        model.generate_content, final_user_query, generation_config=generation_config
                    )
                    llm_response_json_str = response.text.strip()
                    
                    # Log detailed token usage for newly cached requests
                    log_token_usage(response, "NEW_CACHE", account_id, aac_user_id)
                    
                    logging.info(f"Successfully generated content using newly created cache for {account_id}/{aac_user_id}.")
                else:
                    # Cache creation failed, use full prompt fallback
                    logging.warning(f"Cache creation failed for {account_id}/{aac_user_id}. Using full prompt fallback.")
                    full_prompt = await build_full_prompt_for_non_cached_llm(account_id, aac_user_id, final_user_query)
                    llm_response_json_str = await _generate_gemini_content_with_fallback(full_prompt, generation_config, account_id, aac_user_id)
                    
            except Exception as warmup_error:
                logging.error(f"Cache warmup failed for {account_id}/{aac_user_id}: {warmup_error}. Using full prompt fallback.")
                full_prompt = await build_full_prompt_for_non_cached_llm(account_id, aac_user_id, final_user_query)
                llm_response_json_str = await _generate_gemini_content_with_fallback(full_prompt, generation_config, account_id, aac_user_id)
    
    logging.info(f"--- LLM Final JSON Response Text for account {account_id} and user {aac_user_id} (Length: {len(llm_response_json_str)}) ---")

    def extract_json_from_response(response_text: str) -> str:
        """Extract JSON from LLM response, handling markdown code blocks"""
        response_text = response_text.strip()
        if response_text.startswith('```json') and response_text.endswith('```'):
            return '\n'.join(response_text.split('\n')[1:-1]).strip()
        if response_text.startswith('```') and response_text.endswith('```'):
            return '\n'.join(response_text.split('\n')[1:-1]).strip()
        return response_text

    clean_json_str = extract_json_from_response(llm_response_json_str)
    logging.info(f"--- Extracted clean JSON for account {account_id} and user {aac_user_id} (Clean length: {len(clean_json_str)}) ---")

    try:
        parsed_llm_output = json.loads(clean_json_str)
        
        extracted_options_list = []
        if isinstance(parsed_llm_output, dict):
            for key, value in parsed_llm_output.items():
                if isinstance(value, list):
                    extracted_options_list = value
                    logging.info(f"Extracted list from LLM response dictionary using key: '{key}'")
                    break
            if not extracted_options_list:
                logging.warning(f"LLM returned a dictionary but no inner list of options found: {parsed_llm_output.keys()}")
                raise HTTPException(status_code=500, detail="LLM response was a dictionary but contained no list of options.")
        elif isinstance(parsed_llm_output, list):
            extracted_options_list = parsed_llm_output
        else:
            logging.error(f"LLM returned unexpected top-level type: {type(parsed_llm_output)} - Content: {llm_response_json_str}")
            raise HTTPException(status_code=500, detail="LLM response was not valid (not a list or a dict containing a list).")

        if not isinstance(extracted_options_list, list):
            logging.error(f"Logic Error: After processing, extracted LLM options were not a list: {type(extracted_options_list)} - Content: {llm_response_json_str}")
            raise HTTPException(status_code=500, detail="Internal server error: Failed to extract LLM options as a list.")

        return JSONResponse(content=extracted_options_list)

    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse LLM response as JSON: {e}. Clean Raw: {clean_json_str[:500]}...", exc_info=True)
        raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON: {str(e)}")
    except Exception as e:
        logging.error(f"Error processing LLM response for account {account_id} and user {aac_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing LLM response: {str(e)}")




# --- Initialization Function (MODIFIED) ---
def initialize_backend_services():
    global sentence_transformer_model, primary_llm_model_instance, fallback_llm_model_instance, tts_client
    global firestore_db
    global firebase_app

    try:
        # --- NEW DEBUGGING LOGS (TEMPORARY - can remove these lines once stable) ---
        logging.info(f"DEBUG: Checking path: {SERVICE_ACCOUNT_KEY_PATH}")
        logging.info(f"DEBUG: Does SERVICE_ACCOUNT_KEY_PATH exist? {os.path.exists(SERVICE_ACCOUNT_KEY_PATH)}")
        logging.info(f"DEBUG: Is SERVICE_ACCOUNT_KEY_PATH a file? {os.path.isfile(SERVICE_ACCOUNT_KEY_PATH)}")
        mount_dir = os.path.dirname(SERVICE_ACCOUNT_KEY_PATH)
        logging.info(f"DEBUG: Listing contents of mount directory: {mount_dir}")
        try:
            if os.path.exists(mount_dir) and os.path.isdir(mount_dir):
                logging.info(f"DEBUG: Contents of {mount_dir}: {os.listdir(mount_dir)}")
            else:
                logging.warning(f"DEBUG: Mount directory {mount_dir} does not exist or is not a directory.")
        except Exception as list_e:
            logging.error(f"DEBUG: Error listing mount directory {mount_dir}: {list_e}")
        try:
            with open(SERVICE_ACCOUNT_KEY_PATH, 'rb') as f:
                first_bytes = f.read(50) # Read first 50 bytes
                logging.info(f"DEBUG: First 50 bytes of credential file: {first_bytes!r}")
        except FileNotFoundError:
            logging.warning(f"DEBUG: Credential file {SERVICE_ACCOUNT_KEY_PATH} not found for reading test.")
        except Exception as read_e:
            logging.error(f"DEBUG: Error reading credential file {SERVICE_ACCOUNT_KEY_PATH}: {read_e}")
        # --- END DEBUGGING LOGS ---

        # --- Explicitly Load Credentials (MODIFIED, this is the crucial part) ---
        service_account_credentials_gcp = None  # For Google Cloud clients (Firestore, TTS)
        firebase_admin_cert_data = None         # NEW: To hold the raw JSON dictionary for Firebase Admin

        if os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
            try:
                # Load for Google Cloud clients (Firestore, TTS)
                service_account_credentials_gcp = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY_PATH)
                logging.info(f"Google Cloud service account credentials loaded explicitly from {SERVICE_ACCOUNT_KEY_PATH}.")

                # Load for Firebase Admin SDK (requires raw JSON content, direct from file)
                with open(SERVICE_ACCOUNT_KEY_PATH, 'r') as f:
                    firebase_admin_cert_data = json.load(f) # Directly load the JSON into a dictionary
                logging.info("Firebase Admin SDK certificate JSON data loaded.")

            except Exception as e:
                logging.error(f"Error loading service account credentials from file {SERVICE_ACCOUNT_KEY_PATH}: {e}", exc_info=True)
                service_account_credentials_gcp = None
                firebase_admin_cert_data = None # Ensure it's None on failure
        else:
            logging.warning(f"Service account key file not found at {SERVICE_ACCOUNT_KEY_PATH}. Proceeding with Application Default Credentials as fallback where applicable (might fail).")


        # --- Initialize Cloud Firestore client (UNCHANGED from last attempt) ---
        logging.info("Initializing Cloud Firestore client...")
        try:
            if service_account_credentials_gcp:
                firestore_db = FirestoreClient(credentials=service_account_credentials_gcp)
                logging.info("Cloud Firestore client initialized successfully with explicit credentials.")
            else:
                firestore_db = FirestoreClient() # Fallback
                logging.warning("Cloud Firestore client initialized using Application Default Credentials (explicit credentials not found).")
        except Exception as e:
            logging.error(f"Error initializing Cloud Firestore client: {e}", exc_info=True)
            firestore_db = None

        # --- Initialize Google Cloud Text-to-Speech client (UNCHANGED from last attempt) ---
        logging.info("Initializing Google Cloud Text-to-Speech client...")
        try:
            if service_account_credentials_gcp:
                tts_client = google_tts.TextToSpeechClient(credentials=service_account_credentials_gcp)
                logging.info("Google Cloud Text-to-Speech client initialized successfully with explicit credentials.")
            else:
                tts_client = google_tts.TextToSpeechClient() # Fallback
                logging.warning("Google Cloud Text-to-Speech client initialized using Application Default Credentials (explicit credentials not found).")
        except Exception as e:
            logging.error(f"Error initializing Google Cloud Text-to-Speech client: {e}", exc_info=True)
            tts_client = None


         # --- Initialize Firebase Admin SDK (MODIFIED) ---
        logging.info("Initializing Firebase Admin SDK...")
        try:
            if not firebase_admin._apps:
                if firebase_admin_cert_data:
                    # Use explicit credentials for Firebase Admin SDK
                    cred = credentials.Certificate(firebase_admin_cert_data)
                    firebase_app = firebase_admin.initialize_app(cred)
                    logging.info("Firebase Admin SDK initialized successfully with explicit credentials.")
                else:
                    # Fallback to ApplicationDefaultCredentials if explicit loading failed.
                    # This is the path that was failing before, so it's a weak fallback.
                    cred = credentials.ApplicationDefault()
                    firebase_app = firebase_admin.initialize_app(cred)
                    logging.warning("Firebase Admin SDK initialized using Application Default Credentials (explicit credentials not found).")
            else:
                firebase_app = firebase_admin.get_app()
                logging.info("Firebase Admin SDK already initialized.")
        except Exception as e:
            logging.error(f"Error initializing Firebase Admin SDK: {e}", exc_info=True)
            firebase_app = None

        logging.info("All shared backend services initialized successfully.")

    except Exception as e:
        logging.error(f"FATAL: Error initializing shared backend services: {e}", exc_info=True)
        # If services initialized *within this function* fail, set them to None.
        # Models (SentenceTransformer, LLM) are initialized at module level and their
        # status should not be changed here.
        tts_client = None
        
        firestore_db = None
        firebase_app = None




# --- Firestore Helper Functions ---
async def load_firestore_document(account_id: str, aac_user_id: str, doc_subpath: str, default_data: Any) -> Any:
    """
    Loads a document from Firestore for a specific AAC user under an account,
    returning a copy of default_data on error/missing.
    doc_subpath example: "settings/app_settings", "info/birthdays"
    """
    global firestore_db
    if not firestore_db:
        logging.error(f"Firestore DB client not initialized. Cannot load document for AAC user {aac_user_id}.")
        return default_data.copy() if isinstance(default_data, (dict, list)) else default_data

    full_path = f"{FIRESTORE_ACCOUNTS_COLLECTION}/{account_id}/{FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION}/{aac_user_id}/{doc_subpath}"
    doc_ref = firestore_db.document(full_path)
    try:
        doc = await asyncio.to_thread(doc_ref.get)
        if doc.exists:
            data_from_db = doc.to_dict()
            logging.info(f"Loaded Firestore document from {full_path} for AAC user {aac_user_id}.")
            
            # Handle JSON string format for pages data
            if doc_subpath == "config/pages_list" and "pages_json" in data_from_db:
                import json
                try:
                    pages_data = json.loads(data_from_db["pages_json"])
                    logging.info(f"Successfully parsed pages JSON data for AAC user {aac_user_id}.")
                    return pages_data
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse pages JSON data for AAC user {aac_user_id}: {e}")
                    return default_data.copy() if isinstance(default_data, (dict, list)) else default_data
            
            if isinstance(default_data, dict) and isinstance(data_from_db, dict):
                merged_data = default_data.copy()
                merged_data.update(data_from_db) # Merge with defaults
                return merged_data
            elif isinstance(default_data, list) and isinstance(data_from_db, list):
                return data_from_db # Return the list as is
            else:
                logging.warning(f"Type mismatch for Firestore document at {full_path} for AAC user {aac_user_id}. Expected {type(default_data)}, got {type(data_from_db)}. Returning default.")
                return default_data.copy() if isinstance(default_data, (dict, list)) else default_data
        else:
            logging.warning(f"Firestore document at {full_path} not found for AAC user {aac_user_id}. Using and saving defaults.")
            await save_firestore_document(account_id, aac_user_id, doc_subpath, default_data)
            return default_data.copy() if isinstance(default_data, (dict, list)) else default_data
    except Exception as e:
        logging.error(f"Error loading Firestore document from {full_path} for AAC user {aac_user_id}: {e}", exc_info=True)
        return default_data.copy() if isinstance(default_data, (dict, list)) else default_data

def sanitize_for_firestore(data):
    """
    Recursively sanitize data to ensure it's compatible with Firestore.
    Firestore has restrictions on nested objects and certain data types.
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Convert keys to strings and sanitize values
            sanitized[str(key)] = sanitize_for_firestore(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_for_firestore(item) for item in data]
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    else:
        # Convert any other type to string representation
        return str(data)

async def save_firestore_document(account_id: str, aac_user_id: str, doc_subpath: str, data_to_save: Any) -> bool:
    """
    Saves data to a Firestore document for a specific AAC user under an account.
    doc_subpath example: "settings/app_settings", "info/birthdays"
    """
    global firestore_db
    if not firestore_db:
        logging.error(f"Firestore DB client not initialized. Cannot save document for AAC user {aac_user_id}.")
        return False
    try:
        # For complex nested data like pages, store as JSON string to avoid Firestore nested entity limits
        if doc_subpath == "config/pages_list":
            # Convert to JSON string for pages data
            import json
            json_data = {
                "pages_json": json.dumps(data_to_save, ensure_ascii=False, default=str),
                "last_updated": firestore.SERVER_TIMESTAMP
            }
            logging.info(f"Saving pages data as JSON string. Original data type: {type(data_to_save)}")
            data_to_store = json_data
        else:
            # Sanitize the data before saving to Firestore for other documents
            data_to_store = sanitize_for_firestore(data_to_save)
        
        full_path = f"{FIRESTORE_ACCOUNTS_COLLECTION}/{account_id}/{FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION}/{aac_user_id}/{doc_subpath}"
        doc_ref = firestore_db.document(full_path)
        await asyncio.to_thread(doc_ref.set, data_to_store) # Use .set() to overwrite or create
        logging.info(f"Saved Firestore document to {full_path} for AAC user {aac_user_id}.")
        return True
    except Exception as e:
        logging.error(f"Error saving Firestore document to {full_path} for AAC user {aac_user_id}: {e}", exc_info=True)
        return False

async def load_firestore_collection(account_id: str, aac_user_id: str, collection_subpath: str) -> List[Dict]:
    """
    Loads a collection from Firestore for a specific AAC user under an account.
    collection_subpath example: "diary_entries", "chat_history"
    """
    global firestore_db
    if not firestore_db:
        logging.error(f"Firestore DB client not initialized. Cannot load collection for AAC user {aac_user_id}.")
        return []
    try:
        full_path = f"{FIRESTORE_ACCOUNTS_COLLECTION}/{account_id}/{FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION}/{aac_user_id}/{collection_subpath}"
        collection_ref = firestore_db.collection(full_path)
        docs = await asyncio.to_thread(collection_ref.stream)
        entries = []
        for doc in docs:
            entry_data = doc.to_dict()
            if entry_data: # Ensure doc.to_dict() didn't return None if doc data is empty/malformed
                entry_data['id'] = doc.id # Add the document ID
                entries.append(entry_data)
        logging.info(f"Loaded {len(entries)} documents from Firestore collection {full_path} for AAC user {aac_user_id}.")
        return entries
    except Exception as e:
        logging.error(f"Error loading Firestore collection from {full_path} for AAC user {aac_user_id}: {e}", exc_info=True)
        return []

async def save_firestore_collection_items(account_id: str, aac_user_id: str, collection_subpath: str, items: List[Dict]) -> bool:
    """
    Saves the list of items to a Firestore subcollection for a specific AAC user under an account.
    This overwrites existing documents based on ID or creates new ones.
    collection_subpath example: "diary_entries", "chat_history"
    """
    global firestore_db
    if not firestore_db:
        logging.error(f"Firestore DB client not initialized. Cannot save collection for AAC user {aac_user_id}.")
        return False
    


    full_path = f"{FIRESTORE_ACCOUNTS_COLLECTION}/{account_id}/{FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION}/{aac_user_id}/{collection_subpath}"
    collection_ref = firestore_db.collection(full_path)
    try:
        # It's better to delete and re-add for small collections like chat/diary,
        # or use batch writes for efficiency/atomicity if many updates.
        # For now, we'll keep the existing delete-all-then-add logic.
        existing_docs = await asyncio.to_thread(collection_ref.stream)
        for doc in existing_docs:
            await asyncio.to_thread(doc.reference.delete)

        for item in items:
            doc_id = item.get('id') if item.get('id') else str(uuid.uuid4())
            await asyncio.to_thread(collection_ref.document(doc_id).set, item)

        logging.info(f"Saved {len(items)} documents to Firestore collection {full_path} for AAC user {aac_user_id}.")
        return True
    except Exception as e:
        logging.error(f"Error saving Firestore collection to {full_path} for AAC user {aac_user_id}: {e}", exc_info=True)
        return False


# --- API Endpoints for User Info & Current State (MODIFIED to update ChromaDB) ---
class UserInfoNarrative(BaseModel): narrative: str
class UserCurrentState(BaseModel): location: Optional[str] = ""; people: Optional[str] = ""; activity: Optional[str] = ""



# --- FastAPI Lifespan Context Manager (Replaces @app.on_event) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    logging.info("Application startup: Initializing shared backend services...")
    initialize_backend_services() # This now only initializes global, shared items
    # REMOVE THESE:
    # load_settings_from_file() # Settings loaded per user now
    # load_birthdays_from_file() # Birthdays loaded per user now
    logging.info("Startup complete (shared services).")
    yield
    # Code to run on shutdown (optional)
    logging.info("Application shutdown.")

# Assign the lifespan manager to the FastAPI app instance
app.router.lifespan_context = lifespan




# /get-user-info
@app.get("/get-user-info", response_model=UserInfoNarrative)
async def get_user_info_endpoint(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]): # ADD user_id
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    user_info_content_dict = await load_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="info/user_narrative",
        default_data=DEFAULT_USER_INFO.copy() # Use the global default dict
    )
    return JSONResponse(content={"narrative": user_info_content_dict.get("narrative", "")})



# /update-user-info
@app.post("/update-user-info")
async def update_user_info_endpoint(payload: UserInfoNarrative, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    narrative = payload.narrative
    success = await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="info/user_narrative",
        data_to_save={"narrative": narrative} 
    )
    
    # Cache invalidation for user info changes
    if success:
        await cache_manager.invalidate_cache(account_id, aac_user_id)
    
    return {"success": success}


@app.get("/get-user-favorites")
async def get_user_favorites(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """
    Returns all user favorites (scraping configurations) from Firestore.
    """
    account_id = current_ids["account_id"]
   
    aac_user_id = current_ids["aac_user_id"]

    # Call the existing, correct Firestore-based function
    config = await load_dynamic_scraping_config(account_id, aac_user_id)
    if not config:
        raise HTTPException(status_code=500, detail="User favorites (scraping configuration) could not be loaded for this user.")
    return JSONResponse(content=config)


@app.post("/update-user-favorites")
async def update_user_favorites(request: Request, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """
    Updates user favorites (scraping configurations) in Firestore based on the request data.
    """
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]

    # The incoming request.json() should directly provide the structure for scraping_config.
    # Assuming frontend sends {"news_sources": [...], "sports_sources": [...], "entertainment_sources": [...]}.
    # If frontend sends {"news": [...], "sports": [...], "entertainment": [...]} as in your current code,
    # you'll need to re-map the keys or update the frontend to send the correct keys.
    # Let's assume for now the frontend is sending keys like "news_sources", "sports_sources" etc.
    # If not, the `post_scraping_config` endpoint is already set up to validate the structure.
    # For simplicity, we can pass the raw data, and `save_dynamic_scraping_config` will handle validation.

    incoming_config_data = await request.json()

    # Call the existing, correct Firestore-based function
    success = await save_dynamic_scraping_config(account_id, aac_user_id, incoming_config_data)

    # Cache invalidation for user favorites changes
    if success:
        await cache_manager.invalidate_cache(account_id, aac_user_id)
        return JSONResponse(content={"message": "User favorites saved successfully"})
    else:
        raise HTTPException(status_code=500, detail="Failed to save user favorites (scraping configuration) to Firestore.")


async def load_dynamic_scraping_config(account_id: str, aac_user_id: str):
    """Loads scraping configuration from Firestore for a specific user."""
    config = await load_firestore_document( # AWAIT HERE
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="config/scraping_config", # Firestore path
        default_data=DEFAULT_SCRAPING_CONFIG.copy()
    )
    # Add UUIDs if missing to sources for existing data (part of original logic)
    needs_save = False
    for key in DEFAULT_SCRAPING_CONFIG.keys():
        if key in config and isinstance(config[key], list):
            for source in config[key]:
                if 'id' not in source or not source['id']:
                    source['id'] = str(uuid.uuid4()) # Ensure uuid is imported (from uuid import uuid4)
                    needs_save = True
    if needs_save:
        await save_dynamic_scraping_config(account_id, aac_user_id, config) # AWAIT HERE
    return config


async def save_dynamic_scraping_config(account_id: str, aac_user_id: str, config_data: dict):
    """Saves the scraping configuration to Firestore for a specific user."""
    return await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="config/scraping_config",
        data_to_save=config_data
    )

# --- NEW FAVORITES SYSTEM ENDPOINTS ---

@app.get("/api/favorites", response_model=FavoritesData)
async def get_favorites(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """Get all favorite topic buttons with their scraping configurations"""
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    
    try:
        config = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="config/favorites_config",
            default_data=DEFAULT_FAVORITES_CONFIG.copy()
        )
        return FavoritesData(**config)
    except Exception as e:
        logging.error(f"Error loading favorites for user {aac_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load favorites configuration")

@app.post("/api/favorites")
async def save_favorites(favorites_data: FavoritesData, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """Save all favorite topic buttons"""
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    
    try:
        success = await save_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="config/favorites_config",
            data_to_save=favorites_data.dict()
        )
        if success:
            # Cache invalidation for favorites changes
            await cache_manager.invalidate_cache(account_id, aac_user_id)
            return JSONResponse(content={"message": "Favorites saved successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to save favorites")
    except Exception as e:
        logging.error(f"Error saving favorites for user {aac_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save favorites configuration")

@app.post("/api/favorites/smart-analysis")
async def smart_analysis_endpoint(request: Request):
    """Super simple smart analysis that tries multiple approaches automatically"""
    try:
        data = await request.json()
        url = data.get('url', '').strip()
        sample_article_url = data.get('sample_article_url', '').strip() if data.get('sample_article_url') else None
        keywords = data.get('keywords', [])
        
        if not url:
            return {"success": False, "message": "URL is required"}
        
        # Try to analyze the website automatically
        config, analysis_info = perform_smart_website_analysis(url, sample_article_url, keywords)
        
        if config:
            return {
                "success": True,
                "config": config,
                "message": f"Successfully analyzed {url}",
                "articles_found": analysis_info.get('articles_found', 'multiple'),
                "analysis_method": analysis_info.get('method', 'automatic')
            }
        else:
            # Provide more specific error messages
            error_msg = "Could not automatically configure this website."
            suggestions = []
            
            if not sample_article_url:
                suggestions.append("Try providing a sample article URL from this site")
            
            if 'denverpost.com' in url.lower() or 'oklahoman.com' in url.lower():
                suggestions.append("This site may have anti-bot protection")
            
            suggestions.append("Try a pre-built template instead")
            
            full_message = error_msg
            if suggestions:
                full_message += ". Suggestions: " + "; ".join(suggestions)
            
            return {
                "success": False,
                "message": full_message,
                "suggestions": suggestions
            }
            
    except Exception as e:
        print(f"Smart analysis error: {str(e)}")
        return {"success": False, "message": "Analysis failed due to technical error"}

def perform_smart_website_analysis(url, sample_article_url=None, keywords=None):
    """Intelligent website analysis that tries multiple approaches"""
    try:
        if keywords is None:
            keywords = []
            
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Send a request to the website
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        analysis_info = {'method': 'automatic', 'articles_found': 0}
        
        # If we have a sample article URL, use it to understand the structure
        if sample_article_url:
            try:
                article_response = requests.get(sample_article_url, headers=headers, timeout=10, allow_redirects=True)
                article_soup = BeautifulSoup(article_response.content, 'html.parser')
                
                # Extract patterns from the sample article
                config = analyze_from_sample_article(article_soup, sample_article_url, url)
                if config:
                    # Add keywords to the configuration
                    config['keywords'] = keywords if keywords else []
                    analysis_info['method'] = 'sample_article'
                    # Test the config on the main URL
                    main_response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                    main_soup = BeautifulSoup(main_response.content, 'html.parser')
                    if validate_smart_config(config, main_soup):
                        articles = main_soup.select(config['headline_selector'])
                        analysis_info['articles_found'] = len(articles)
                        return config, analysis_info
            except Exception as e:
                print(f"Sample article analysis failed: {e}")
        
        # Regular analysis of the main URL
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try multiple strategies in order of likelihood
        strategies = [
            analyze_common_news_patterns,
            analyze_semantic_patterns,
            analyze_structural_patterns,
            analyze_fallback_patterns
        ]
        
        for strategy in strategies:
            result = strategy(soup, url)
            if result and validate_smart_config(result, soup):
                # Add keywords to the configuration
                result['keywords'] = keywords if keywords else []
                articles = soup.select(result['headline_selector'])
                analysis_info['articles_found'] = len(articles)
                analysis_info['method'] = strategy.__name__
                return result, analysis_info
        
        return None, analysis_info
        
    except Exception as e:
        print(f"Smart analysis failed for {url}: {str(e)}")
        return None, {'method': 'error', 'articles_found': 0}

def analyze_from_sample_article(article_soup, sample_url, base_url):
    """Analyze a sample article to understand the site structure"""
    try:
        # Get the domain pattern
        from urllib.parse import urlparse
        sample_parsed = urlparse(sample_url)
        base_parsed = urlparse(base_url)
        
        # Look at the sample article's structure to understand link patterns
        title_element = None
        
        # Common article title patterns
        title_selectors = [
            'h1', 'h1.headline', 'h1.title', '.article-title', '.headline', 
            '[data-testid="headline"]', '.story-headline', '.entry-title'
        ]
        
        for selector in title_selectors:
            elements = article_soup.select(selector)
            if elements and len(elements[0].get_text().strip()) > 10:
                title_element = elements[0]
                break
        
        if not title_element:
            return None
        
        # Now create selectors that would work on the main page
        # Common patterns for article listing pages
        headline_selectors = [
            'h2 a', 'h3 a', '.headline a', '.article-title a',
            'h2', 'h3', '.headline', '.article-title',
            '[data-testid="card-headline"]', '.story-headline'
        ]
        
        link_selectors = [
            'h2 a', 'h3 a', '.headline a', '.article-title a',
            'a[href*="/story/"]', 'a[href*="/article/"]', 
            'a[href*="/sports/"]', 'a[href*="/news/"]'
        ]
        
        # Return a configuration based on common patterns
        return {
            'url': base_url,
            'headline_selector': 'h2, h3, .headline, .article-title',
            'url_selector': 'h2 a, h3 a, .headline a, .article-title a',
            'url_attribute': 'href',
            'url_prefix': f"{base_parsed.scheme}://{base_parsed.netloc}",
            'keywords': []
        }
        
    except Exception as e:
        print(f"Sample article analysis error: {e}")
        return None

def analyze_common_news_patterns(soup, url):
    """Try common news website patterns"""
    # Site-specific patterns for known sites
    site_patterns = {
        'denverpost.com': {
            'headline_selector': 'h3 a, h2 a, .headline a',
            'url_selector': 'h3 a, h2 a, .headline a'
        },
        'oklahoman.com': {
            'headline_selector': 'h3 a, h2 a, .story-headline a',
            'url_selector': 'h3 a, h2 a, .story-headline a'
        },
        'espn.com': {
            'headline_selector': 'h1 a, h2 a, h3 a',
            'url_selector': 'h1 a, h2 a, h3 a'
        }
    }
    
    # Check if this is a known site
    for domain, pattern in site_patterns.items():
        if domain in url.lower():
            headlines = soup.select(pattern['headline_selector'])
            links = soup.select(pattern['url_selector'])
            
            if len(headlines) >= 2 and len(links) >= 2:
                return {
                    'url': url,
                    'headline_selector': pattern['headline_selector'],
                    'url_selector': pattern['url_selector'],
                    'url_attribute': 'href',
                    'url_prefix': get_url_prefix(url),
                    'keywords': []
                }
    
    # Generic common patterns
    common_patterns = [
        # BBC-style
        {
            'headline_selector': 'h3[data-testid="card-headline"], [data-testid="card-headline"]',
            'url_selector': 'a[data-testid="internal-link"]'
        },
        # CNN-style
        {
            'headline_selector': 'h3.cd__headline a span, .cd__headline',
            'url_selector': 'h3.cd__headline a, .cd__headline a'
        },
        # Generic news patterns - more specific first
        {
            'headline_selector': 'h2 a, h3 a',
            'url_selector': 'h2 a, h3 a'
        },
        {
            'headline_selector': 'h2, h3',
            'url_selector': 'h2 a, h3 a'
        },
        # Article tags
        {
            'headline_selector': 'article h2, article h3',
            'url_selector': 'article a'
        },
        # WordPress/CMS patterns
        {
            'headline_selector': '.entry-title, .post-title, .story-headline',
            'url_selector': '.entry-title a, .post-title a, .story-headline a'
        }
    ]
    
    for pattern in common_patterns:
        headlines = soup.select(pattern['headline_selector'])
        links = soup.select(pattern['url_selector'])
        
        if len(headlines) >= 3 and len(links) >= 3:
            return {
                'url': url,
                'headline_selector': pattern['headline_selector'],
                'url_selector': pattern['url_selector'],
                'url_attribute': 'href',
                'url_prefix': get_url_prefix(url),
                'keywords': []
            }
    
    return None

def analyze_semantic_patterns(soup, url):
    """Look for semantic patterns in the HTML"""
    # Find elements that look like article headlines
    potential_headlines = []
    
    # Look for headings with article-like text
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        text = tag.get_text().strip()
        if len(text) > 10 and looks_like_article_title(text):
            potential_headlines.append(tag)
    
    if len(potential_headlines) >= 3:
        # Create selector for these headlines
        tag_names = set(tag.name for tag in potential_headlines)
        headline_selector = ', '.join(tag_names)
        
        # Look for links within or near these headlines
        url_selector = ', '.join(f'{tag} a' for tag in tag_names)
        
        return {
            'url': url,
            'headline_selector': headline_selector,
            'url_selector': url_selector,
            'url_attribute': 'href',
            'url_prefix': get_url_prefix(url),
            'keywords': []
        }
    
    return None

def analyze_structural_patterns(soup, url):
    """Analyze the overall structure of the page"""
    # Find repeated structures that might be article cards
    potential_containers = soup.find_all(['div', 'article', 'section'])
    
    # Look for containers with both headings and links
    good_containers = []
    for container in potential_containers:
        headings = container.find_all(['h1', 'h2', 'h3', 'h4'])
        links = container.find_all('a')
        
        if len(headings) > 0 and len(links) > 0:
            # Check if this looks like an article snippet
            text_content = container.get_text().strip()
            if 20 < len(text_content) < 500:  # Reasonable length for article preview
                good_containers.append(container)
    
    if len(good_containers) >= 3:
        # Try to find common class names
        class_names = []
        for container in good_containers[:5]:  # Look at first 5
            if container.get('class'):
                class_names.extend(container['class'])
        
        # Find most common class
        if class_names:
            from collections import Counter
            common_class = Counter(class_names).most_common(1)[0][0]
            
            return {
                'url': url,
                'headline_selector': f'.{common_class} h2, .{common_class} h3',
                'url_selector': f'.{common_class} a',
                'url_attribute': 'href',
                'url_prefix': get_url_prefix(url),
                'keywords': []
            }
    
    return None

def analyze_fallback_patterns(soup, url):
    """Last resort - very basic patterns"""
    # Just try to find any headings and links
    headings = soup.find_all(['h2', 'h3'])
    links = soup.find_all('a')
    
    if len(headings) >= 2 and len(links) >= 5:
        return {
            'url': url,
            'headline_selector': 'h2, h3',
            'url_selector': 'a',
            'url_attribute': 'href',
            'url_prefix': get_url_prefix(url),
            'keywords': []
        }
    
    return None

def looks_like_article_title(text):
    """Check if text looks like an article title"""
    # Basic heuristics
    if len(text) < 10 or len(text) > 200:
        return False
    
    # Should have some capitalization
    if text.islower() or text.isupper():
        return False
    
    # Shouldn't be navigation or common website elements
    skip_patterns = [
        'menu', 'navigation', 'search', 'login', 'signup', 'subscribe',
        'follow us', 'contact', 'about', 'privacy', 'terms'
    ]
    
    text_lower = text.lower()
    for pattern in skip_patterns:
        if pattern in text_lower:
            return False
    
    return True

def validate_smart_config(config, soup):
    """Validate that the smart config actually works"""
    try:
        headlines = soup.select(config['headline_selector'])
        links = soup.select(config['url_selector'])
        
        # Must find at least 2 of each
        if len(headlines) < 2 or len(links) < 2:
            return False
        
        # Check that links actually have href attributes
        valid_links = 0
        for link in links[:5]:  # Check first 5
            href = link.get(config['url_attribute'])
            if href and href.strip():
                valid_links += 1
        
        return valid_links >= 2
        
    except Exception:
        return False

def get_url_prefix(url):
    """Extract the base URL for prefixing relative links"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except:
        return ""

@app.post("/api/favorites/auto-detect-selectors")
async def auto_detect_selectors(
    request: dict,
    current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]
):
    """Auto-detect CSS selectors for web scraping from sample URLs"""
    try:
        sample_url = request.get("sample_url")
        base_url = request.get("base_url")
        
        if not sample_url or not base_url:
            return {"success": False, "message": "Both sample_url and base_url are required"}
        
        # Import requests for web scraping
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse
        
        # Fetch the base URL page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(base_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"success": False, "message": f"Could not fetch base URL: {response.status_code}"}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Auto-detect selectors using common patterns
        detected_selectors = detect_article_selectors(soup, sample_url, base_url)
        
        if not detected_selectors["headline_selector"] or not detected_selectors["link_selector"]:
            return {
                "success": False, 
                "message": "Could not auto-detect selectors. Please configure manually.",
                "selectors": detected_selectors
            }
        
        # Test the detected selectors
        test_config = {
            "url": base_url,
            "headline_selector": detected_selectors["headline_selector"],
            "url_selector": detected_selectors["link_selector"],
            "url_attribute": "href",
            "url_prefix": detected_selectors.get("url_prefix", ""),
            "keywords": []
        }
        
        test_result = test_scraping_config(test_config)
        
        return {
            "success": True,
            "message": f"Auto-detected selectors successfully! Found {len(test_result.get('articles', []))} articles.",
            "selectors": detected_selectors,
            "confidence": detected_selectors.get("confidence", 0.8),
            "sample_count": len(test_result.get('articles', []))
        }
        
    except Exception as e:
        logging.error(f"Error auto-detecting selectors: {e}", exc_info=True)
        return {"success": False, "message": f"Auto-detection failed: {str(e)}"}

def detect_article_selectors(soup, sample_url, base_url):
    """Analyze webpage structure to detect the best CSS selectors for articles"""
    from urllib.parse import urljoin, urlparse
    
    parsed_sample = urlparse(sample_url)
    parsed_base = urlparse(base_url)
    
    # Common article link patterns to look for
    link_patterns = [
        'a[href*="/article/"]',
        'a[href*="/story/"]',
        'a[href*="/news/"]',
        'a[href*="/post/"]',
        'h1 a', 'h2 a', 'h3 a',
        '.article-link', '.story-link', '.news-link',
        'article a', '.entry a', '.post a'
    ]
    
    # Common headline patterns
    headline_patterns = [
        'h1', 'h2', 'h3',
        '.headline', '.title', '.article-title', '.story-title',
        'h1 a', 'h2 a', 'h3 a',
        'article h1', 'article h2', 'article h3'
    ]
    
    best_link_selector = None
    best_headline_selector = None
    best_score = 0
    
    # Test each combination of patterns
    for link_pattern in link_patterns:
        links = soup.select(link_pattern)
        if not links:
            continue
            
        # Filter links that could be articles
        article_links = []
        for link in links:
            href = link.get('href', '')
            if href:
                full_url = urljoin(base_url, href)
                # Check if this could be an article URL
                if is_likely_article_url(full_url, sample_url):
                    article_links.append(link)
        
        if len(article_links) < 2:  # Need at least 2 articles
            continue
            
        # Find corresponding headline pattern
        for headline_pattern in headline_patterns:
            headlines = soup.select(headline_pattern)
            if not headlines:
                continue
                
            # Score this combination
            score = score_selector_combination(article_links, headlines, soup)
            
            if score > best_score:
                best_score = score
                best_link_selector = link_pattern
                best_headline_selector = headline_pattern
    
    # Determine URL prefix
    url_prefix = ""
    if best_link_selector:
        sample_links = soup.select(best_link_selector)
        if sample_links:
            first_href = sample_links[0].get('href', '')
            if first_href and not first_href.startswith('http'):
                parsed = urlparse(base_url)
                url_prefix = f"{parsed.scheme}://{parsed.netloc}"
    
    return {
        "headline_selector": best_headline_selector,
        "link_selector": best_link_selector,
        "url_prefix": url_prefix,
        "confidence": min(best_score / 10, 1.0)  # Normalize score to 0-1
    }

def is_likely_article_url(url, sample_url):
    """Check if a URL looks like it could be an article similar to the sample"""
    from urllib.parse import urlparse
    
    parsed_url = urlparse(url)
    parsed_sample = urlparse(sample_url)
    
    # Must be from same domain
    if parsed_url.netloc != parsed_sample.netloc:
        return False
    
    # Look for common article URL patterns
    path = parsed_url.path.lower()
    sample_path = parsed_sample.path.lower()
    
    # Common article indicators
    article_indicators = ['article', 'story', 'news', 'post', 'blog']
    has_indicator = any(indicator in path for indicator in article_indicators)
    
    # Similar path structure to sample
    sample_parts = [p for p in sample_path.split('/') if p]
    url_parts = [p for p in path.split('/') if p]
    
    # Should have similar depth
    depth_similar = abs(len(sample_parts) - len(url_parts)) <= 2
    
    # Look for date patterns (articles often have dates in URLs)
    import re
    has_date_pattern = bool(re.search(r'/20\d{2}/', path))
    
    return has_indicator and depth_similar

def score_selector_combination(links, headlines, soup):
    """Score how good a selector combination is"""
    score = 0
    
    # Prefer more matches (but not too many)
    link_count = len(links)
    headline_count = len(headlines)
    
    if 3 <= link_count <= 50:
        score += 5
    elif 2 <= link_count <= 100:
        score += 3
    
    if 3 <= headline_count <= 50:
        score += 5
    elif 2 <= headline_count <= 100:
        score += 3
    
    # Prefer when link and headline counts are similar
    count_diff = abs(link_count - headline_count)
    if count_diff <= 2:
        score += 3
    elif count_diff <= 5:
        score += 1
    
    # Prefer links that have meaningful text
    meaningful_links = 0
    for link in links[:10]:  # Sample first 10
        text = link.get_text(strip=True)
        if text and len(text) > 10:  # Has substantial text
            meaningful_links += 1
    
    score += meaningful_links
    
    # Prefer headlines that have meaningful text
    meaningful_headlines = 0
    for headline in headlines[:10]:  # Sample first 10
        text = headline.get_text(strip=True)
        if text and len(text) > 10:
            meaningful_headlines += 1
    
    score += meaningful_headlines
    
    return score

# --- HELP SYSTEM API ENDPOINTS ---

class HelpContent(BaseModel):
    content: str = Field(..., description="HTML content of the help document")
    page_specific: bool = Field(default=False, description="Whether this is page-specific help")
    target_page: Optional[str] = Field(None, description="Target page for page-specific help")
    title: str = Field(..., min_length=1, max_length=100, description="Title of the help document")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

class CreateHelpContentRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)
    page_specific: bool = Field(default=False)
    target_page: Optional[str] = Field(None)

class UpdateHelpContentRequest(BaseModel):
    help_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)
    page_specific: bool = Field(default=False)
    target_page: Optional[str] = Field(None)

@app.get("/api/help/content")
async def get_help_content(
    token_info: Annotated[Dict[str, str], Depends(verify_firebase_token_only)],
    page: Optional[str] = None
):
    """Get help content - either general help or page-specific help"""
    account_id = token_info["account_id"]
    
    try:
        # Load help content from Firestore
        help_data = await load_firestore_document(
            account_id="system",  # Use system-wide help content
            aac_user_id="default",
            doc_subpath="help/content",
            default_data={"general": [], "page_specific": {}}
        )
        
        if page:
            # Return page-specific help if requested
            page_help = help_data.get("page_specific", {}).get(page, [])
            return JSONResponse(content={
                "page": page,
                "content": page_help,
                "type": "page_specific"
            })
        else:
            # Return general help
            general_help = help_data.get("general", [])
            return JSONResponse(content={
                "content": general_help,
                "type": "general"
            })
            
    except Exception as e:
        logging.error(f"Error loading help content: {e}")
        # Return default help content
        default_content = {
            "title": "Welcome to Bravo Help",
            "content": "<h1>Getting Started</h1><p>Welcome to your AAC communication app!</p>",
            "created_at": dt.now().isoformat()
        }
        return JSONResponse(content={
            "content": [default_content],
            "type": "general"
        })

@app.post("/api/help/content")
async def create_help_content(
    request_data: CreateHelpContentRequest,
    token_info: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]
):
    """Create new help content (admin only)"""
    account_id = token_info["account_id"]
    user_email = token_info.get("email", "")
    
    # Check if user is admin
    if user_email != "admin@talkwithbravo.com":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Load existing help content
        help_data = await load_firestore_document(
            account_id="system",
            aac_user_id="default", 
            doc_subpath="help/content",
            default_data={"general": [], "page_specific": {}}
        )
        
        # Create new help content
        new_content = {
            "id": str(uuid.uuid4()),
            "title": request_data.title,
            "content": request_data.content,
            "page_specific": request_data.page_specific,
            "target_page": request_data.target_page,
            "created_at": dt.now().isoformat(),
            "updated_at": dt.now().isoformat()
        }
        
        # Add to appropriate section
        if request_data.page_specific and request_data.target_page:
            if request_data.target_page not in help_data["page_specific"]:
                help_data["page_specific"][request_data.target_page] = []
            help_data["page_specific"][request_data.target_page].append(new_content)
        else:
            help_data["general"].append(new_content)
        
        # Save back to Firestore
        success = await save_firestore_document(
            account_id="system",
            aac_user_id="default",
            doc_subpath="help/content",
            data_to_save=help_data
        )
        
        if success:
            return JSONResponse(content={
                "message": "Help content created successfully",
                "content_id": new_content["id"]
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to save help content")
            
    except Exception as e:
        logging.error(f"Error creating help content: {e}")
        raise HTTPException(status_code=500, detail="Failed to create help content")

@app.put("/api/help/content")
async def update_help_content(
    request_data: UpdateHelpContentRequest,
    token_info: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]
):
    """Update existing help content (admin only)"""
    account_id = token_info["account_id"]
    user_email = token_info.get("email", "")
    
    # Check if user is admin
    if user_email != "admin@talkwithbravo.com":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Load existing help content
        help_data = await load_firestore_document(
            account_id="system",
            aac_user_id="default",
            doc_subpath="help/content", 
            default_data={"general": [], "page_specific": {}}
        )
        
        # Find and update the content
        content_found = False
        
        # Check general help
        for i, content in enumerate(help_data["general"]):
            if content.get("id") == request_data.help_id:
                help_data["general"][i].update({
                    "title": request_data.title,
                    "content": request_data.content,
                    "page_specific": request_data.page_specific,
                    "target_page": request_data.target_page,
                    "updated_at": dt.now().isoformat()
                })
                content_found = True
                break
        
        # Check page-specific help if not found in general
        if not content_found:
            for page, contents in help_data["page_specific"].items():
                for i, content in enumerate(contents):
                    if content.get("id") == request_data.help_id:
                        help_data["page_specific"][page][i].update({
                            "title": request_data.title,
                            "content": request_data.content,
                            "page_specific": request_data.page_specific,
                            "target_page": request_data.target_page,
                            "updated_at": dt.now().isoformat()
                        })
                        content_found = True
                        break
                if content_found:
                    break
        
        if not content_found:
            raise HTTPException(status_code=404, detail="Help content not found")
        
        # Save back to Firestore
        success = await save_firestore_document(
            account_id="system",
            aac_user_id="default",
            doc_subpath="help/content",
            data_to_save=help_data
        )
        
        if success:
            return JSONResponse(content={"message": "Help content updated successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to save help content")
            
    except Exception as e:
        logging.error(f"Error updating help content: {e}")
        raise HTTPException(status_code=500, detail="Failed to update help content")

@app.delete("/api/help/content/{help_id}")
async def delete_help_content(
    help_id: str,
    token_info: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]
):
    """Delete help content (admin only)"""
    account_id = token_info["account_id"]
    user_email = token_info.get("email", "")
    
    # Check if user is admin
    if user_email != "admin@talkwithbravo.com":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Load existing help content
        help_data = await load_firestore_document(
            account_id="system",
            aac_user_id="default",
            doc_subpath="help/content",
            default_data={"general": [], "page_specific": {}}
        )
        
        # Find and remove the content
        content_found = False
        
        # Check general help
        help_data["general"] = [c for c in help_data["general"] if c.get("id") != help_id]
        
        # Check page-specific help
        for page in help_data["page_specific"]:
            original_count = len(help_data["page_specific"][page])
            help_data["page_specific"][page] = [c for c in help_data["page_specific"][page] if c.get("id") != help_id]
            if len(help_data["page_specific"][page]) < original_count:
                content_found = True
        
        if not content_found:
            raise HTTPException(status_code=404, detail="Help content not found")
        
        # Save back to Firestore
        success = await save_firestore_document(
            account_id="system",
            aac_user_id="default",
            doc_subpath="help/content",
            data_to_save=help_data
        )
        
        if success:
            return JSONResponse(content={"message": "Help content deleted successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to delete help content")
            
    except Exception as e:
        logging.error(f"Error deleting help content: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete help content")

@app.post("/api/favorites/test-scraping")
async def test_scraping_config(test_request: TestScrapingRequest, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """Test a scraping configuration and return sample results"""
    try:
        # Convert scraping config to dict format expected by scrape_website
        config_dict = test_request.scraping_config.dict()
        
        # Test the scraping
        articles = await scrape_website(config_dict)
        
        return JSONResponse(content={
            "success": True,
            "sample_count": len(articles),
            "sample_articles": articles[:5],  # Return first 5 articles as sample
            "message": f"Successfully scraped {len(articles)} articles"
        })
    except Exception as e:
        logging.error(f"Error testing scraping config: {e}", exc_info=True)
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "message": "Failed to test scraping configuration"
        })

@app.post("/api/favorites/get-topic-content")
async def get_topic_content(request: Request, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """Get content for a specific topic by scraping and processing with LLM"""
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    
    try:
        data = await request.json()
        topic_text = data.get("topic", "")
        
        if not topic_text:
            raise HTTPException(status_code=400, detail="Missing topic parameter")
        
        # Load favorites to find matching button
        favorites_config = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="config/favorites_config",
            default_data=DEFAULT_FAVORITES_CONFIG.copy()
        )
        
        # Find the button with matching text
        target_button = None
        for button in favorites_config.get("buttons", []):
            if button.get("text", "").lower() == topic_text.lower():
                target_button = button
                break
        
        if not target_button:
            raise HTTPException(status_code=404, detail=f"No favorite topic found for '{topic_text}'")
        
        # Get scraping config
        scraping_config = target_button.get("scraping_config", {})
        
        if not scraping_config:
            raise HTTPException(status_code=400, detail="No scraping configuration found for this topic")
        
        # Scrape articles
        articles = await scrape_website(scraping_config)
        
        if not articles:
            return JSONResponse(content={
                "summaries": [],
                "message": "No articles found for this topic"
            })
        
        # Process with LLM (similar to get_current_events)
        import random
        random.shuffle(articles)
        num_articles_to_process = 10
        top_articles = articles[:num_articles_to_process]
        
        # Process articles with LLM
        llm_tasks = [_process_single_article(item, topic_text) for item in top_articles]
        llm_results = await asyncio.gather(*llm_tasks)
        
        # Filter successful results
        successful_results = [result for result in llm_results if result is not None]
        
        return JSONResponse(content={
            "summaries": successful_results,
            "topic": topic_text
        })
        
    except Exception as e:
        logging.error(f"Error getting topic content for {topic_text}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get content for topic: {e}")


async def scrape_website(config):
    url = config.get("url")
    headline_selector = config.get("headline_selector")
    url_selector = config.get("url_selector")
    url_attribute = config.get("url_attribute", 'href')
    url_prefix = config.get("url_prefix", "")
    articles = []
    try:
        if not url or not headline_selector or not url_selector:
            print(f"Incomplete scraping config for {url}")
            return []
        # Use aiohttp for asynchronous requests
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                headline_elements = soup.select(headline_selector)
                url_elements = soup.select(url_selector)

                for i in range(min(len(headline_elements), len(url_elements))):
                    headline = headline_elements[i].get_text(strip=True)
                    article_url = url_elements[i].get(url_attribute)
                    if article_url:
                        full_url = urljoin(url, url_prefix + article_url) # use urljoin
                        articles.append({"title": headline, "url": full_url})
        return articles
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []





# --- Helper function to process ONE article ---
async def _process_single_article(item: dict, event_type: str):
    """
    Calls LLM for a single article, parses the response, and returns 
    a valid dictionary {'option': ..., 'summary': ...} on success, 
    or None on failure/error.
    """
    if not isinstance(item, dict) or 'title' not in item or 'url' not in item:
        print(f"Skipping invalid item in _process_single_article: {item!r}")
        return None 

    # UPDATED prompt instructions and example JSON structure:
    prompt_template = """
Given the following {event_type} story title and URL:
Title: {title}
URL: {url}

Please perform the following two tasks based *only* on the provided Title and URL:
1. Generate a natural-sounding, expressive, and engaging conversational starter sentence or two about this news story, suitable for initiating a discussion with someone nearby (e.g., "Did you hear about...", "I just saw..."). Do not use something obvious like "Did you see the article...". Keep it brief, energetic and focus on the main point indicated by the title. Add a question or prompt to encourage conversation.
2. Generate a very short (3-5 word) phrase that captures the absolute key message or topic (suitable for displaying on a button).

Format your response STRICTLY as a single JSON object with two keys:
- "option": This key's value should be the conversational starter sentence(s) (from task 1).
- "summary": This key's value should be the very short 3-5 word phrase (from task 2).

Example JSON format:
{{ "option": "Did you hear about the new library opening downtown? They say it has some great features.", "summary": "New library opens" }}

JSON response:
"""
    
    prompt_text = None 
    try:
        prompt_text = prompt_template.format(
            event_type=event_type, 
            title=item['title'], 
            url=item['url']
        )
    except KeyError as e:
        print(f"ERROR: KeyError during prompt formatting for item {item!r}. Error: {e}")
        return None 
    except Exception as e:
        print(f"ERROR: Unexpected error during prompt formatting for item {item!r}. Error: {e}")
        return None

    if prompt_text is None:
         print(f"ERROR: prompt_text was None for item {item!r}, skipping LLM call.")
         return None

    extracted_json_string = None 
    
    try:
        # --- LLM Call ---
        # Use the helper function for LLM call with fallback
        summary_text = await _generate_gemini_content_with_fallback(prompt_text)
        #print(f"LLM raw output for '{item['title']}': {summary_text}") # Keep logging raw output

        # --- Attempt to Extract JSON OBJECT using Regex ---
        # ***** CHANGE HERE: Look for '{...}' instead of '[...]' *****
        match = re.search(r'(\{.*\})', summary_text, re.DOTALL) 

        if match:
            extracted_json_string = match.group(1)
            #print(f"Extracted JSON string: {extracted_json_string}")

            # --- Parse the *Extracted* JSON string ---
            try:
                # Should parse directly into a dictionary now
                parsed_data = json.loads(extracted_json_string) 

                # --- Validate the Dictionary ---
                # ***** CHANGE HERE: Validate dictionary directly *****
                if isinstance(parsed_data, dict) and "option" in parsed_data and "summary" in parsed_data:
                     # parsed_data is the dictionary we need
                     article_data = parsed_data 
                     print(f"Successfully processed: {item['title']}")
                     return article_data # Return the valid dictionary
                else:
                    # Handle missing keys or if it's not a dict
                    print(f"Error: Parsed JSON is not a dict or missing keys for '{item['title']}'. Data: {parsed_data}")
                    return None # Exclude items with wrong structure or missing keys
            except json.JSONDecodeError as json_e:
                print(f"Error decoding extracted JSON for '{item['title']}': {json_e}. Extracted: {extracted_json_string}")
                return None # Exclude items with invalid JSON
        else:
            # Handle cases where the regex didn't find the {...} pattern
            # ***** CHANGE HERE: Update error message *****
            print(f"Error: Could not find JSON object pattern '{{...}}' in LLM output for '{item['title']}'. Output: {summary_text}") 
            return None # Exclude items where regex fails

    except Exception as e:
        # Handle errors during the LLM call itself
        print(f"Error during LLM content generation for '{item['title']}': {e}")
        return None 




# --- Main route handler ---
@app.post("/get-current-events")
async def get_current_events(request: Request, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    data = await request.json()
    event_type = data.get("eventType") # e.g., "news", "sports", "entertainment"
    #print(f"--- Received request for /get-current-events: eventType='{event_type}' ---") # Log request
    
    scraping_configs_main = await load_dynamic_scraping_config(account_id, aac_user_id) 
    config_key = f"{event_type}_sources"
    scraping_configs = scraping_configs_main.get(config_key, [])
    #print(f"Found {len(scraping_configs)} scraping configs for key '{config_key}'.") # Log config count

    if not scraping_configs:
        print(f"No configs found for '{event_type}', returning empty list.")
        return JSONResponse(content=[])

    all_articles = []

    # --- Web Scraping (concurrent) ---
    # Ensure scrape_website function can handle the dicts in scraping_configs
    #print(f"Starting web scraping for {len(scraping_configs)} sources...")
    scrape_tasks = [scrape_website(config) for config in scraping_configs]
    scrape_results = await asyncio.gather(*scrape_tasks)
    for i, articles in enumerate(scrape_results):
        #print(f"Source {i+1} found {len(articles)} articles.") # Log articles per source
        all_articles.extend(articles)
    #print(f"Total articles found after scraping: {len(all_articles)}") # Log total scraped
    # --- End Web Scraping ---

    if all_articles:
        random.shuffle(all_articles)
        num_articles_to_process = 10 
        top_articles = all_articles[:num_articles_to_process] 
        #print(f"Processing {len(top_articles)} articles with LLM for type '{event_type}'...")

        # --- Create concurrent tasks for LLM processing ---
        llm_tasks = [_process_single_article(item, event_type) for item in top_articles]
        
        # --- Run LLM tasks concurrently ---
        results = await asyncio.gather(*llm_tasks) 

        # --- Filter out None results (errors/excluded items) ---
        final_summarized_options = [result for result in results if result is not None]

        #print(f"Final combined list being returned (excluding errors): {final_summarized_options}")
        return JSONResponse(content=final_summarized_options)
    else:
        return JSONResponse(content=[])

# A new Pydantic model for the /play-audio request
class PlayAudioRequest(BaseModel):
    text: str
    routing_target: Optional[RoutingTarget] = "default"



@app.post("/play-audio")
async def play_audio(request: PlayAudioRequest, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    effective_routing_target = request.routing_target or "default"
    if not request.text:
        raise HTTPException(status_code=400, detail="No text provided")
    try:
        # NEW: Load user-specific settings for voice and rate
        user_settings = await load_settings_from_file(account_id, aac_user_id) # Load settings

        # Use settings, falling back to global defaults if setting is missing
        voice_to_use = user_settings.get("selected_tts_voice_name", DEFAULT_TTS_VOICE)
        rate_to_use = user_settings.get("speech_rate", DEFAULT_SPEECH_RATE)

        logging.info(f"Synthesizing speech for account {account_id} user {aac_user_id} with text: '{request.text[:50]}...' for routing target: {request.routing_target}")

        audio_bytes, sample_rate = await synthesize_speech_to_bytes(
            text=request.text,
            voice_name=voice_to_use, # Pass the value from settings
            wpm_rate=rate_to_use      # Pass the value from settings
        )
        import base64
        encoded_audio = base64.b64encode(audio_bytes).decode('utf-8')
        
        # Save audio to a unique file in the static directory
        filename = f"play_audio_{uuid.uuid4().hex}.wav"
        file_path = os.path.join(static_file_path, filename)
        with open(file_path, "wb") as f:
            f.write(audio_bytes)


        audio_url = f"https://{DOMAIN}/static/{filename}"

        return JSONResponse(content={
            "audio_data": encoded_audio,
            "audio_url": audio_url,
            "sample_rate": sample_rate,
            "routing_target": request.routing_target
        })
    
    except Exception as e:
        logging.error(f"Error handling /play-audio request for routing target {effective_routing_target}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to synthesize audio: {str(e)}")







# Ensure this function (synthesize_speech_to_bytes) is in your server.py file,
# unindented at the global scope, and has this full body.
async def synthesize_speech_to_bytes(text: str, voice_name: str, wpm_rate: int) -> tuple[bytes, int]:
    """
    Synthesizes speech using the provided parameters. No DB lookups.
    """
    if not tts_client:
        raise Exception("TTS service unavailable.")

    # The logic is the same, but it uses passed-in args, not DB lookups
    pyttsx3_wpm_rate = wpm_rate
    speaking_rate_google = 1.0
    if pyttsx3_wpm_rate < 130: speaking_rate_google = 0.85
    elif pyttsx3_wpm_rate > 230: speaking_rate_google = 1.15

    logging.info(f"Using Google Cloud TTS. Voice: {voice_name}, Rate: {speaking_rate_google}")
    synthesis_input = google_tts.SynthesisInput(text=text)
    voice_params = google_tts.VoiceSelectionParams(language_code="en-US", name=voice_name)
    
    sample_rate_hertz = 24000
    if "Standard" in voice_name:
        sample_rate_hertz = 16000

    audio_config = google_tts.AudioConfig(
        audio_encoding=google_tts.AudioEncoding.LINEAR16,
        speaking_rate=speaking_rate_google,
        sample_rate_hertz=sample_rate_hertz
    )
    
    # This call should be wrapped to run in a thread to not block the event loop
    response = await asyncio.to_thread(
        tts_client.synthesize_speech,
        input=synthesis_input, voice=voice_params, audio_config=audio_config
    )

    return response.audio_content, sample_rate_hertz



TEST_SOUND_FILE = "static/test.wav"  # Define the path to your test sound file.  Make sure this file exists!

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)






# Audio config (user-specific)
# REMOVE the global `AUDIO_CONFIG_FILE = "audio_config.json"`
async def load_config(account_id: str, aac_user_id: str) -> Dict: # Now an async function
    """Loads the audio device configuration from Firestore for a specific user."""
    # Define a default structure for audio_config, matching template_user_data_paths["audio_config.json"]
    DEFAULT_AUDIO_CONFIG = json.loads(template_user_data_paths["audio_config.json"])

    try:
        config = await load_firestore_document( # Use the Firestore helper
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="config/audio_config", # Subpath to the audio config document
            default_data=DEFAULT_AUDIO_CONFIG.copy()
        )
        return {"personal_device": config.get("personal_device"), "system_device": config.get("system_device")}
    except Exception as e:
        logging.error(f"Error loading audio config for account {account_id} and user {aac_user_id}: {e}")
        return {"error": str(e)}



async def save_audio_config(account_id: str, aac_user_id: str, personal_device_id: Optional[int], system_device_id: Optional[int]) -> bool: # Now an async function, type hinting for IDs
    """Saves the audio device configuration to Firestore for a specific user."""
    config_to_save = {
        "personal_device": personal_device_id,
        "system_device": system_device_id
    }
    try:
        success = await save_firestore_document( # Use the Firestore helper
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="config/audio_config", # Subpath to the audio config document
            data_to_save=config_to_save # Now sending a dictionary
        )
        logging.info(f"Audio config saved for account {account_id} and user {aac_user_id}: {config_to_save}")
        return success
    except Exception as e:
        logging.error(f"Error saving audio config for account {account_id} and user {aac_user_id}: {e}")
        return False
    


@app.get("/audio-devices")
async def list_audio_devices():
    """
    Returns a list of available audio devices.
    """
#    devices = get_audio_devices()
#    if "error" in devices:
#        raise HTTPException(status_code=500, detail=devices["error"])
#    return JSONResponse(content=devices)




@app.get("/get-audio-devices-config")
async def get_audio_devices_config(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    config = await load_config(account_id, aac_user_id) # Call the now async load_config with both IDs
    if "error" in config: raise HTTPException(status_code=500, detail=config["error"])
    return JSONResponse(content=config)
    


# --- Request Body Model ---
class AnalyzeUrlRequest(BaseModel):
    """Defines the expected structure of the request body."""
    url: str
    keywords: List[str] = [] # Use List from typing
    sample_html: Optional[str] = None # Use Optional for optional fields



# --- API Endpoint ---
# Make sure this decorator points to your FastAPI app instance
@app.post("/api/analyze-url")
# --- THREADS FEATURE: Models, Firestore Helpers, Endpoints ---
###############################################################

class FavoriteLocationThread(BaseModel):
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    favorite_name: str  # Links to the favorite location
    location: str
    people: str  
    activity: str
    created_at: str  # ISO date string
    created_by: str  # aac_user_id
    last_message_at: Optional[str] = None  # ISO date string of last message

class ThreadMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thread_id: str
    content: str
    sender_type: str  # "user" (for AAC user responses) or "incoming" (for questions/comments from others)
    created_at: str  # ISO date string
    
# --- Thread Management Models ---
class OpenThreadRequest(BaseModel):
    favorite_name: str
    
class ThreadMessageRequest(BaseModel):
    content: str
    sender_type: str  # "user" or "incoming"

# --- Firestore Helpers for Threads ---
async def load_favorite_threads(account_id: str, aac_user_id: str) -> List[dict]:
    """Load all threads for a user."""
    return await load_firestore_collection(account_id, aac_user_id, "favorite_threads")

async def save_favorite_thread(account_id: str, aac_user_id: str, thread_data: dict) -> bool:
    """Save a new thread to Firestore."""
    threads = await load_favorite_threads(account_id, aac_user_id)
    threads.append(thread_data)
    return await save_firestore_collection_items(account_id, aac_user_id, "favorite_threads", threads)

async def update_favorite_thread(account_id: str, aac_user_id: str, thread_id: str, updated_data: dict) -> bool:
    """Update an existing thread in Firestore."""
    threads = await load_favorite_threads(account_id, aac_user_id)
    for i, thread in enumerate(threads):
        if thread.get("thread_id") == thread_id:
            threads[i] = {**thread, **updated_data}
            return await save_firestore_collection_items(account_id, aac_user_id, "favorite_threads", threads)
    return False

async def get_favorite_thread_by_name(account_id: str, aac_user_id: str, favorite_name: str) -> Optional[dict]:
    """Get a thread by favorite location name."""
    threads = await load_favorite_threads(account_id, aac_user_id)
    for thread in threads:
        if thread.get("favorite_name") == favorite_name:
            return thread
    return None

async def load_thread_messages(account_id: str, aac_user_id: str, thread_id: str) -> List[dict]:
    """Load all messages for a specific thread, sorted by created_at timestamp."""
    messages = await load_firestore_collection(account_id, aac_user_id, f"favorite_threads/{thread_id}/messages")
    
    # Sort messages by created_at timestamp to ensure chronological order
    if messages:
        try:
            messages.sort(key=lambda msg: msg.get('created_at', ''))
        except Exception as e:
            logging.warning(f"Failed to sort thread messages by created_at: {e}")
    
    return messages

async def save_thread_message(account_id: str, aac_user_id: str, thread_id: str, message_data: dict) -> bool:
    """Save a message to a thread and update thread's last_message_at."""
    # Save the message
    messages = await load_thread_messages(account_id, aac_user_id, thread_id)
    messages.append(message_data)
    messages_saved = await save_firestore_collection_items(account_id, aac_user_id, f"favorite_threads/{thread_id}/messages", messages)
    
    # Update thread's last_message_at
    if messages_saved:
        await update_favorite_thread(account_id, aac_user_id, thread_id, {
            "last_message_at": message_data.get("created_at")
        })
    
    return messages_saved

# --- Endpoints for Threads Feature ---

@app.post("/api/threads/open")
async def open_thread_endpoint(
    payload: OpenThreadRequest, 
    current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]
):
    """Open a thread for a favorite location. Creates thread if it doesn't exist."""
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    
    try:
        # First, check when the favorite location was loaded and validate favorite status
        current_state = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_state",
            default_data=DEFAULT_USER_CURRENT.copy()
        )
        
        # Check if location was loaded recently (within 4 hours)
        loaded_at_str = current_state.get("loaded_at")
        if not loaded_at_str:
            return {"success": False, "message": "Location not updated. Please update Locate and try again."}
        
        try:
            from datetime import datetime, timezone
            loaded_at = datetime.fromisoformat(loaded_at_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            hours_since_loaded = (now - loaded_at).total_seconds() / 3600
            
            if hours_since_loaded > 4:
                return {"success": False, "message": "Thread cancelled. Location not updated within the last 4 hours. Please load a Favorite Location and try again."}
        except ValueError:
            return {"success": False, "message": "Location timestamp invalid. Please update Locate and try again."}
        
        # Check if a favorite was loaded and is still valid
        favorite_name_from_state = current_state.get("favorite_name")
        saved_at_str = current_state.get("saved_at")
        
        # Validate that the requested favorite matches what was loaded
        if not favorite_name_from_state or favorite_name_from_state != payload.favorite_name:
            return {"success": False, "message": "Thread cancelled. Location not updated within the last 4 hours. Please load a Favorite Location and try again."}
        
        # Check if location was manually changed after loading favorite
        if saved_at_str:
            try:
                saved_at = datetime.fromisoformat(saved_at_str.replace('Z', '+00:00'))
                # If data was saved after the favorite was loaded, favorite is no longer valid
                if saved_at > loaded_at:
                    return {"success": False, "message": "Thread cancelled. Location was modified after loading favorite. Please reload the Favorite Location and try again."}
            except ValueError:
                # If we can't parse saved_at, be conservative and reject
                return {"success": False, "message": "Location timestamp invalid. Please reload the Favorite Location and try again."}
        
        # Load favorite details to get the full location info
        favorites_data = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_favorites",
            default_data={"favorites": []}
        )
        
        favorite = None
        for fav in favorites_data.get("favorites", []):
            if fav.get("name") == payload.favorite_name:
                favorite = fav
                break
        
        if not favorite:
            return {"success": False, "message": f"Favorite location '{payload.favorite_name}' not found."}
        
        # Check if thread already exists
        existing_thread = await get_favorite_thread_by_name(account_id, aac_user_id, payload.favorite_name)
        
        if existing_thread:
            # Load ALL messages for display
            messages = await load_thread_messages(account_id, aac_user_id, existing_thread["thread_id"])
            
            # Sort messages by created_at timestamp to ensure chronological order
            if messages:
                try:
                    messages.sort(key=lambda msg: msg.get('created_at', ''))
                except Exception as e:
                    logging.warning(f"Failed to sort thread messages by created_at: {e}")
            
            # Return all messages for display, and recent 5 for LLM context
            recent_messages_for_llm = messages[-5:] if len(messages) > 0 else []
            
            return {
                "success": True, 
                "thread": existing_thread,
                "all_messages": messages,  # All messages for display
                "recent_messages": recent_messages_for_llm,  # Last 5 for LLM context
                "is_new": False
            }
        else:
            # Create new thread
            from datetime import datetime, timezone
            now_iso = datetime.now(timezone.utc).isoformat()
            
            new_thread = FavoriteLocationThread(
                favorite_name=payload.favorite_name,
                location=favorite.get("location", ""),
                people=favorite.get("people", ""),
                activity=favorite.get("activity", ""),
                created_at=now_iso,
                created_by=aac_user_id
            )
            
            thread_data = new_thread.dict()
            success = await save_favorite_thread(account_id, aac_user_id, thread_data)
            
            if success:
                return {
                    "success": True, 
                    "thread": thread_data,
                    "recent_messages": [],
                    "is_new": True
                }
            else:
                return {"success": False, "message": "Failed to create thread."}
        
    except Exception as e:
        logging.error(f"Error opening thread: {e}")
        return {"success": False, "message": "Error opening thread."}

@app.get("/api/threads/{thread_id}/messages")
async def get_thread_messages_endpoint(
    thread_id: str, 
    current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]
):
    """Get all messages for a thread."""
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    messages = await load_thread_messages(account_id, aac_user_id, thread_id)
    return {"messages": messages}

@app.post("/api/threads/{thread_id}/messages")
async def post_message_to_thread_endpoint(
    thread_id: str, 
    payload: ThreadMessageRequest, 
    current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]
):
    """Add a message to a thread."""
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    
    message = ThreadMessage(
        thread_id=thread_id,
        content=payload.content,
        sender_type=payload.sender_type,
        created_at=now_iso
    )
    
    message_data = message.dict()
    success = await save_thread_message(account_id, aac_user_id, thread_id, message_data)
    
    if success:
        return {"success": True, "message": message_data}
    else:
        raise HTTPException(status_code=500, detail="Failed to save message.")



# --- THREADS FEATURE ---
# Threads are organized by Favorite Locations.
# Each favorite location can have one associated thread for communication history.






async def analyze_url_for_selectors(request_data: AnalyzeUrlRequest):
    """
    Analyzes a URL or HTML snippet to suggest CSS selectors for headlines and links,
    using an LLM for analysis.
    """
    url = str(request_data.url)
    keywords = request_data.keywords
    sample_html = request_data.sample_html # Get the sample HTML

    html_content = "" # Stores fetched HTML if needed
    determined_prefix = None # Stores the base URL (scheme + netloc)
    base_url = ""
    analysis_summary = "No structure analysis performed." # Default message
    llm_prompt = "" # Initialize prompt string

    # --- 1. Determine Base URL / Prefix (always needed) ---
    try:
        parsed_uri = urlparse(url)
        # Ensure scheme and netloc are present to form a valid base URL
        if parsed_uri.scheme and parsed_uri.netloc:
            base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
            # Basic check if it looks like an HTTP/HTTPS URL
            if base_url.startswith("http"):
                determined_prefix = base_url
        else:
            # Log if the URL doesn't seem to have a scheme or domain
            logging.warning(f"Could not determine scheme/netloc from URL: {url}")
    except Exception as e:
        # Log any errors during URL parsing
        logging.warning(f"Could not parse base URL from {url}: {e}")
        # Continue without prefix if parsing fails

    # --- 2. Choose Analysis Path and Prepare LLM Prompt ---
    if sample_html:
        # --- Path A: Analyze Provided HTML Snippet ---
        logging.info(f"Analyzing provided HTML snippet for {url}")
        # ***** UPDATED PROMPT for Sample HTML *****
        llm_prompt = f"""
Analyze the following HTML element snippet, which is a representative example of an article headline/link element from the webpage at URL: {url}

Example Element Snippet:
```html
{sample_html}
```
Keywords associated with desired content (if any): {', '.join(keywords) if keywords else 'None'}

Based primarily on the structure, tag name, attributes (especially classes like `gnt_m_flm_a` if present and relevant), and text content visible *in this snippet*, please derive the most likely, specific, yet robust CSS selectors to:

1.  Identify the primary ANCHOR TAG (`<a>`) containing the link for similar articles on the page. This is the **url_selector**.
2.  Identify the element containing the main headline TEXT for similar articles on the page. This is the **headline_selector**.

**Important Considerations:**
* If the headline text is directly inside the anchor tag itself (like in the example `<a class='some-class'>Headline Text</a>`), then the `headline_selector` might be the *same* as the `url_selector`, or it could target a more specific element *within* the anchor if one clearly contains *only* the text.
* Aim for selectors that are specific enough to target these article elements but not so specific that they would only match this single example if minor variations exist between items.
* **Prioritize using meaningful CSS classes** found on the anchor tag or headline element if they seem descriptive and likely to be repeated for similar items (e.g., `.article-link`, `.headline-text`, `.gnt_m_flm_a`). Avoid overly generic selectors like just 'a' or 'h2' unless no better option exists in the snippet.

Return your suggestions STRICTLY as a single JSON object with two keys:

"headline_selector": Your best guess CSS selector for the headline TEXT element (string or null if unsure).
"url_selector": Your best guess CSS selector for the ANCHOR TAG (`<a>`) (string or null if unsure).

Example JSON format:
{{ "option": "Did you hear about the new library opening downtown? They say it has some great features.", "summary": "New library opens" }}

JSON response:
""" # End of f-string for Path A prompt

    else:
        # --- Path B: Fetch and Analyze Whole Page (Fallback) ---
        logging.info(f"No sample HTML provided. Fetching and analyzing structure for {url}")
        try:
            # --- Fetch HTML ---
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            # Use a timeout for the request
            # Consider using a library like `httpx` which integrates better with asyncio
            async with aiohttp.ClientSession(headers=headers) as session:
                # Follow redirects (allow_redirects=True is default)
                # Added ssl=False for potential local SSL verification issues, review security implications for production
                async with session.get(url, timeout=15, ssl=False) as response:
                    # Raise an exception for bad status codes (4xx or 5xx)
                    response.raise_for_status()
                    # Store fetched HTML content
                    html_content = await response.text()
                    logging.info(f"Successfully fetched content ({len(html_content)} bytes) from {url}")

            # Check if content was actually retrieved
            if not html_content:
                raise ValueError("Retrieved empty content from URL in fallback.")

            # --- Analyze Structure (Basic) ---
            logging.info(f"Parsing HTML structure for {url}")
            soup = BeautifulSoup(html_content, 'html.parser')

            # Try to find common patterns for articles/links/headlines more intelligently
            # Prioritize elements within common container tags like <article>, <section>, <main>
            common_selectors = [
                'article a[href]', 'section a[href]', 'main a[href]', # Links within containers
                '.story a[href]', '.post a[href]', '.card a[href]', '.item a[href]', # Common class names
                'article h1', 'article h2', 'article h3', # Headlines within articles
                'section h1', 'section h2', 'section h3', # Headlines within sections
                '.story h1', '.story h2', '.story h3', '.post h1', '.post h2', '.post h3' # Headlines in common classes
            ]
            links_sample = []
            headlines_sample = []
            for selector in common_selectors:
                if 'a[href]' in selector and len(links_sample) < 15:
                    links_sample.extend(soup.select(selector, limit=15 - len(links_sample)))
                elif ('h1' in selector or 'h2' in selector or 'h3' in selector) and len(headlines_sample) < 15:
                     headlines_sample.extend(soup.select(selector, limit=15 - len(headlines_sample)))

            # Fallback if specific searches yield too few results
            if len(links_sample) < 5:
                links_sample.extend(soup.find_all('a', href=True, limit=15 - len(links_sample)))
            if len(headlines_sample) < 5:
                 headlines_sample.extend(soup.find_all(['h1', 'h2', 'h3', 'h4'], limit=15 - len(headlines_sample)))

            # Remove duplicates based on element object id
            links_sample = list({id(el): el for el in links_sample}.values())
            headlines_sample = list({id(el): el for el in headlines_sample}.values())

            structure_examples = []
            # Generate examples of link structures found
            logging.info(f"Found {len(links_sample)} potential link samples, {len(headlines_sample)} potential headline samples.")
            for link in links_sample[:10]: # Limit examples sent
                parent = link.parent
                grandparent = parent.parent if parent else None
                parent_classes = '.'.join(parent.get('class',[])) if parent and parent.get('class',[]) else ''
                grandparent_classes = '.'.join(grandparent.get('class',[])) if grandparent and grandparent.get('class',[]) else ''
                parent_info = f"<{parent.name}{'.' + parent_classes if parent_classes else ''}>" if parent else "None"
                grandparent_info = f"<{grandparent.name}{'.' + grandparent_classes if grandparent_classes else ''}>" if grandparent else "None"
                link_text_snippet = link.get_text(strip=True)[:70]
                link_href_snippet = link.get('href', '')[:50]
                structure_examples.append(f"- Link: <a href='{link_href_snippet}...'>{link_text_snippet}...</a> (Parent: {parent_info}, Grandparent: {grandparent_info})")

            # Generate examples of headline structures found
            for headline in headlines_sample[:10]: # Limit examples sent
                parent = headline.parent
                parent_classes = '.'.join(parent.get('class',[])) if parent and parent.get('class',[]) else ''
                parent_info = f"<{parent.name}{'.' + parent_classes if parent_classes else ''}>" if parent else "None"
                headline_text_snippet = headline.get_text(strip=True)[:80]
                headline_tag = headline.name
                headline_contains_link = " (contains <a>)" if headline.find('a', href=True) else ""
                structure_examples.append(f"- Headline: <{headline_tag}...>{headline_text_snippet}...</{headline_tag}>{headline_contains_link} (Parent: {parent_info})")

            # Create the summary string for the prompt
            if structure_examples:
                analysis_summary = "Potential Content Structures Found (sample):\n" + "\n".join(structure_examples) # Send gathered examples
            else:
                analysis_summary = "Could not automatically identify significant link/headline samples via basic structure analysis."
            logging.info(f"Generated analysis summary for LLM:\n{analysis_summary}")

            # --- Craft LLM prompt using page structure summary ---
            llm_prompt = f"""
Analyze the website structure based on its URL, keywords, and the following summary of potential content structures found on the page.
URL: {url}
Keywords: {', '.join(keywords) if keywords else 'None'}

Structure Summary:
{analysis_summary}

Based *only* on the information above (URL, keywords, structure summary), suggest the most likely, specific CSS selectors to reliably identify:

1.  The elements containing the main article or story headline text (**headline_selector**).
2.  The primary anchor tags (`<a>`) associated with those headlines/articles (**url_selector**).

Return suggestions STRICTLY as a single JSON object with two keys:

"headline_selector": Your best guess CSS selector for the element containing the headline TEXT (string or null if unsure).
"url_selector": Your best guess CSS selector for the ANCHOR TAG (`<a>`) (string or null if unsure).

Consider the likely relationship between headlines and links (e.g., link inside headline, headline inside link, link near headline). Aim for selectors specific enough to target only the main content articles/items, avoiding navigation, footers, or sidebars if possible based on common structures. If unsure, return null for a selector. Use classes and element hierarchy.

Example JSON format:
{{ "headline_selector": "h2.article-title", "url_selector": "article a.read-more" }}
Known Working Example for a different site (for reference only):
{{ "headline_selector": "#main > div a.article-title span.dfm-title", "url_selector": "#main > div a.article-title" }}

JSON response:
""" # End of f-string for Path B prompt (success)

        except aiohttp.ClientError as e:
            # Handle errors during the HTTP request
            logging.error(f"HTTP Client Error fetching {url} in fallback: {e}")
            analysis_summary = f"Could not fetch URL content: {e}"
            # Craft a simpler prompt asking for generic selectors if fetch failed
            llm_prompt = f"""
Could not fetch content from URL: {url}
Error: {e}
Keywords associated with desired content (if any): {', '.join(keywords) if keywords else 'None'}

Based *only* on the URL and keywords, suggest *common/generic* CSS selectors for typical news/blog headlines and their associated links, as fetching the page failed. Return null if no reasonable guess can be made.

Return your suggestions STRICTLY as a single JSON object with two keys:

"headline_selector": Your best guess CSS selector for the headline TEXT element (string or null).
"url_selector": Your best guess CSS selector for the ANCHOR TAG (`<a>`) (string or null if unsure).

Example JSON format: {{ "headline_selector": "h2.article-title", "url_selector": "article a.read-more" }}
Known Working Example for a different site (for reference only): {{ "headline_selector": "#main > div a.article-title span.dfm-title", "url_selector": "#main > div a.article-title" }}

JSON response:
""" # End of f-string for Path B prompt (fetch error)
        except Exception as e:
            # Catch other errors during BS4 analysis or other processing
            logging.exception(f"Error processing URL {url} structure analysis in fallback: {e}") # Use logging.exception to include traceback
            analysis_summary = f"Error analyzing HTML structure: {e}"
            # Craft simpler prompt if analysis failed
            llm_prompt = f"""
Error analyzing HTML structure for URL: {url}
Error: {e}
Keywords associated with desired content (if any): {', '.join(keywords) if keywords else 'None'}

Based *only* on the URL and keywords, suggest *common/generic* CSS selectors for typical news/blog headlines and their associated links, as analyzing the page structure failed. Return null if no reasonable guess can be made.

Return your suggestions STRICTLY as a single JSON object with two keys:

"headline_selector": Your best guess CSS selector for the element containing the headline TEXT (string or null).
"url_selector": Your best guess CSS selector for the ANCHOR TAG (`<a>`) (string or null if unsure).

Example JSON format: {{ "headline_selector": "h2.article-title", "url_selector": "article a.read-more" }}
Known Working Example for a different site (for reference only): {{ "headline_selector": "#main > div a.article-title span.dfm-title", "url_selector": "#main > div a.article-title" }}

JSON response:
""" # End of f-string for Path B prompt (analysis error)

    # --- 3. Call LLM (if a prompt was generated) ---
    llm_suggestion = None # Default value
    extracted_llm_json_string = None # Store the raw JSON string found

    if not llm_prompt:
        # This should ideally not happen if logic above is correct, but safety check
        logging.error("LLM prompt was not generated. Cannot call LLM.")
        final_response = {"headline_selector": None, "url_selector": None, "url_prefix": determined_prefix}
        return JSONResponse(content=final_response)
    elif not genai:
         logging.error("GenAI library not configured or failed to initialize. Skipping LLM call.")
         final_response = {"headline_selector": None, "url_selector": None, "url_prefix": determined_prefix}
         # Optionally, return a specific error message to the frontend
         # raise HTTPException(status_code=503, detail="AI analysis service is unavailable.")
         return JSONResponse(content=final_response)
    else:
        # Proceed with LLM call only if a prompt was successfully generated and genai is available
        try:
            logging.info(f"--- Sending Prompt to LLM ({GEMINI_PRIMARY_MODEL}) for {url} ---")
            # logging.debug(llm_prompt) # Use debug level for potentially large prompts
            logging.info("--- End of Prompt ---")

            # Use the new helper function for LLM call with fallback
            llm_response  = await _generate_gemini_content_with_fallback(llm_prompt)

            # Access the text part of the response safely
            llm_output_text = ""
            try:
                # Recommended way for newer versions (check genai library documentation)
                # This assumes generate_content returns an object with a 'parts' attribute
                # If it returns a simple string or different structure, adjust accordingly.
                 if hasattr(llm_response, 'parts') and isinstance(llm_response.parts, list):
                    llm_output_text = "".join(part.text for part in llm_response.parts if hasattr(part, 'text'))
                 elif hasattr(llm_response, 'text'):
                     llm_output_text = llm_response.text # Fallback for simpler response structure
                 else:
                     # If the structure is unknown, log the response type and try converting to string
                     logging.warning(f"Unexpected LLM response structure type: {type(llm_response)}. Attempting str().")
                     llm_output_text = str(llm_response)

            except Exception as resp_e:
                 logging.error(f"Error extracting text from LLM response object: {resp_e}")
                 # Decide how to handle - maybe raise, maybe return empty suggestion
                 raise ValueError(f"Unsupported LLM response structure or extraction error: {resp_e}")


            llm_output_text = llm_output_text.strip()
            # Log the raw output clearly
            logging.info(f"--- LLM Raw Output for {url} ---")
            logging.info(llm_output_text)
            logging.info("--- End of LLM Raw Output ---")


            # --- 4. Parse LLM Response ---
            # Use regex to find a JSON object within the response text
            # re.DOTALL makes '.' match newlines as well
            # Updated regex to be less greedy and handle potential surrounding text
            match = re.search(r'\{[\s\S]*\}', llm_output_text) # Look for {} block, allowing any char including newline

            if match:
                extracted_llm_json_string = match.group(0) # Get the matched JSON string
                logging.info(f"Extracted JSON string: {extracted_llm_json_string}")
                try:
                    # Attempt to parse the extracted string as JSON
                    llm_suggestion = json.loads(extracted_llm_json_string)

                    # --- Basic validation of the parsed JSON structure ---
                    if not isinstance(llm_suggestion, dict):
                         logging.warning(f"LLM suggestion is not a dictionary: {llm_suggestion}")
                         llm_suggestion = None
                    elif "headline_selector" not in llm_suggestion or "url_selector" not in llm_suggestion:
                         logging.warning(f"LLM suggestion missing required keys ('headline_selector', 'url_selector'): {llm_suggestion}")
                         llm_suggestion = None # Discard invalid structure
                    else:
                        # --- Further validation: check if values are strings or None ---
                        h_sel = llm_suggestion.get("headline_selector")
                        u_sel = llm_suggestion.get("url_selector")
                        if (h_sel is not None and not isinstance(h_sel, str)) or \
                           (u_sel is not None and not isinstance(u_sel, str)):
                            logging.warning(f"LLM suggestion values are not strings or null: {llm_suggestion}")
                            llm_suggestion = None # Discard invalid types
                        else:
                             logging.info(f"Successfully parsed LLM suggestion: {llm_suggestion}")


                except json.JSONDecodeError as json_e:
                    # Handle cases where the extracted string is not valid JSON
                    logging.warning(f"Could not decode JSON from LLM suggestion: {json_e}. String was: '{extracted_llm_json_string}'")
                    llm_suggestion = None # Discard invalid JSON
            else:
                # Handle cases where no JSON object is found in the response
                logging.warning(f"Could not find JSON object in LLM suggestion output.")
                llm_suggestion = None # Discard if no JSON object found

        except Exception as e:
            # Catch any other errors during the LLM call or processing
            logging.exception(f"ERROR: Error during LLM call or processing for {url}: {e}")
            # Continue without LLM suggestions if the call fails, llm_suggestion remains None

    # --- 5. Prepare Final Response ---
    # Safely get selectors from the suggestion, defaulting to None if suggestion is invalid/missing
    final_response = {
        "headline_selector": llm_suggestion.get("headline_selector") if llm_suggestion else None,
        "url_selector": llm_suggestion.get("url_selector") if llm_suggestion else None,
        "url_prefix": determined_prefix # Determined earlier
    }

    # --- 6. Optional: Verify selectors ---
    # Verification only makes sense if html_content was successfully fetched (in fallback mode)
    # and if the LLM actually provided selectors.
    if html_content and not sample_html and llm_suggestion:
        logging.info("--- Verifying suggested selectors ---")
        try:
            # Re-parse the fetched HTML for verification
            soup = BeautifulSoup(html_content, 'html.parser')

            # Verify headline selector if suggestion exists and is a non-empty string
            headline_sel = final_response.get("headline_selector")
            if headline_sel: # Only verify if not None/empty
                try:
                    found_headlines = soup.select(headline_sel)
                    count = len(found_headlines)
                    logging.info(f"Verification: Headline selector '{headline_sel}' found {count} elements.")
                    if count == 0:
                        logging.warning(f"Verification Warning: Suggested headline selector found 0 elements.")
                        # Decide whether to clear the suggestion if verification fails:
                        # final_response["headline_selector"] = None
                except Exception as select_e:
                    # Catch errors like invalid CSS selector syntax
                    logging.warning(f"Verification Warning: Error applying headline selector '{headline_sel}': {select_e}")
                    # Optionally clear invalid selector
                    # final_response["headline_selector"] = None

            # Verify URL selector if suggestion exists and is a non-empty string
            url_sel = final_response.get("url_selector")
            if url_sel: # Only verify if not None/empty
                try:
                    found_links = soup.select(url_sel)
                    count = len(found_links)
                    logging.info(f"Verification: URL selector '{url_sel}' found {count} elements.")
                    if count == 0:
                        logging.warning(f"Verification Warning: Suggested url selector found 0 elements.")
                        # Decide whether to clear the suggestion if verification fails:
                        # final_response["url_selector"] = None
                except Exception as select_e:
                    logging.warning(f"Verification Warning: Error applying URL selector '{url_sel}': {select_e}")
                    # Optionally clear invalid selector
                    # final_response["url_selector"] = None

        except Exception as bs_e:
            # Catch errors during BeautifulSoup parsing for verification
            logging.warning(f"Warning: Error during selector verification step (parsing HTML): {bs_e}")

    # --- 7. Return final suggestions ---
    logging.info(f"Returning analysis suggestions for {url}: {final_response}")
    return JSONResponse(content=final_response)



# --- Pydantic Models (Using V2 @field_validator) ---
class SettingsModel(BaseModel):
    scanDelay: Optional[int] = Field(None, description="Auditory scan delay in milliseconds.", gt=99)
    wakeWordInterjection: Optional[str] = Field(None, description="The interjection part of the wake word (e.g., 'Hey').", min_length=1, max_length=50)
    wakeWordName: Optional[str] = Field(None, description="The name part of the wake word (e.g., 'Brady').", min_length=1, max_length=50)
    CountryCode: Optional[str] = Field(None, description="Country code for holiday lookups (e.g., US, CA).", min_length=2, max_length=2)
    speech_rate: Optional[int] = Field(None, description="Speech rate in WPM (e.g., 100-300).", gt=49, lt=401) # Added speech_rate
    LLMOptions: Optional[int] = Field(None, description="Number of options returned by LLM (e.g., 1-50)", ge=1, le=50) 
    FreestyleOptions: Optional[int] = Field(20, description="Number of word options returned for freestyle communication (e.g., 1-50)", ge=1, le=50)
    llm_provider: Optional[str] = Field(None, description="LLM provider choice: 'gemini' or 'chatgpt'.", min_length=3)
    ScanningOff: Optional[bool] = Field(None, description="Enable/disable scanning of off-screen elements.") # Added ScanningOff
    SummaryOff: Optional[bool] = Field(None, description="Enable/disable summary generation.") # Added SummaryOff    
    selected_tts_voice_name: Optional[str] = None
    gridColumns: Optional[int] = Field(None, description="Number of columns displayed in grid", ge=2, le=18)
    lightColorValue: Optional[int] = Field(None, description="Color value for light theme (e.g., 4294779156).", gt=0)
    darkColorValue: Optional[int] = Field(None, description="Color value for dark theme (e.g., 4294901764).", gt=0)
    scanLoopLimit: Optional[int] = Field(None, description="Scan loop limit (0 for unlimited, 1-10 for limit).", ge=0, le=10)
    toolbarPIN: Optional[str] = Field(None, description="PIN code for toolbar access.", min_length=4, max_length=4)
    autoClean: Optional[bool] = Field(None, description="Enable/disable automatic cleanup on Speak Display.") # Added autoClean
    displaySplash: Optional[bool] = Field(None, description="Enable/disable splash screen display when announcing text.")
    displaySplashTime: Optional[int] = Field(None, description="Duration in milliseconds to display splash screen.", ge=500, le=10000)
    enableMoodSelection: Optional[bool] = Field(None, description="Enable/disable mood selection at session start.")
    enablePictograms: Optional[bool] = Field(None, description="Enable/disable AAC pictogram display on buttons.")


    @field_validator('wakeWordInterjection', 'wakeWordName', 'CountryCode', mode='before')
    @classmethod
    def strip_and_convert_empty_to_none(cls, value: Any) -> Optional[str]: # Use Any for input type robustness
        if isinstance(value, str):
            stripped_value = value.strip()
            return stripped_value if stripped_value else None
        return value # Return non-strings (like None) as is

    @field_validator('CountryCode', mode='before') # speech_rate is int, no need for uppercase
    @classmethod
    def ensure_uppercase_codes(cls, value: Any) -> Optional[str]:
        if isinstance(value, str) and value:
            return value.strip().upper() # Add strip here too
        return value
    

class VoiceDetail(BaseModel):
    name: str
    language_codes: List[str]
    natural_sample_rate_hertz: int
    ssml_gender: str

class TestTTSVoiceRequest(BaseModel):
    voice_name: str
    text: str = "This is a test of the selected voice."


# --- Helper Functions ---

async def load_settings_from_file(account_id: str, aac_user_id: str) -> Dict:
    """
    Loads settings from Firestore for a specific user, returning defaults if error/missing.
    """
    return await load_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="settings/app_settings",
        default_data=DEFAULT_SETTINGS.copy()
    )


async def save_settings_to_file(account_id: str, aac_user_id: str, settings_data_to_save: Dict) -> bool:
    """
    Saves settings to Firestore for a specific user.
    It loads current settings, updates them with new valid data, and saves back.
    """
    # DEBUG: Log FreestyleOptions in incoming data
    if 'FreestyleOptions' in settings_data_to_save:
        logging.warning(f"DEBUG save_settings_to_file - FreestyleOptions in incoming data: {settings_data_to_save['FreestyleOptions']}")
    
    # Load current settings first to merge and retain unspecified fields
    current_settings = await load_settings_from_file(account_id, aac_user_id)
    
    # DEBUG: Log current FreestyleOptions before merge
    logging.warning(f"DEBUG save_settings_to_file - FreestyleOptions in current_settings before merge: {current_settings.get('FreestyleOptions', 'NOT_FOUND')}")
    
    # Remove any keys not defined in DEFAULT_SETTINGS before merging to avoid storing junk
    sanitized_data_to_save = {k: v for k, v in settings_data_to_save.items() if k in DEFAULT_SETTINGS}
    
    # DEBUG: Log FreestyleOptions after sanitization
    if 'FreestyleOptions' in sanitized_data_to_save:
        logging.warning(f"DEBUG save_settings_to_file - FreestyleOptions in sanitized_data: {sanitized_data_to_save['FreestyleOptions']}")
    else:
        logging.warning(f"DEBUG save_settings_to_file - FreestyleOptions NOT in sanitized_data. Original keys: {list(settings_data_to_save.keys())}, DEFAULT_SETTINGS keys: {list(DEFAULT_SETTINGS.keys())}")
    
    # Merge (update existing defaults with new sanitized data)
    current_settings.update(sanitized_data_to_save)
    
    # DEBUG: Log FreestyleOptions in final merged settings
    logging.warning(f"DEBUG save_settings_to_file - FreestyleOptions in final merged settings: {current_settings.get('FreestyleOptions', 'NOT_FOUND')}")

    return await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="settings/app_settings", # Firestore path
        data_to_save=current_settings # Save the merged dict
    )

# --- API Endpoints ---

# /api/settings
@app.get("/api/settings", response_model=SettingsModel)
async def get_settings(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    logging.info(f"GET /api/settings request received for acccount {account_id} and user {aac_user_id}.")
    settings_dict = await load_settings_from_file(account_id, aac_user_id) # Get as dict
    # Create an instance of SettingsModel from the dict
    settings_model_instance = SettingsModel(**settings_dict) 
    # FastAPI will handle the serialization to JSON, no need for .model_dump() here
    # because response_model=SettingsModel is already specified
    return settings_model_instance # Return the Pydantic instance directly

@app.post("/api/settings", response_model=SettingsModel)
async def save_settings_endpoint(settings_update: SettingsModel, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]): # ADD user_id
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    is_demo_mode = current_ids.get("is_demo_mode", False)

    update_data = settings_update.model_dump(exclude_unset=True)
    logging.info(f"POST /api/settings request received for account {account_id} and user {aac_user_id} with update data: {update_data}")
    
    # DEBUG: Log FreestyleOptions specifically
    if 'FreestyleOptions' in update_data:
        logging.warning(f"DEBUG FreestyleOptions - Received value in update_data: {update_data['FreestyleOptions']}")
    
    # Demo mode: return current settings without saving (temporary session changes)
    if is_demo_mode:
        logging.info(f"Demo mode: Settings changes not persisted for account {account_id}")
        # Return the requested settings as if they were saved (temporary session behavior)
        current_settings = await load_settings_from_file(account_id, aac_user_id)
        current_settings.update(update_data)  # Apply changes temporarily
        return JSONResponse(content=SettingsModel(**current_settings).model_dump())
    
    # Regular mode: save settings normally
    success = await save_settings_to_file(account_id, aac_user_id, update_data)

    if success:
        # Await load_settings_from_file to get the actual dictionary
        saved_settings_dict = await load_settings_from_file(account_id, aac_user_id)
        
        # CRITICAL FIX: Invalidate relevant caches after settings update
        try:
            await cache_manager.invalidate_cache(account_id, aac_user_id)
            logging.info(f"Invalidated cache for account {account_id}, user {aac_user_id} after settings update")
        except Exception as e:
            logging.error(f"Failed to invalidate caches after settings update: {e}")
        
        # JSONResponse expects a dictionary, not a Pydantic model here.
        # Using model_dump on the SettingsModel with saved_settings_dict will structure it correctly for JSON.
        return JSONResponse(content=SettingsModel(**saved_settings_dict).model_dump())
    else:
        raise HTTPException(status_code=500, detail="Failed to save settings to Firestore.")

@app.get("/api/account/toolbar-pin")
async def get_toolbar_pin(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """Get the current toolbar PIN."""
    try:
        account_id = current_ids["account_id"]
        aac_user_id = current_ids["aac_user_id"]
        settings = await load_settings_from_file(account_id, aac_user_id)
        return {"pin": settings.get("toolbarPIN", "")}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to load toolbar PIN.")

@app.put("/api/account/toolbar-pin")
async def update_toolbar_pin(
    pin_data: dict,
    current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]
):
    """Update the toolbar PIN."""
    try:
        account_id = current_ids["account_id"]
        aac_user_id = current_ids["aac_user_id"]
        # Accept both 'pin' and 'toolbarPIN' field names for compatibility
        pin = pin_data.get("toolbarPIN", pin_data.get("pin", ""))
        current_settings = await load_settings_from_file(account_id, aac_user_id)
        current_settings["toolbarPIN"] = pin
        success = await save_settings_to_file(account_id, aac_user_id, current_settings)
        if success:
            return {"message": "Toolbar PIN updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save toolbar PIN.")
    except Exception as e:
        logging.error(f"Error updating toolbar PIN: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update toolbar PIN: {str(e)}")

# NEW: Model for account update requests
class UpdateAccountRequest(BaseModel):
    account_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    therapist_email: Optional[str] = None
    is_therapist: Optional[bool] = None
    allow_admin_access: Optional[bool] = None

# NEW: Model for admin account selection
class SelectAccountRequest(BaseModel):
    account_id: str

# NEW: Get account details for editing
@app.get("/api/account/details")
async def get_account_details(current_account: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]):
    """Get account details for editing."""
    global firestore_db
    if not firestore_db:
        raise HTTPException(status_code=503, detail="Firestore DB client not initialized.")
    
    try:
        account_id = current_account["account_id"]
        account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id)
        account_doc = await asyncio.to_thread(account_doc_ref.get)
        
        if not account_doc.exists:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account_data = account_doc.to_dict()
        
        # Return only the fields that can be edited
        return {
            "email": account_data.get("email", ""),
            "account_name": account_data.get("account_name", ""),
            "address": account_data.get("address", ""),
            "phone": account_data.get("phone", ""),
            "therapist_email": account_data.get("therapist_email", ""),
            "is_therapist": account_data.get("is_therapist", False),
            "allow_admin_access": account_data.get("allow_admin_access", True)
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching account details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch account details")

# NEW: Update account details
@app.post("/api/account/update")
async def update_account_details(
    update_data: UpdateAccountRequest,
    current_account: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]
):
    """Update account details."""
    global firestore_db
    if not firestore_db:
        raise HTTPException(status_code=503, detail="Firestore DB client not initialized.")
    
    try:
        account_id = current_account["account_id"]
        account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id)
        
        # Build update data, only including fields that were provided
        update_fields = {}
        if update_data.account_name is not None:
            update_fields["account_name"] = update_data.account_name
        if update_data.address is not None:
            update_fields["address"] = update_data.address
        if update_data.phone is not None:
            update_fields["phone"] = update_data.phone
        if update_data.therapist_email is not None:
            update_fields["therapist_email"] = update_data.therapist_email
        if update_data.is_therapist is not None:
            update_fields["is_therapist"] = update_data.is_therapist
        if update_data.allow_admin_access is not None:
            update_fields["allow_admin_access"] = update_data.allow_admin_access
        
        update_fields["last_updated"] = dt.now().isoformat()
        
        await asyncio.to_thread(account_doc_ref.update, update_fields)
        
        return {"message": "Account updated successfully"}
    except Exception as e:
        logging.error(f"Error updating account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update account")

# NEW: Get accounts accessible by admin/therapist
@app.get("/api/admin/accessible-accounts")
async def get_accessible_accounts(current_account: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]):
    """Get accounts that admin/therapist can access."""
    global firestore_db
    if not firestore_db:
        raise HTTPException(status_code=503, detail="Firestore DB client not initialized.")
    
    try:
        account_id = current_account["account_id"]
        
        # Get current user's account to check if they're admin or therapist
        current_account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id)
        current_account_doc = await asyncio.to_thread(current_account_doc_ref.get)
        
        if not current_account_doc.exists:
            raise HTTPException(status_code=404, detail="Current account not found")
        
        current_account_data = current_account_doc.to_dict()
        user_email = current_account_data.get("email", "")
        is_admin = user_email == "admin@talkwithbravo.com"
        is_therapist = current_account_data.get("is_therapist", False)
        
        if not is_admin and not is_therapist:
            raise HTTPException(status_code=403, detail="Access denied: Not an admin or therapist")
        
        # Query all accounts
        accounts_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION)
        all_accounts = await asyncio.to_thread(list, accounts_ref.stream())
        
        accessible_accounts = []
        for account_doc in all_accounts:
            account_data = account_doc.to_dict()
            
            # Admin can access all accounts that allow admin access
            if is_admin:
                if account_data.get("allow_admin_access", True):  # Default to True if not set
                    accessible_accounts.append({
                        "account_id": account_doc.id,
                        "account_name": account_data.get("account_name", ""),
                        "email": account_data.get("email", "")
                    })
            # Therapists can access accounts where they're listed as therapist_email
            elif is_therapist:
                if account_data.get("therapist_email") == user_email:
                    accessible_accounts.append({
                        "account_id": account_doc.id,
                        "account_name": account_data.get("account_name", ""),
                        "email": account_data.get("email", "")
                    })
        
        return accessible_accounts
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting accessible accounts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get accessible accounts")

# NEW: Select account for admin/therapist access
@app.post("/api/admin/select-account")
async def select_account_for_access(
    request_data: SelectAccountRequest,
    current_account: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]
):
    """Select an account for admin/therapist to access."""
    global firestore_db
    if not firestore_db:
        raise HTTPException(status_code=503, detail="Firestore DB client not initialized.")
    
    try:
        current_account_id = current_account["account_id"]
        target_account_id = request_data.account_id
        
        # Get current user's account to verify permissions
        current_account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(current_account_id)
        current_account_doc = await asyncio.to_thread(current_account_doc_ref.get)
        
        if not current_account_doc.exists:
            raise HTTPException(status_code=404, detail="Current account not found")
        
        current_account_data = current_account_doc.to_dict()
        user_email = current_account_data.get("email", "")
        is_admin = user_email == "admin@talkwithbravo.com"
        is_therapist = current_account_data.get("is_therapist", False)
        
        if not is_admin and not is_therapist:
            raise HTTPException(status_code=403, detail="Access denied: Not an admin or therapist")
        
        # Get target account to verify access permissions
        target_account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(target_account_id)
        target_account_doc = await asyncio.to_thread(target_account_doc_ref.get)
        
        if not target_account_doc.exists:
            raise HTTPException(status_code=404, detail="Target account not found")
        
        target_account_data = target_account_doc.to_dict()
        
        # Verify access permissions
        has_access = False
        if is_admin and target_account_data.get("allow_admin_access", True):
            has_access = True
        elif is_therapist and target_account_data.get("therapist_email") == user_email:
            has_access = True
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied to this account")
        
        # Return success - the frontend will handle switching context
        return {
            "message": "Account access granted", 
            "account_id": target_account_id,
            "account_name": target_account_data.get("account_name", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error selecting account for access: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to select account")

# NEW: Get user profiles for admin-selected account
@app.get("/api/admin/account-users/{account_id}")
async def get_admin_account_users(
    account_id: str,
    firebase_user: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]
):
    """Get user profiles for a specific account (admin/therapist access)."""
    global firestore_db
    if not firestore_db:
        raise HTTPException(status_code=503, detail="Firestore DB client not initialized.")
    
    try:
        # Get the Firebase user UID (this is the admin/therapist's UID)
        admin_firebase_uid = firebase_user["account_id"]
        
        # Get admin/therapist account to verify permissions
        admin_account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(admin_firebase_uid)
        admin_account_doc = await asyncio.to_thread(admin_account_doc_ref.get)
        
        if not admin_account_doc.exists:
            raise HTTPException(status_code=404, detail="Admin account not found")
        
        admin_account_data = admin_account_doc.to_dict()
        user_email = admin_account_data.get("email", "")
        is_admin = user_email == "admin@talkwithbravo.com"
        is_therapist = admin_account_data.get("is_therapist", False)
        
        if not is_admin and not is_therapist:
            raise HTTPException(status_code=403, detail="Access denied: Not an admin or therapist")
        
        # Get target account to verify access permissions
        target_account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id)
        target_account_doc = await asyncio.to_thread(target_account_doc_ref.get)
        
        if not target_account_doc.exists:
            raise HTTPException(status_code=404, detail="Target account not found")
        
        target_account_data = target_account_doc.to_dict()
        
        # Verify access permissions
        has_access = False
        if is_admin and target_account_data.get("allow_admin_access", True):
            has_access = True
        elif is_therapist and target_account_data.get("therapist_email") == user_email:
            has_access = True
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied to this account")
        
        # Get user profiles for the target account
        users_collection_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
        
        docs = await asyncio.to_thread(users_collection_ref.stream)
        
        user_profiles = []
        for doc in docs:
            profile_data = doc.to_dict()
            if profile_data:
                user_profiles.append({
                    "aac_user_id": doc.id,
                    "display_name": profile_data.get("display_name", doc.id),
                })
        
        logging.info(f"Admin/therapist fetched {len(user_profiles)} user profiles for account {account_id}")
        return JSONResponse(content=user_profiles)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting admin account users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get account users")

@app.get("/api/available-llm-models")
async def get_available_llm_models():
    """Returns a list of available LLM models suitable for generateContent."""
    try:
        if not genai: # Check if genai is configured
            raise HTTPException(status_code=503, detail="Generative AI service not configured.")
        
        models_list = []
        filtered_models = []
        # Regex to identify models we might want to exclude (e.g., specific old versions, some previews)
        # This excludes models ending in -001, -002, etc., or -preview-MMDD
        exclude_pattern = re.compile(r"(-[0-9]{3,}|-preview-[0-9]{4,})$")

        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                model_name = m.name

                # Filter out experimental models
                if "exp" in model_name.lower():
                    continue

                # Filter out models matching the exclude pattern (unless it's a 'latest' model)
                if exclude_pattern.search(model_name) and not model_name.endswith("-latest"):
                    continue
                
                filtered_models.append(model_name)
        
        return JSONResponse(content={"models": sorted(list(set(filtered_models)))}) # Sort and unique
                
    except Exception as e:
        logging.error(f"Error fetching available LLM models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not retrieve LLM models: {str(e)}")



@app.get("/api/tts-voices", response_model=List[VoiceDetail])
async def get_tts_voices_endpoint():
    if not tts_client:
        raise HTTPException(status_code=503, detail="TTS client not available")
    try:
        response = tts_client.list_voices(language_code="en-US") # Filter for en-US directly
        voices = []
        for voice in response.voices:
            voices.append(VoiceDetail(
                name=voice.name,
                language_codes=list(voice.language_codes),
                natural_sample_rate_hertz=voice.natural_sample_rate_hertz,
                ssml_gender=google_tts.SsmlVoiceGender(voice.ssml_gender).name
            ))
        voices.sort(key=lambda v: v.name) # Sort for consistent UI
        return voices
    except Exception as e:
        logging.error(f"Error fetching TTS voices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching TTS voices: {str(e)}")
    


# /api/test-tts-voice OLD VERSION
"""
@app.post("/api/test-tts-voice")
async def test_tts_voice_endpoint(request_data: TestTTSVoiceRequest, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"] # Get account_id
    if not tts_client: raise HTTPException(status_code=503, detail="TTS client not available")
    try:
        # Load audio settings from Firestore using both IDs
        current_audio_settings = await load_config(account_id, aac_user_id) # Call the now async load_config
        system_device_index = current_audio_settings.get("system_device")
        logging.info(f"Testing TTS voice for user {aac_user_id} (account {account_id}): {request_data.voice_name} on device index: {system_device_index} with text: '{request_data.text}'")

        # The `play_audio_data` function is not defined in your provided server.py,
        # but assuming it's intended to be a local helper or frontend interaction.
        # If it's a backend helper, it should also be updated to receive these parameters.
        # For this context, we assume it's fine or needs your local adjustment.
        # play_audio_data(response.audio_content, sample_rate, system_device_index) # This line likely needs to be removed or adapted depending on its role.

        # If the purpose is just to synthesize and return or trigger a frontend play
        # you might need to synthesize here using `synthesize_speech_to_bytes` then return it.
        audio_bytes, sample_rate = await synthesize_speech_to_bytes(
            text=request_data.text,
            voice_name=request_data.voice_name,
            wpm_rate=DEFAULT_SPEECH_RATE # Or get from settings
        )
        # You'd then typically return this audio as a base64 string
        import base64
        encoded_audio = base64.b64encode(audio_bytes).decode('utf-8')
        return JSONResponse(content={
            "message": "Test sound synthesized successfully.",
            "audio_data": encoded_audio,
            "sample_rate": sample_rate,
            "system_device_index": system_device_index # Return this to frontend
        })

    except Exception as e:
        logging.error(f"Error testing TTS voice for user {aac_user_id} in account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error testing voice: {str(e)}")
"""


@app.post("/api/test-tts-voice")
async def test_tts_voice_endpoint(request_data: TestTTSVoiceRequest, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    if not tts_client:
        raise HTTPException(status_code=503, detail="TTS client not available")
    try:
        current_audio_settings = await load_config(account_id, aac_user_id)
        system_device_index = current_audio_settings.get("system_device")
        logging.info(f"Testing TTS voice for user {aac_user_id} (account {account_id}): {request_data.voice_name} on device index: {system_device_index} with text: '{request_data.text}'")

        audio_bytes, sample_rate = await synthesize_speech_to_bytes(
            text=request_data.text,
            voice_name=request_data.voice_name,
            wpm_rate=DEFAULT_SPEECH_RATE
        )

        # Save audio to a unique file in the static directory
        filename = f"tts_test_{uuid.uuid4().hex}.wav"
        file_path = os.path.join(static_file_path, filename)
        with open(file_path, "wb") as f:
            f.write(audio_bytes)

        # Build the public URL (adjust domain as needed)
        audio_url = f"https://{DOMAIN}/static/{filename}"

        return JSONResponse(content={
            "message": "Test sound synthesized successfully.",
            "audio_url": audio_url,
            "sample_rate": sample_rate,
            "system_device_index": system_device_index
        })

    except Exception as e:
        logging.error(f"Error testing TTS voice for user {aac_user_id} in account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error testing voice: {str(e)}")
    

# --- Custom Observances Data ---
FIXED_OBSERVANCES = [
    {"month": 2, "day": 14, "name": "Valentine's Day"},
    {"month": 3, "day": 17, "name": "St. Patrick's Day"},
    {"month": 10, "day": 31, "name": "Halloween"},
    # Add more fixed date observances here
]




def get_nth_weekday_of_month(year: int, month: int, weekday_to_find: int, n: int) -> Optional[date]:
    """ Helper to find dates like '2nd Sunday in May'. weekday_to_find: 0=Mon, 6=Sun """
    month_calendar = calendar.monthcalendar(year, month)
    count = 0
    found_date = None
    for week_data in month_calendar:
        if week_data[weekday_to_find] != 0: # Day exists in this week
            count += 1
            if count == n:
                found_date = date(year, month, week_data[weekday_to_find])
                break
    # For "last" (n=-1) or if n is too large (e.g. 5th Sunday when only 4 exist)
    if (n == -1 and not found_date) or (n > count and not found_date):
        for week_data in reversed(month_calendar):
            if week_data[weekday_to_find] != 0:
                found_date = date(year, month, week_data[weekday_to_find])
                break
    return found_date


# --- Easter Sunday Calculation ---
def calc_easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4      
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


# --- Updated Helper Function for Holidays & Observances ---
async def get_upcoming_holidays_and_observances(account_id: str, aac_user_id: str, days_ahead=14) -> List[str]:
    aac_user_id = aac_user_id
    account_id = account_id
    
    settings = await load_settings_from_file(account_id=account_id, aac_user_id=aac_user_id)
    country_code = settings.get('CountryCode') or DEFAULT_SETTINGS['CountryCode']

    if not country_code or not isinstance(country_code, str) or len(country_code) != 2:
        logging.warning(f"Invalid country_code for holidays: '{country_code}'. Using 'US'.")
        country_code = 'US'

    today = date.today()
    events_by_date = {}

    def add_event(event_date: date, name: str):
        date_str = event_date.isoformat()
        if date_str not in events_by_date:
            events_by_date[date_str] = []
        if name not in events_by_date[date_str]: # Avoid duplicates
            events_by_date[date_str].append(name)

    # 1. Get official holidays
    try:
        country_holidays_instance = holidays.CountryHoliday(country_code, observed=True)
        logging.info(f"Holiday instance created for Country: {country_code} (country-wide).")
        for d_offset in range(days_ahead + 1):
            current_date_to_check = today + timedelta(days=d_offset)
            holiday_name = country_holidays_instance.get(current_date_to_check)
            if holiday_name:
                add_event(current_date_to_check, holiday_name)
    except KeyError: # If country code is not found by 'holidays' library
        logging.warning(f"Official holiday data not available for Country: {country_code}.")
        # No need to add a note to events_by_date, it's just a warning.
        # add_event(today, f"Official holiday data not available for {country_code}") # Remove explicit text here
    except Exception as e: # Catch other potential issues
        logging.error(f"Error initializing holidays library for {country_code}: {e}", exc_info=True)
        # add_event(today, f"Error initializing holiday data for {country_code}") # Remove explicit text here


    # 2. Add Fixed Observances
    for year_offset in range(2): # Check current year and next year if range crosses over
        current_year = today.year + year_offset
        for obs in FIXED_OBSERVANCES:
            try:
                obs_date = date(current_year, obs["month"], obs["day"])
                if today <= obs_date <= today + timedelta(days=days_ahead):
                    add_event(obs_date, obs["name"])
            except ValueError: # Invalid date (e.g. Feb 29)
                pass

    # 3. Add Floating Observances (example for US)
    for year_offset in range(2):
        current_year = today.year + year_offset
        if country_code == 'US': # Add more country/region specific rules as needed
            # Mother's Day (2nd Sunday in May)
            mothers_day = get_nth_weekday_of_month(current_year, 5, calendar.SUNDAY, 2)
            if mothers_day and today <= mothers_day <= today + timedelta(days=days_ahead):
                add_event(mothers_day, "Mother's Day")
            # Father's Day (3rd Sunday in June)
            fathers_day = get_nth_weekday_of_month(current_year, 6, calendar.SUNDAY, 3)
            if fathers_day and today <= fathers_day <= today + timedelta(days=days_ahead):
                add_event(fathers_day, "Father's Day")
            # Thanksgiving (4th Thursday in November) - often official, but good to have rule
            # The holidays library usually covers this for US. This is an example if it didn't.
            # thanksgiving = get_nth_weekday_of_month(current_year, 11, calendar.THURSDAY, 4)
            # if thanksgiving and today <= thanksgiving <= today + timedelta(days=days_ahead):
            #     add_event(thanksgiving, "Thanksgiving Day")


    # Easter Sunday (varies each year, calculated)
    easter_sunday = calc_easter_sunday(current_year)
    if easter_sunday and today <= easter_sunday <= today + timedelta(days=days_ahead):
        add_event(easter_sunday, "Easter Sunday")


    # 4. Format for output
    formatted_events = []
    if not events_by_date: # If after all checks, still no events
         return [f"No major holidays or observances found in the next {days_ahead} days for {country_code}."]

    for day_str in sorted(events_by_date.keys()): # Sort by date
        formatted_events.append(f"{day_str}: {', '.join(events_by_date[day_str])}")
    
    logging.info(f"Upcoming holidays and observances found: {formatted_events}")
    return formatted_events



class BirthdayEntry(BaseModel):
    name: str = Field(..., min_length=1)
    monthDay: str # Expects "MM-DD" format

    # Use Pydantic V2 field validator
    @field_validator('monthDay')
    @classmethod
    def validate_month_day_format(cls, v: str) -> str:
        if not isinstance(v, str) or len(v) != 5 or v[2] != '-':
            raise ValueError(f"Invalid monthDay format '{v}', must be MM-DD")
        try:
            month, day = map(int, v.split('-'))
            dt(2000, month, day) # Use dt alias, check with leap year
        except ValueError:
            raise ValueError(f"Invalid month or day in monthDay format '{v}'")
        return v

class BirthdayData(BaseModel):
    userBirthdate: Optional[str] = None # Frontend sends string
    friendsFamily: List[BirthdayEntry] = []

    # Use Pydantic V2 field validator
    @field_validator('userBirthdate')
    @classmethod
    def validate_user_birthdate_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None # Allow empty string as None
        if not isinstance(v, str):
             raise ValueError("userBirthdate must be a string or null")
        try:
            # Check if it's a valid YYYY-MM-DD date
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid userBirthdate format '{v}', must be YYYY-MM-DD or null/empty")
        return v

# --- Friends & Family Models ---
class FriendFamilyEntry(BaseModel):
    name: str = Field(..., min_length=1)
    relationship: str = Field(..., min_length=1)
    about: str = Field(default="", description="Information about this person")
    birthday: Optional[str] = Field(default=None, description="Birthday in MM-DD format")

    @field_validator('birthday')
    @classmethod
    def validate_birthday_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not isinstance(v, str) or len(v) != 5 or v[2] != '-':
            raise ValueError(f"Invalid birthday format '{v}', must be MM-DD")
        try:
            month, day = map(int, v.split('-'))
            dt(2000, month, day) # Use dt alias, check with leap year
        except ValueError:
            raise ValueError(f"Invalid month or day in birthday format '{v}'")
        return v

class FriendsFamilyData(BaseModel):
    friends_family: List[FriendFamilyEntry] = []
    available_relationships: List[str] = []

class RelationshipManagementRequest(BaseModel):
    relationship: str = Field(..., min_length=1)
    action: str = Field(..., pattern="^(add|remove)$")

# --- Pydantic Model for Diary Entry ---
class DiaryEntryInput(BaseModel):
    date: str # Expects YYYY-MM-DD from date input
    entry: str = Field(..., min_length=1)

    @field_validator('date')
    @classmethod
    def validate_diary_date_format(cls, v: str) -> str:
        if not isinstance(v, str): raise ValueError("Date must be a string")
        try: date.fromisoformat(v) # Check YYYY-MM-DD format
        except ValueError: raise ValueError("Invalid date format, must be YYYY-MM-DD")
        return v

class DiaryEntryOutput(DiaryEntryInput): # Model for response/storage
    id: str # UUID generated by backend

# --- Pydantic Model for Chat History Entry ---
class ChatEntry(BaseModel):
    timestamp: str # ISO format timestamp string
    question: str
    response: str
    id: str # UUID generated by backend

class ChatHistoryPayload(BaseModel): # For receiving data from gridpage.js
     question: str
     response: str




# Specific Load/Save wrappers using the generic functions
# Specific Load/Save wrappers using the generic functions
async def load_settings_from_file(account_id: str, aac_user_id: str) -> Dict:
    """
    Loads settings from Firestore for a specific user, returning defaults if error/missing.
    """
    return await load_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="settings/app_settings", # Firestore path
        default_data=DEFAULT_SETTINGS.copy()
    )


async def load_birthdays_from_file(account_id: str, aac_user_id: str) -> Dict: # <--- CHANGE 'user_id' to 'aac_user_id'
    """Loads birthday data from Firestore for a specific user."""
    default_birthdays_json_str = template_user_data_paths["birthdays.json"]
    default_birthdays_dict = json.loads(default_birthdays_json_str)

    loaded_data = await load_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id, # This is now consistent
        doc_subpath="info/birthdays", # Firestore path
        default_data=default_birthdays_dict # Use the dictionary as default
    )

    # ... (rest of function, including the logging line inside that uses `aac_user_id`) ...
    if not isinstance(loaded_data.get('friendsFamily'), list):
        logging.warning(f"Correcting 'friendsFamily' format in loaded birthday data for account {account_id} and user {aac_user_id}.")
        loaded_data['friendsFamily'] = []
    if loaded_data.get('userBirthdate'):
        try:
            date.fromisoformat(loaded_data['userBirthdate'])
        except (ValueError, TypeError) as e:
            logging.warning(f"Invalid userBirthdate '{loaded_data['userBirthdate']}' found in Firestore data for account {account_id} and user {aac_user_id}. Setting to None.")
            loaded_data['userBirthdate'] = None
    return loaded_data


async def save_birthdays_to_file(account_id: str, aac_user_id: str, birthday_data: Dict) -> bool: # <--- CHANGE 'user_id' to 'aac_user_id'
    """Saves birthday data to Firestore for a specific user."""
    # birthday_data should already be a dictionary from the BirthdayData Pydantic model
    return await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id, # This is now consistent
        doc_subpath="info/birthdays", # Firestore path
        data_to_save=birthday_data # This is already a dictionary
    )


# --- Friends & Family Load/Save ---
async def load_friends_family_from_file(account_id: str, aac_user_id: str) -> Dict:
    """Loads friends & family data from Firestore for a specific user."""
    default_friends_family = {
        "friends_family": DEFAULT_FRIENDS_FAMILY.copy(),
        "available_relationships": DEFAULT_RELATIONSHIPS.copy()
    }

    loaded_data = await load_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="info/friends_family",
        default_data=default_friends_family
    )

    # Ensure structure is correct
    if not isinstance(loaded_data.get('friends_family'), list):
        logging.warning(f"Correcting 'friends_family' format in loaded data for account {account_id} and user {aac_user_id}.")
        loaded_data['friends_family'] = []
    
    if not isinstance(loaded_data.get('available_relationships'), list):
        logging.warning(f"Correcting 'available_relationships' format in loaded data for account {account_id} and user {aac_user_id}.")
        loaded_data['available_relationships'] = DEFAULT_RELATIONSHIPS.copy()

    # Migrate old prefixed relationship types to new clean ones
    def clean_relationship(rel):
        """Remove prefixes from relationship types"""
        if rel.startswith("Family - "):
            return rel.replace("Family - ", "")
        elif rel.startswith("Friend - "):
            return rel.replace("Friend - ", "")
        elif rel.startswith("Professional - "):
            return rel.replace("Professional - ", "")
        elif rel.startswith("Community - "):
            return rel.replace("Community - ", "")
        return rel

    # Clean available relationships
    original_relationships = loaded_data['available_relationships'][:]
    cleaned_relationships = []
    for rel in loaded_data['available_relationships']:
        cleaned_rel = clean_relationship(rel)
        if cleaned_rel not in cleaned_relationships:
            cleaned_relationships.append(cleaned_rel)
    
    # Clean relationships in friends_family entries
    for person in loaded_data['friends_family']:
        if person.get('relationship'):
            person['relationship'] = clean_relationship(person['relationship'])

    # Update the relationships list
    loaded_data['available_relationships'] = cleaned_relationships

    # If we made changes, save the cleaned data back
    if original_relationships != cleaned_relationships:
        logging.info(f"Migrated relationship types from prefixed to clean format for account {account_id} and user {aac_user_id}.")
        await save_friends_family_to_file(account_id, aac_user_id, loaded_data)

    return loaded_data

async def save_friends_family_to_file(account_id: str, aac_user_id: str, friends_family_data: Dict) -> bool:
    """Saves friends & family data to Firestore for a specific user."""
    return await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="info/friends_family",
        data_to_save=friends_family_data
    )

# --- Button Activity Log Load/Save ---
async def load_button_activity_log(account_id: str, aac_user_id: str) -> List[Dict]:
    """
    Loads the button activity log from Firestore for a specific user.
    """
    # User activities are individual documents within a subcollection.
    entries = await load_firestore_collection(
        account_id=account_id,
        aac_user_id=aac_user_id,
        collection_subpath="button_activity_log", # Firestore subcollection path
    )

    # Original code added IDs to old entries if missing.
    # This will be less necessary if all new entries correctly use an ID.
    # But if you have old local data imported, this can still be useful.
    needs_save = False
    for entry in entries:
        if 'id' not in entry or not entry.get('id'):
            entry['id'] = str(uuid.uuid4()) # Ensure uuid is imported (from uuid import uuid4)
            needs_save = True

    if needs_save:
        await save_firestore_collection_items(
            account_id=account_id,
            aac_user_id=aac_user_id,
            collection_subpath="button_activity_log", # <--- CORRECTED
            items=entries
        )
    return entries



async def save_button_activity_log(account_id: str, aac_user_id: str, log_entries: List[Dict]):
    global firestore_db
    if not firestore_db:
        logging.error(f"Firestore DB client not initialized. Cannot log activity for account {account_id} and user {aac_user_id}.")
        return False
    collection_ref = firestore_db.collection(f"{FIRESTORE_ACCOUNTS_COLLECTION}/{account_id}/{FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION}/{aac_user_id}/button_activity_log") # CORRECTED
    try:
        for entry in log_entries:
            doc_id = entry.get('id') if entry.get('id') else str(uuid.uuid4())
            await asyncio.to_thread(collection_ref.document(doc_id).set, entry)
        logging.info(f"Appended {len(log_entries)} items to button activity log for account {account_id} and user {aac_user_id}.") 
        return True
    except Exception as e:
        logging.error(f"Error appending button activity log for account {account_id} and user {aac_user_id}: {e}", exc_info=True) 
        return False



async def load_diary_entries(account_id: str, aac_user_id: str) -> List[Dict]:
    """
    Loads and validates diary entries from Firestore for a specific user.
    Only returns entries that have 'id', 'date', and 'entry' fields as strings.
    """
    # This now loads from Firestore collection
    raw_entries = await load_firestore_collection(
        account_id=account_id,
        aac_user_id=aac_user_id,
        collection_subpath="diary_entries", # Firestore subcollection path
    )

    valid_entries = []
    # This flag is not strictly needed anymore if save_firestore_collection_items handles ID generation on set,
    # but keeping it for explicitness if we want to log ID additions.
    # needs_resave_due_to_missing_ids = False 

    for entry_data in raw_entries:
        if not isinstance(entry_data, dict):
            logging.warning(f"Skipping non-dictionary item in diary_entries for user {aac_user_id}: {entry_data}")
            continue

        entry_id = entry_data.get('id')
        # Ensure ID is a string. load_firestore_collection should already add it.
        # If an entry somehow lacks an ID here, it's problematic but we'll log and skip if it's not a string.
        if not isinstance(entry_id, str):
            logging.warning(f"Diary entry for user {aac_user_id} is missing a string ID or has an invalid ID type: {entry_data}. Skipping.")
            continue # Skip entries without a valid string ID
        
        # Validate essential fields for a diary entry
        if isinstance(entry_data.get('date'), str) and \
           isinstance(entry_data.get('entry'), str):
            valid_entries.append(entry_data)
        else:
            logging.warning(f"Skipping malformed diary entry (missing date/entry or wrong type) for user {aac_user_id}, ID {entry_id}: {entry_data}")

    return sorted(valid_entries, key=lambda x: x.get('date', '0001-01-01'), reverse=True)



async def save_diary_entries(account_id: str, aac_user_id: str, entries: List[Dict]):
    """
    Saves/overwrites all items in a Firestore subcollection, handling list of dicts.
    """
    sorted_entries = sorted(entries, key=lambda x: x.get('date', '0001-01-01'), reverse=True)
    return await save_firestore_collection_items(
        account_id=account_id,
        aac_user_id=aac_user_id,
        collection_subpath="diary_entries", # Firestore subcollection path
        items=sorted_entries # Save all items to the subcollection
    )


# --- Chat History Load/Save ---
async def load_chat_history(account_id: str, aac_user_id: str) -> List[Dict]:
    return await load_firestore_collection(
        account_id=account_id,
        aac_user_id=aac_user_id,
        collection_subpath="chat_history", # Firestore subcollection path
    )

async def save_chat_history(account_id: str, aac_user_id: str, history: List[Dict]):
    # The MAX_CHAT_HISTORY limit check should happen in the calling endpoint (e.g., record_chat_history)
    return await save_firestore_collection_items(
        account_id=account_id,
        aac_user_id=aac_user_id,
        collection_subpath="chat_history", # Firestore subcollection path
        items=history # Save all items to the subcollection
    )


# Update the `get_upcoming_birthdays` function to accept `user_id`
async def get_upcoming_birthdays(account_id: str, aac_user_id: str, days_ahead=14) -> List[str]: # ADD user_id
    """Calculates upcoming friend/family birthdays and user's age if applicable."""
    birthdays = await load_birthdays_from_file(account_id=account_id, aac_user_id=aac_user_id)

    today = date.today()
    output_lines = []

    # Calculate User Age
    user_age = None
    user_birthdate_str = birthdays.get('userBirthdate')
    if user_birthdate_str:
        try:
            birth_date = date.fromisoformat(user_birthdate_str)
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            user_age = age
            output_lines.append(f"User's current age: {user_age}")
            logging.info(f"Calculated user age: {user_age}")
            # Check if user's birthday is upcoming
            try:
                this_year_bday = date(today.year, birth_date.month, birth_date.day)
                next_year_bday = date(today.year + 1, birth_date.month, birth_date.day)
                upcoming_user_bday = None
                if today <= this_year_bday <= today + timedelta(days=days_ahead): upcoming_user_bday = this_year_bday
                elif today <= next_year_bday <= today + timedelta(days=days_ahead): upcoming_user_bday = next_year_bday
                if upcoming_user_bday:
                     days_diff = (upcoming_user_bday - today).days
                     relative_day = f" (in {days_diff} days)" if days_diff > 1 else (" (Tomorrow!)" if days_diff == 1 else " (Today!)")
                     output_lines.append(f"{upcoming_user_bday.strftime('%B %d')}: Your Birthday!{relative_day}")
            except ValueError: logging.warning(f"Cannot construct date for user bday {user_birthdate_str}")
        except (ValueError, TypeError) as e:
            logging.warning(f"Cannot parse user birthdate '{user_birthdate_str}': {e}")
            # Optionally, add a default message about invalid birthdate
            output_lines.append("User birthdate is not set or is invalid.")

    # Check Friends/Family Birthdays
    upcoming_ff_birthdays = {}
    for person in birthdays.get('friendsFamily', []):
        try:
            month_day_str = person.get('monthDay')
            name = person.get('name')
            if not month_day_str or not name: continue
            month, day = map(int, month_day_str.split('-'))
            # Check this year
            try:
                this_year_bday = date(today.year, month, day)
                if today <= this_year_bday <= today + timedelta(days=days_ahead):
                    if this_year_bday not in upcoming_ff_birthdays: upcoming_ff_birthdays[this_year_bday] = []
                    if name not in upcoming_ff_birthdays[this_year_bday]: upcoming_ff_birthdays[this_year_bday].append(name)
            except ValueError: pass # Ignore invalid dates like Feb 29
            # Check next year if range crosses year boundary
            # Corrected logic for year boundary check
            end_date = today + timedelta(days=days_ahead)
            if this_year_bday < today or this_year_bday > end_date: # If not in range this year
                 try:
                     next_year_bday = date(today.year + 1, month, day)
                     # Check if next year's birthday falls within the original window from today
                     if today <= next_year_bday <= end_date:
                         if next_year_bday not in upcoming_ff_birthdays: upcoming_ff_birthdays[next_year_bday] = []
                         if name not in upcoming_ff_birthdays[next_year_bday]: upcoming_ff_birthdays[next_year_bday].append(name)
                 except ValueError: pass # Ignore invalid dates like Feb 29
        except Exception as e: logging.warning(f"Error processing friend/family birthday {person}: {e}")

    if upcoming_ff_birthdays:
        output_lines.append("Upcoming Birthdays:")
        for bday_date in sorted(upcoming_ff_birthdays.keys()):
            days_diff = (bday_date - today).days
            relative_day = f" (in {days_diff} days)" if days_diff > 1 else (" (Tomorrow!)" if days_diff == 1 else " (Today!)")
            names = ", ".join(upcoming_ff_birthdays[bday_date])
            output_lines.append(f"  {bday_date.strftime('%B %d')}: {names}'s Birthday{relative_day}")
    elif not user_age: # Only add this if no age and no birthdays found
        output_lines.append(f"No birthdays found in the next {days_ahead} days.")

    logging.info(f"Upcoming birthday context: {output_lines}")
    return output_lines



# /api/profile
@app.get("/api/birthdays", response_model=BirthdayData)
async def get_birthdays(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]): # ADD user_id
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    logging.info(f"GET /api/birthdays request received for account {account_id} and user {aac_user_id}.")
    birthdays = await load_birthdays_from_file(account_id, aac_user_id) # Pass user_id
    return JSONResponse(content=birthdays)



@app.post("/api/birthdays", response_model=BirthdayData)
async def save_birthdays(birthday_data: BirthdayData, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]): # ADD user_id
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    logging.info(f"POST /api/birthdays request received for account {account_id} and user {aac_user_id} with data: {birthday_data}")
    data_to_save = birthday_data.model_dump(mode='json')
    
    success = await save_birthdays_to_file(account_id, aac_user_id, data_to_save) # Renamed to 'success' for clarity

    if success:
        # Invalidate cache so it gets rebuilt with new birthday data
        await cache_manager.invalidate_cache(account_id, aac_user_id)
        logging.info(f"Invalidated cache for account {account_id} and user {aac_user_id} after birthday update")
        
        return JSONResponse(content=data_to_save)
    else: 
        raise HTTPException(status_code=500, detail="Failed to save birthday data to file.")


# /api/friends-family
@app.get("/api/friends-family", response_model=FriendsFamilyData)
async def get_friends_family(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    logging.info(f"GET /api/friends-family request received for account {account_id} and user {aac_user_id}.")
    friends_family_data = await load_friends_family_from_file(account_id, aac_user_id)
    return JSONResponse(content=friends_family_data)

@app.post("/api/friends-family", response_model=FriendsFamilyData)
async def save_friends_family(friends_family_data: FriendsFamilyData, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    logging.info(f"POST /api/friends-family request received for account {account_id} and user {aac_user_id} with data: {friends_family_data}")
    data_to_save = friends_family_data.model_dump(mode='json')
    
    success = await save_friends_family_to_file(account_id, aac_user_id, data_to_save)

    if success:
        # Invalidate cache so it gets rebuilt with new friends & family data
        await cache_manager.invalidate_cache(account_id, aac_user_id)
        logging.info(f"Invalidated cache for account {account_id} and user {aac_user_id} after friends & family update")
        
        return JSONResponse(content=data_to_save)
    else: 
        raise HTTPException(status_code=500, detail="Failed to save friends & family data to file.")

@app.post("/api/manage-relationships")
async def manage_relationships(request: RelationshipManagementRequest, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    logging.info(f"POST /api/manage-relationships request received for account {account_id} and user {aac_user_id} with action: {request.action}")
    
    # Load current data
    friends_family_data = await load_friends_family_from_file(account_id, aac_user_id)
    available_relationships = friends_family_data.get('available_relationships', DEFAULT_RELATIONSHIPS.copy())
    
    if request.action == "add":
        if request.relationship and request.relationship not in available_relationships:
            available_relationships.append(request.relationship)
            friends_family_data['available_relationships'] = available_relationships
            success = await save_friends_family_to_file(account_id, aac_user_id, friends_family_data)
            if success:
                return JSONResponse(content={"success": True, "available_relationships": available_relationships})
            else:
                raise HTTPException(status_code=500, detail="Failed to add relationship.")
        else:
            raise HTTPException(status_code=400, detail="Relationship already exists or is invalid.")
    
    elif request.action == "remove":
        if request.relationship and request.relationship in available_relationships:
            available_relationships.remove(request.relationship)
            friends_family_data['available_relationships'] = available_relationships
            success = await save_friends_family_to_file(account_id, aac_user_id, friends_family_data)
            if success:
                return JSONResponse(content={"success": True, "available_relationships": available_relationships})
            else:
                raise HTTPException(status_code=500, detail="Failed to remove relationship.")
        else:
            raise HTTPException(status_code=400, detail="Relationship not found.")
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'add' or 'remove'.")


# /api/user-info
@app.get("/api/user-info")
async def get_user_info_api(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    logging.info(f"GET /api/user-info request received for account {account_id} and user {aac_user_id}.")
    
    user_info_content_dict = await load_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="info/user_narrative",
        default_data=DEFAULT_USER_INFO.copy()
    )
    return JSONResponse(content={
        "userInfo": user_info_content_dict.get("narrative", ""),
        "currentMood": user_info_content_dict.get("currentMood")
    })

# Debug endpoint for cache inspection
@app.get("/api/debug/cache")
async def get_cache_debug_info(
    current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)],
    include_content: bool = False
):
    """Debug endpoint to inspect cache state for troubleshooting"""
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    logging.info(f"GET /api/debug/cache request received for account {account_id} and user {aac_user_id}.")
    
    try:
        # Get detailed cache debug information
        debug_info = cache_manager.get_cache_debug_info(account_id, aac_user_id, include_content)
        
        # Add overall cache statistics
        cache_stats = cache_manager.get_cache_stats()
        
        # Try to get current user data for comparison
        try:
            user_info = await load_firestore_document(
                account_id=account_id,
                aac_user_id=aac_user_id,
                doc_subpath="info/user_narrative",
                default_data=DEFAULT_USER_INFO.copy()
            )
            debug_info["current_user_data"] = {
                "has_mood": "currentMood" in user_info,
                "current_mood": user_info.get("currentMood"),
                "narrative_length": len(user_info.get("narrative", ""))
            }
        except Exception as e:
            debug_info["current_user_data"] = {"error": str(e)}
        
        return JSONResponse(content={
            "success": True,
            "debug_info": debug_info,
            "cache_stats": cache_stats,
            "timestamp": dt.now().isoformat()
        })
    
    except Exception as e:
        logging.error(f"Error getting cache debug info: {e}")
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "timestamp": dt.now().isoformat()
        }, status_code=500)

@app.post("/api/user-info")
async def save_user_info_api(request: Dict, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    
    # The request body can have 'narrative' or 'userInfo'. Let's handle both for compatibility.
    user_info = request.get("narrative", request.get("userInfo", ""))
    current_mood = request.get("currentMood")
    
    logging.info(f"🔄 POST /api/user-info request - account {account_id}, user {aac_user_id}")
    logging.info(f"📝 Narrative length: {len(user_info) if user_info else 0} chars")
    logging.info(f"😊 Current mood: {current_mood}")
    
    # Log the raw request for debugging
    logging.info(f"🔍 Raw request data: {request}")
    
    success = await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="info/user_narrative",
        data_to_save={"narrative": user_info, "currentMood": current_mood}
    )
    
    if success:
        try:
            # Track mood update timestamp if mood was changed
            if current_mood:
                global mood_update_timestamps
                user_key = f"{account_id}/{aac_user_id}"
                mood_update_timestamps[user_key] = time.time()
                logging.info(f"🕐 Mood update timestamp recorded for {user_key}: {current_mood}")
            
            logging.info(f"✅ User info updated for {account_id}/{aac_user_id}. Mood: {current_mood}. Invalidating cache...")
            await cache_manager.invalidate_cache(account_id, aac_user_id)
            logging.info(f"🗑️ Cache invalidated successfully for mood/info change")
        except Exception as cache_error:
            logging.error(f"❌ Failed to invalidate cache for account {account_id} and user {aac_user_id}: {cache_error}", exc_info=True)
        
        return JSONResponse(content={"narrative": user_info, "currentMood": current_mood})
    else:
        raise HTTPException(status_code=500, detail="Failed to save user info.")


# /api/diary-entries
@app.get("/api/diary-entries", response_model=List[DiaryEntryOutput])
async def get_diary_entries_endpoint(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    logging.info(f"GET /api/diary-entries request received for user {aac_user_id}.")
    raw_entries = await load_diary_entries(account_id, aac_user_id) 

    valid_entries = []
    for entry in raw_entries:
        if isinstance(entry, dict) and \
           isinstance(entry.get('date'), str) and \
           isinstance(entry.get('entry'), str) and \
           isinstance(entry.get('id'), str):
            valid_entries.append(entry)
        else:
            logging.warning(f"Skipping malformed diary entry during backend processing for user {aac_user_id}: {entry}")
            
    try:
        valid_entries.sort(key=lambda x: dt.strptime(x.get('date'), '%Y-%m-%d').date(), reverse=True)
    except (ValueError, TypeError) as e:
        logging.error(f"Error sorting diary entries by date for account {account_id} and user {aac_user_id}: {e}")
    return JSONResponse(content=valid_entries)

@app.post("/api/diary-entry", response_model=DiaryEntryOutput, status_code=201)
async def add_or_update_diary_entry(entry_data: DiaryEntryInput, response: Response, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    logging.info(f"POST /api/diary-entry received for account {account_id} and user {aac_user_id}: {entry_data}")

    new_entry_dict = entry_data.model_dump()
    entries = await load_diary_entries(account_id, aac_user_id)

    existing_entry_index = -1
    for i, entry in enumerate(entries):
        if isinstance(entry, dict) and entry.get('date') == new_entry_dict['date']:
            existing_entry_index = i
            new_entry_dict['id'] = entry.get('id', str(uuid.uuid4()))
            break

    current_status = 201
    if existing_entry_index != -1:
        entries[existing_entry_index] = new_entry_dict
        current_status = 200
    else:
        new_entry_dict['id'] = str(uuid.uuid4())
        entries.append(new_entry_dict)

    if await save_diary_entries(account_id, aac_user_id, entries):
        await cache_manager.invalidate_cache(account_id, aac_user_id)
        logging.info(f"Invalidated cache after diary entry update for user {aac_user_id}.")
        response.status_code = current_status
        return new_entry_dict
    else:
        raise HTTPException(status_code=500, detail="Failed to save diary entry.")

@app.delete("/api/diary-entry/{entry_id}")
async def delete_diary_entry(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)], entry_id: str = Path(..., description="The ID of the diary entry to delete")):
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]
    logging.info(f"DELETE /api/diary-entry/{entry_id} request received for account {account_id} and user {aac_user_id}.")
    
    entries = await load_diary_entries(account_id, aac_user_id)
    initial_length = len(entries)
    entries_after_delete = [entry for entry in entries if entry.get('id') != entry_id]
    
    if len(entries_after_delete) < initial_length:
        if await save_diary_entries(account_id, aac_user_id, entries_after_delete):
            await cache_manager.invalidate_cache(account_id, aac_user_id)
            logging.info(f"Invalidated cache after deleting diary entry for user {aac_user_id}.")
            return Response(status_code=204)
        else:
            raise HTTPException(status_code=500, detail="Failed to save diary entries after deletion.")
    else: 
        raise HTTPException(status_code=404, detail=f"Diary entry with ID '{entry_id}' not found.")





# /record_chat_history
@app.post("/record_chat_history")
async def record_chat_history_endpoint(payload: ChatHistoryPayload, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]): # ADD user_id
    try:
        aac_user_id = current_ids["aac_user_id"]
        account_id = current_ids["account_id"]
        question = payload.question
        response = payload.response
        if not question or not response: raise HTTPException(status_code=400, detail="Missing question or response.")
        timestamp = dt.now().isoformat()
        log_entry = {"timestamp": timestamp, "question": question, "response": response, "id": uuid.uuid4().hex}
        history = load_chat_history(account_id, aac_user_id) # Pass user_id
        history.append(log_entry)
        if len(history) > MAX_CHAT_HISTORY: history = history[-MAX_CHAT_HISTORY:]
        if save_chat_history(account_id, aac_user_id, history): # Pass user_id
            logging.info(f"Chat history updated successfully for account {account_id} and user {aac_user_id}.")
            
            # Invalidate the cache since chat history has changed
            await cache_manager.invalidate_cache(account_id, aac_user_id)
            
            return JSONResponse(content={"message": "Chat history saved successfully"})
        else: raise HTTPException(status_code=500, detail="Failed to save chat history.")
    except HTTPException as http_exc: raise http_exc
    except Exception as e:
        logging.error(f"Error recording chat history for account {account_id} and user {aac_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    


class PageActivityReportItem(BaseModel):
    page_name: str
    clicks: int
    is_defined: bool # True if the page exists in pages.json




@app.get("/api/audit/reports/global-page-activity", response_model=List[PageActivityReportItem])
async def get_global_page_activity_report(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """
    Generates a report of page visit counts, excluding 'home' for a specific user.
    Includes all defined pages, marking if they have been clicked.
    """
    try:
        aac_user_id = current_ids["aac_user_id"]
        account_id = current_ids["account_id"]

        activity_log = await load_button_activity_log(account_id, aac_user_id) # This loads the raw data
        logging.info(f"DEBUG: Loaded activity_log for account {account_id} and  user {aac_user_id}. Number of entries: {len(activity_log)}")
        for i, entry in enumerate(activity_log):
            logging.info(f"DEBUG: Activity_log entry {i}: {entry.get('page_name')=}, {entry.get('button_text')=}")

        all_defined_pages_data = await load_pages_from_file(account_id, aac_user_id)
        logging.info(f"DEBUG: Loaded pages data for account {account_id} and user {aac_user_id}. Number of entries: {len(all_defined_pages_data)}")
        
        defined_page_names = {page.get("name") for page in all_defined_pages_data if page.get("name")}
        logging.info(f"DEBUG: Defined page names for account{account_id} and user {aac_user_id}: {defined_page_names}")
        
        page_click_counts = Counter()
        for entry in activity_log:
            page_name = entry.get("page_name") # Get the raw page_name
            # Ensure proper stripping and lowercasing for comparison, defensive coding
            cleaned_page_name = page_name.strip().lower() if page_name else None 
            
            logging.info(f"DEBUG: Processing entry. Original page_name='{page_name}', Cleaned='{cleaned_page_name}'")

            # The filtering condition is here:
            if cleaned_page_name and cleaned_page_name != "home": # Now using cleaned_page_name
                page_click_counts[cleaned_page_name] += 1 # Add to counter using cleaned name
                logging.info(f"DEBUG: Page '{cleaned_page_name}' counted.")
            else:
                logging.info(f"DEBUG: Page '{page_name}' excluded (either None/empty or 'home').")
        
        logging.info(f"DEBUG: Final page_click_counts for account {account_id} and user {aac_user_id}: {page_click_counts}")


        report_data = []

        # Add pages that were clicked (from page_click_counts)
        for page_name, clicks in page_click_counts.items(): # page_name here is already cleaned/lowercased
            # Note: We append the raw page name from defined_page_names if available, or use the cleaned one
            original_page_name_for_display = next((p for p in all_defined_pages_data if p.get("name") and p.get("name").lower() == page_name), page_name)
            report_data.append(PageActivityReportItem(
                page_name=original_page_name_for_display.get("name") if isinstance(original_page_name_for_display, dict) else original_page_name_for_display, # Use original case for display
                clicks=clicks,
                is_defined=page_name in defined_page_names # defined_page_names are raw, but check via loop
            ))
            
        # Add defined pages that were NOT clicked (and not 'home')
        for defined_page_raw_name_from_pages_json in defined_page_names: # Iterate through raw names from pages.json
            if defined_page_raw_name_from_pages_json.lower() != "home" and defined_page_raw_name_from_pages_json.lower() not in page_click_counts:
                report_data.append(PageActivityReportItem(
                    page_name=defined_page_raw_name_from_pages_json,
                    clicks=0,
                    is_defined=True
                ))
                
        # Sort and return
        report_data.sort(key=lambda x: (-x.clicks, x.page_name))
        
        logging.info(f"Generated global page activity report for account {account_id} and user {aac_user_id} with {len(report_data)} items.")
        return report_data
        
    except Exception as e:
        logging.error(f"Error generating global page activity report for account {account_id} and user {aac_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error generating report: {str(e)}")



class PageButtonReportItem(BaseModel):
    button_text: str
    button_summary: Optional[str] = None
    clicks: int
    source_type: str # e.g., "Defined Static", "LLM Generated Click", "Clicked (Not Defined Static)"



@app.get("/api/page-names", response_model=List[str])
async def get_all_page_names(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]): # ADD user_id header
    """Returns a list of all unique page names from pages.json for a specific user."""
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    try:
        pages_data = await load_pages_from_file(account_id, aac_user_id) # Pass user_id
        page_names = sorted(list(set(page.get("name") for page in pages_data if page.get("name"))))
        return page_names
    except Exception as e:
        logging.error(f"Error fetching page names for account {account_id} and user {aac_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve page names.")


@app.get("/api/audit/reports/page-button-activity/{page_name}")
async def get_page_button_activity_report(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)], page_name: str = Path(..., description="The name of the page to report on.")): # ADD user_i
    """
    Generates a report of button click activity for a specific page and user.
    Includes all defined static buttons for that page and any LLM-generated buttons clicked on that page.
    """
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    try:
        activity_log = await load_button_activity_log(account_id, aac_user_id) # Pass user_id
        all_pages_data = await load_pages_from_file(account_id, aac_user_id)

        target_page_data = next((p for p in all_pages_data if p.get("name") == page_name), None)
        if not target_page_data:
            logging.warning(f"Page '{page_name}' not found in pages.json for defined button analysis.")

        report_items_dict = {} 

        page_specific_log = [
            entry for entry in activity_log 
            if entry.get("page_name") == page_name and entry.get("button_text") and
               not entry.get("is_llm_generated", False) # Exclude LLM generated clicks
        ]

        if target_page_data:
            for static_button_def in target_page_data.get("buttons", []):
                btn_text = static_button_def.get("text")
                if not btn_text:
                    continue
                
                btn_summary = static_button_def.get("speechPhrase") or btn_text 
                
                clicks = sum(1 for log_entry in page_specific_log 
                             if log_entry.get("button_text") == btn_text) # Count clicks from the already filtered log
                
                report_items_dict[btn_text] = PageButtonReportItem(
                    button_text=btn_text,
                    button_summary=btn_summary,
                    clicks=clicks,
                    source_type="Defined Static"
                )

        button_click_counts = Counter()
        logged_summaries = {} # Initialize logged_summaries

        
        # Summaries are less relevant here as we only process non-LLM clicks now
        for log_entry in page_specific_log:
            btn_text = log_entry.get("button_text") # Define btn_text from log_entry
            if not btn_text: # Skip if button_text is missing in log
                continue
            button_click_counts[btn_text] += 1
            if btn_text not in logged_summaries: # Now logged_summaries is defined
                logged_summaries[btn_text] = log_entry.get("button_summary") or btn_text # Store summary from log


        for btn_text, total_clicks in button_click_counts.items():
            if btn_text in report_items_dict: 
                 # If it's a defined static button, its clicks were already counted
                # from the filtered log in the first loop. Just ensure the count is correct.
                report_items_dict[btn_text].clicks = total_clicks # Total non-LLM clicks for this text 
            else: 
                # If the button text is not defined static, it's a non-LLM click
                # on a button that isn't in pages.json for this page.
                source_type = "Clicked (Not Defined Static)"
                report_items_dict[btn_text] = PageButtonReportItem(
                    button_text=btn_text,
                    button_summary=logged_summaries.get(btn_text), # Use the summary from the log
                    clicks=total_clicks,
                    source_type=source_type
                )

        final_report_list = sorted(report_items_dict.values(), key=lambda x: (-x.clicks, x.button_text))
        logging.info(f"Generated page button activity report for '{page_name}' with {len(final_report_list)} items.")
        return final_report_list

    except Exception as e:
        logging.error(f"Error generating page button activity report for '{page_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error generating report: {str(e)}")



# --- Button Click Audit Trail ---
class ButtonClickData(BaseModel):
    timestamp: str  # ISO format string
    page_name: str
    page_context_prompt: Optional[str] = None # The prompt used if buttons were LLM-generated for a dynamic page
    button_text: str
    button_summary: Optional[str] = None
    is_llm_generated: bool
    originating_button_text: Optional[str] = None # Changed to Optional
    # session_id: Optional[str] = None # Optional: To track user sessions if implemented




# /api/audit/log-button-click
@app.post("/api/audit/log-button-click")
async def log_button_click_endpoint(click_data: ButtonClickData, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]): # ADD user_id
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    try:
        log_entry = click_data.model_dump()
        activity_log = await load_button_activity_log(account_id, aac_user_id) # Pass user_id
        activity_log.append(log_entry)
        print(f"Button click logged for account {account_id} and user {aac_user_id}: {log_entry}")
        success = await save_button_activity_log(account_id, aac_user_id, activity_log)
        if success:
            logging.info(f"Button click logged for account {account_id} and user {aac_user_id}: Page '{click_data.page_name}', Button '{click_data.button_text[:50]}...'")
            
            # Cache is NOT invalidated here to preserve context during a session.
            # It will be invalidated by other actions like changing user info, settings, etc.
            logging.info(f"Cache not invalidated for button click for user {aac_user_id}.")
            
            return JSONResponse(content={"message": "Button click logged successfully."})
        else: raise HTTPException(status_code=500, detail="Failed to save button click log.")
    except Exception as e:
        logging.error(f"Error logging button click for account {account_id} and user {aac_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    



# /api/audit/activity-report
@app.get("/api/audit/activity-report")
async def get_activity_report_endpoint(start_date: str, end_date: str, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]): # ADD user_id
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    try:
        start_dt = dt.fromisoformat(start_date.replace("Z", "+00:00"))
        end_dt = dt.fromisoformat(end_date.replace("Z", "+00:00"))
        activity_log = await load_button_activity_log(account_id, aac_user_id) # Pass user_id
        filtered_log = []
        for entry in activity_log:
            timestamp_str = entry.get("timestamp")
            if timestamp_str: # Check if timestamp exists
                try:
                    entry_dt = dt.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if start_dt <= entry_dt <= end_dt:
                        filtered_log.append(entry)
                except ValueError:
                    logging.warning(f"Skipping activity log entry due to invalid timestamp format for user {aac_user_id}, entry ID {entry.get('id', 'N/A')}: {timestamp_str}")
            else:
                logging.warning(f"Skipping activity log entry due to missing timestamp for user {aac_user_id}, entry ID {entry.get('id', 'N/A')}")
        return JSONResponse(content=filtered_log)
    except ValueError: raise HTTPException(status_code=400, detail="Invalid date format. Please use ISO format (YYYY-MM-DDTHH:MM:SSZ).")
    except Exception as e:
        logging.error(f"Error generating activity report for account {account_id} and user {aac_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# --- Request Body Model for User Registration ---
class CreateAccountRequest(BaseModel):
    account_name: str
    num_users_allowed: int = Field(default=1, ge=1)  # Default to 1, minimum 1
    promo_code: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    therapist_email: Optional[str] = None
    is_therapist: Optional[bool] = False  # NEW: Flag to indicate if this account is a therapist
    allow_admin_access: Optional[bool] = True  # NEW: Flag to allow Bravo admin access (default True)

    # --- NEW: Email is derived from token, not provided here
    # email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$") # Email will be derived from token

# --- Pydantic model for simplified token verification (registration) ---
class FirebaseTokenPayload(BaseModel):
    account_id: str
    email: Optional[str] = None # Email might not be present in all flows

# --- FastAPI Dependency for Firebase Token Verification (simplified) ---
async def verify_firebase_token_only(
    token: Annotated[HTTPAuthorizationCredentials, Depends(oauth2_scheme)]
) -> Dict[str, str]:
    global firebase_app
    if not firebase_app:
        raise HTTPException(status_code=503, detail="Authentication service unavailable.")
    try:
        decoded_token = await asyncio.to_thread(auth.verify_id_token, token.credentials)
        # Return Firebase UID and email from the token
        return {"account_id": decoded_token['uid'], "email": decoded_token.get('email')}
    except auth.InvalidIdTokenError:
        logging.warning("Invalid Firebase ID token received during token-only verification.")
        raise HTTPException(status_code=401, detail="Invalid authentication token.")
    except auth.ExpiredIdTokenError:
        logging.warning("Expired Firebase ID token received during token-only verification.")
        raise HTTPException(status_code=401, detail="Authentication token expired. Please log in again.")
    except Exception as e:
        logging.error(f"Error during token-only verification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authentication error during token verification: {e}")



@app.post("/api/auth/register")
async def register_account(
    request_data: CreateAccountRequest,
    token_info: Annotated[Dict[str, str], Depends(verify_firebase_token_only)] # Use the new, simpler dependency
):
    account_id = token_info['account_id'] # Firebase UID from the token
    email = token_info['email'] # Email from the token

    global firestore_db
    if not firestore_db:
        raise HTTPException(status_code=503, detail="Firestore DB client not initialized.")

    try:
        # 1. Check if the Firestore account document already exists for this Firebase UID.
        # This handles idempotency: if the client-side Firebase Auth already registered the user
        # and then the backend call is a retry or refresh.
        account_doc_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(account_id)
        account_doc = await asyncio.to_thread(account_doc_ref.get)
        
        if account_doc.exists:
            logging.warning(f"Account (Firebase UID: {account_id}, Email: {email}) already exists in Firestore.")
            account_data = account_doc.to_dict() # Get existing account data
            # If the account document already exists, fetch its first AAC user ID to return.
            existing_users_ref = account_doc_ref.collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
            # Fetch all user documents to check if any exist.
            existing_aac_user_docs_list = await asyncio.to_thread(list, existing_users_ref.stream())

            if existing_aac_user_docs_list:
                first_aac_user_id = existing_aac_user_docs_list[0].id
                logging.info(f"Found existing AAC user '{first_aac_user_id}' for account '{account_id}'.")
                return JSONResponse(content={
                    "message": "Account already registered with existing user profiles.",
                    "account_id": account_id,
                    "first_aac_user_id": first_aac_user_id
                }, status_code=200)
            else:
                # Account exists, but NO AAC users. Fix this inconsistent state.
                num_users_to_create = account_data.get("num_users_allowed", 1)
                account_name_from_db = account_data.get("account_name", "User")
                logging.warning(f"Account '{account_id}' exists but has no AAC users. Initializing {num_users_to_create} profile(s).")
                first_aac_user_id = None
                for i in range(num_users_to_create):
                    new_aac_user_id = str(uuid.uuid4())
                    if i == 0: first_aac_user_id = new_aac_user_id
                    await _initialize_new_aac_user_profile(
                        account_id=account_id,
                        aac_user_id=new_aac_user_id,
                        display_name=f"{account_name_from_db}'s Device {i + 1}"
                    )
                logging.info(f"Initialized {num_users_to_create} AAC user(s) for existing account '{account_id}'.")
                return JSONResponse(content={
                    "message": "Account existed, user profiles now initialized.",
                    "account_id": account_id,
                    "first_aac_user_id": first_aac_user_id
                }, status_code=200) # Still 200 as we "fixed" the state

        else: # Account document does NOT exist, proceed with new creation
            # 2. Determine billing status based on promo code
            is_active = True
            trial_ends_at = None
            if request_data.promo_code and request_data.promo_code.upper() == POC_PROMO_CODE:
                promo_status = "POC_FREE"
            elif request_data.promo_code and request_data.promo_code.upper() == FREE_TRIAL_PROMO_CODE:
                promo_status = "TRIALING"
                trial_ends_at = (dt.now() + timedelta(days=30)).isoformat()
            else:
                promo_status = "NONE"

            # 3. Create Account Document in Firestore
            account_data = {
                "email": email, # Use email from token_info
                "account_name": request_data.account_name,
                "num_users_allowed": request_data.num_users_allowed,
                "promo_code_applied": request_data.promo_code.upper() if request_data.promo_code else None,
                "promo_status": promo_status,
                "is_active": is_active,
                "trial_ends_at": trial_ends_at,
                "address": request_data.address,
                "phone": request_data.phone,
                "therapist_email": request_data.therapist_email,
                "is_therapist": request_data.is_therapist,  # NEW: Therapist flag
                "allow_admin_access": request_data.allow_admin_access,  # NEW: Admin access permission
                "authorized_users": [email], # Creator's email is always authorized
                "created_at": dt.now().isoformat(),
                "last_updated": dt.now().isoformat()
            }

            # CRITICAL FIX: Await the Firestore set operation and handle potential errors.
            try:
                await asyncio.to_thread(account_doc_ref.set, account_data)
            except Exception as e_firestore_set:
                logging.error(f"Failed to set account document in Firestore for UID {account_id}: {e_firestore_set}", exc_info=True)
                # Optionally, delete the Firebase Auth user here if the Firestore setup fails critically.
                raise HTTPException(status_code=500, detail=f"Failed to create account record in database: {e_firestore_set}")

            logging.info(f"Account '{account_id}' ({email}) created successfully in Firestore.")

            # 4. Create the requested number of individual AAC user profiles
            num_users_to_create = request_data.num_users_allowed
            first_aac_user_id = None # To store the ID of the first user created

            for i in range(num_users_to_create):
                new_aac_user_id = str(uuid.uuid4())
                if i == 0: first_aac_user_id = new_aac_user_id # Capture the first one
                await _initialize_new_aac_user_profile(
                    account_id=account_id,
                    aac_user_id=new_aac_user_id,
                    display_name=f"{request_data.account_name}'s Device {i + 1}"
                )

            return JSONResponse(content={
                "message": "Account and user profiles created successfully.",
                "account_id": account_id,
                "first_aac_user_id": first_aac_user_id
            }, status_code=201)

    except EmailAlreadyExistsError as e: # This exception is for if create_user was mistakenly called (it's removed now)
        logging.warning(f"Unexpected EmailAlreadyExistsError caught in backend for email {email}. This should ideally be handled by frontend Firebase SDK.")
        raise HTTPException(status_code=400, detail="Email already registered. Please log in or use a different email.")
    except HTTPException as e: # Re-raise explicit HTTPExceptions
        raise e
    except Exception as e:
        logging.error(f"Error during account registration Firestore setup for UID {account_id}, email {email}: {e}", exc_info=True)
        # IMPORTANT: Consider adding logic here to delete the Firebase Auth user
        # if the Firestore setup fails. This prevents orphaned Firebase Auth users.
        # However, it adds complexity. For now, manual cleanup might be needed if this happens.
        raise HTTPException(status_code=500, detail=f"Failed to finalize account setup: {e}")


class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/login")
async def login_account(request_data: LoginRequest):
    global firebase_app

    if not firebase_app:
        raise HTTPException(status_code=503, detail="Firebase backend service not initialized.")

    # Firebase Admin SDK does not directly have a "sign_in_with_email_and_password" function.
    # Authentication is done client-side via Firebase Client SDK, which gives an ID token.
    # The backend's role is to *verify* that token.

    # This endpoint is primarily for demonstrating how the client would send credentials
    # and the server would then verify a token. For email/password login, the client-side
    # Firebase SDK handles the initial login and token generation.

    # Therefore, this endpoint would typically *not* take email/password.
    # Instead, a client-side Firebase Auth login would happen, which returns an ID token.
    # The client would then send this token to other *secured* endpoints for verification.

    # For now, we'll keep a placeholder or adapt based on client-side token flow.
    # If this endpoint were to directly handle login (e.g., using a non-Firebase identity provider),
    # it would return some form of session token.
    # Since we're using Firebase Auth:
    raise HTTPException(status_code=405, detail="Login must be initiated client-side via Firebase SDK to obtain an ID token.")

    # If you were to implement custom token generation for a specific scenario (e.g., integrating with legacy systems):
    # try:
    #     user_record = await asyncio.to_thread(auth.get_user_by_email, request_data.email)
    #     custom_token = await asyncio.to_thread(auth.create_custom_token, user_record.uid)
    #     return JSONResponse(content={"custom_token": custom_token.decode('utf-8')})
    # except auth.AuthError as e:
    #     logging.error(f"Firebase Auth error during custom token creation: {e}", exc_info=True)
    #     raise HTTPException(status_code=401, detail="Invalid credentials or user not found.")
    # except Exception as e:
    #     logging.error(f"Error creating custom token: {e}", exc_info=True)
    #     raise HTTPException(status_code=500, detail="Internal server error during login.")


async def _initialize_new_aac_user_profile(account_id: str, aac_user_id: str, display_name: str):
    """
    Initializes a new individual AAC user profile under a given account_id in Firestore
    """
    global firestore_db

    if not firestore_db:
        logging.error("Firestore DB client not initialized. Cannot initialize new AAC user profile.")
        raise Exception("Firestore DB client not initialized.")

    # Base path for this individual AAC user's data
    user_base_path = f"accounts/{account_id}/{FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION}/{aac_user_id}"

    # First, create the root document for the AAC user and store their display name
    aac_user_doc_ref = firestore_db.document(user_base_path)
    await asyncio.to_thread(aac_user_doc_ref.set, {
        "display_name": display_name,
        "created_at": dt.now().isoformat(),
        "parent_account_id": account_id
    })
    logging.info(f"Created AAC user document for '{display_name}' ({aac_user_id}) under account {account_id}.")

    # --- Initialize Firestore Documents for this AAC user ---
    # Using the template_user_data_paths from your existing code
    # Adjust paths to include the account_id and aac_user_id

    # Initial settings:
    await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="config/app_settings",
        data_to_save=json.loads(template_user_data_paths["settings.json"])
    )

    # Initial birthdays:
    await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="info/birthdays",
        data_to_save=json.loads(template_user_data_paths["birthdays.json"])
    )

    # Initial user info narrative:
    user_info_content = template_user_data_paths["user_info.txt"]
    await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="info/user_narrative",
        data_to_save={"narrative": user_info_content}
    )

    # Initial user current state:
    user_current_str = template_user_data_paths["user_current.txt"]
    user_current_dict = {}
    for line in user_current_str.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            norm_key = key.strip().lower().replace(" ", "_").replace("_present", "")
            user_current_dict[norm_key] = value.strip()
    await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="info/current_state",
        data_to_save=user_current_dict
    )

    # Initial user favorites/scraping config:
    await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="config/scraping_config",
        data_to_save=json.loads(template_user_data_paths["user_favorites.json"])
    )

    # Initial pages (use save_pages_to_file to correctly wrap the list in a dict):
    initial_pages_list = json.loads(template_user_data_paths["pages.json"])
    # Ensure all page names and targetPages in the default template are lowercase
    for page in initial_pages_list:
        if "name" in page and page["name"]:
            page["name"] = page["name"].lower()
        if "buttons" in page and isinstance(page["buttons"], list):
            for button in page["buttons"]:
                if isinstance(button, dict) and "targetPage" in button and button["targetPage"]:
                    button["targetPage"] = button["targetPage"].lower()
    await save_pages_to_file(account_id, aac_user_id, initial_pages_list)

    # Initial audio config:
    await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="config/audio_config",
        data_to_save=json.loads(template_user_data_paths["audio_config.json"])
    )

    # --- Initialize empty collections in Firestore ---
    # Firestore doesn't explicitly create collections for empty ones,
    # but making a dummy write here ensures the path exists if it's strictly needed
     # for any client-side calls that check for collection existence. Use asyncio.to_thread for non-blocking set.
    await asyncio.to_thread(firestore_db.collection(f"{user_base_path}/diary_entries").document("placeholder").set, {"created": True})
    await asyncio.to_thread(firestore_db.collection(f"{user_base_path}/chat_history").document("placeholder").set, {"created": True})
    await asyncio.to_thread(firestore_db.collection(f"{user_base_path}/button_activity_log").document("placeholder").set, {"created": True})

    logging.info(f"Individual AAC user '{aac_user_id}' initialized with default data in Firestore ")


# --- Freestyle Endpoints ---
class FreestyleWordPredictionRequest(BaseModel):
    text: str = Field(default="", description="Context text from build space")
    spelling_word: str = Field(default="", description="Current partial word being spelled")
    predict_full_words: bool = Field(default=True, description="Whether to predict full words or completions")

@app.post("/api/freestyle/word-prediction")
async def get_freestyle_word_prediction(
    request: FreestyleWordPredictionRequest,
    current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]
):
    """
    Provides word completion suggestions for freestyle text input
    """
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    
    try:
        # Load user settings to get FreestyleOptions
        settings = await load_settings_from_file(account_id, aac_user_id)
        freestyle_options = settings.get("FreestyleOptions", 20)  # Default to 20 if not set
        
        # Load user context for better predictions
        user_info = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/user_narrative",
            default_data={"narrative": ""}
        )
        
        # Determine what we're predicting
        context_text = request.text.strip() if request.text else ""
        partial_word = request.spelling_word.strip() if request.spelling_word else ""
        
        if not partial_word:
            return JSONResponse(content={"predictions": []})
        
        # Create prompt for full word prediction with user context
        user_context = user_info.get("narrative", "")
        
        if context_text:
            prompt = f"Given the user context: '{user_context}' and the existing text: '{context_text}', provide {freestyle_options} complete words that start with '{partial_word}'. The words should be contextually appropriate and commonly used. Return only the complete words, one per line."
        else:
            prompt = f"Given the user context: '{user_context}', provide {freestyle_options} complete words that start with '{partial_word}'. The words should be commonly used. Return only the complete words, one per line."
        
        # Use LLM to generate predictions
        response_text = await _generate_gemini_content_with_fallback(prompt)
        
        # Parse predictions - ensure they are complete words starting with the partial word
        raw_predictions = [line.strip() for line in response_text.split('\n') if line.strip()]
        predictions = []
        
        for pred in raw_predictions[:freestyle_options * 2]:  # Get extra to filter
            # Ensure the prediction starts with the partial word and is a complete word
            if pred.lower().startswith(partial_word.lower()) and len(pred) > len(partial_word):
                predictions.append(pred)
            elif not partial_word and pred:  # If no partial word, just add valid predictions
                predictions.append(pred)
        
        # Limit to freestyle_options predictions
        predictions = predictions[:freestyle_options]
        
        logging.info(f"Word predictions for partial '{partial_word}' with context '{context_text}': {predictions}")
        return JSONResponse(content={"predictions": predictions})
        
    except Exception as e:
        logging.error(f"Error generating word predictions for account {account_id}, user {aac_user_id}: {e}", exc_info=True)
        return JSONResponse(content={"predictions": []})
    

class FreestyleWordOptionsRequest(BaseModel):
    build_space_text: Optional[str] = None
    request_different_options: Optional[bool] = False


@app.post("/api/freestyle/word-options")
async def get_freestyle_word_options(
    request: FreestyleWordOptionsRequest,
    current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]
):
    """
    Provides contextual word suggestions for freestyle communication
    """
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    
    try:
        # Load user settings to get FreestyleOptions
        settings = await load_settings_from_file(account_id, aac_user_id)
        freestyle_options = settings.get("FreestyleOptions", 20)  # Default to 20 if not set
        
        # Load user context
        user_info = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/user_narrative",
            default_data={"narrative": ""}
        )
        
        user_current = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_state",
            default_data=DEFAULT_USER_CURRENT.copy()
        )
        
        # Create context-aware prompt
        context_parts = []
        if user_info.get("narrative"):
            context_parts.append(f"User info: {user_info['narrative']}")
        if user_current.get("location"):
            context_parts.append(f"Current location: {user_current['location']}")
        if user_current.get("people"):
            context_parts.append(f"People present: {user_current['people']}")
        if user_current.get("activity"):
            context_parts.append(f"Current activity: {user_current['activity']}")
        
        context_str = " | ".join(context_parts) if context_parts else "General conversation"
        
        # Handle build space context for dynamic suggestions
        build_space_text = request.build_space_text or ""

        logging.info(f"Raw build space text: '{build_space_text}'")
        logging.info(f"Context for word options: '{context_str}'")
        
        
        if build_space_text.strip():
            # If there's text in build space, provide contextual next words
            variation_text = "different and alternative" if request.request_different_options else "varied and diverse"
            prompt = f"""Given this context: {context_str} and the partial sentence '{build_space_text}', provide exactly {freestyle_options} {variation_text} useful words or short phrases that would logically complete or continue this communication. 

Requirements:
- Each option should be DIFFERENT and UNIQUE
- Focus on words that would naturally follow what's already written
- Provide variety in the suggestions (different topics, actions, descriptions)
- Return only the words/phrases, one per line
- Do not repeat the same option multiple times
- Make each option distinct and useful

Examples of good variety: verbs, adjectives, locations, time expressions, etc."""
        else:
            # If no build space text, provide conversation starters
            variation_text = "different and alternative" if request.request_different_options else "varied and diverse"
            prompt = f"""Given this context: {context_str}, provide exactly {freestyle_options} {variation_text} useful words or short phrases to START AAC communication. 

Requirements:
- Each option should be DIFFERENT and UNIQUE
- Include common conversation starters like 'I', 'You', 'Where', 'Who', 'What', 'Can', 'Want', 'Need', etc.
- Provide variety in the suggestions (questions, statements, greetings, etc.)
- Return only the words/phrases, one per line
- Do not repeat the same option multiple times
- Make each option distinct and useful"""
        
        logging.info(f"Generated prompt for LLM: {prompt}")

        # Use LLM to generate options with generation config for more randomness
        generation_config = {
            "temperature": 0.8,  # Add some randomness
            "top_p": 0.9,
            "candidate_count": 1
        }
        
        response_text = await _generate_gemini_content_with_fallback(prompt, generation_config, account_id, aac_user_id)
        
        # Parse options and ensure uniqueness
        all_options = [line.strip() for line in response_text.split('\n') if line.strip()]
        
        # Remove duplicates while preserving order
        unique_options = []
        seen = set()
        for option in all_options:
            option_lower = option.lower()
            if option_lower not in seen and option:
                unique_options.append(option)
                seen.add(option_lower)
        
        # Take only the requested number
        options = unique_options[:freestyle_options]
        
        logging.info(f"Generated {len(options)} unique word options for build space: '{build_space_text}' with context: {context_str}")
        logging.info(f"Options: {options}")
        return JSONResponse(content={"word_options": options})
        
    except Exception as e:
        logging.error(f"Error generating word options for account {account_id}, user {aac_user_id}: {e}", exc_info=True)
        return JSONResponse(content={"word_options": []})


class FreestyleCleanupRequest(BaseModel):
    text_to_cleanup: str = Field(..., min_length=1, description="Text to clean up and improve")

@app.post("/api/freestyle/cleanup-text")
async def cleanup_freestyle_text(
    request: FreestyleCleanupRequest,
    current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]
):
    """
    Uses LLM to clean up and improve freestyle text with better grammar and structure,
    incorporating user context from RAG database for personalized cleanup
    """
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    
    try:
        # Create lightweight user query for the caching function
        user_query_only = f"""Clean up and improve this text while preserving the original meaning and intent. Use my personal context to make the cleanup more personalized and appropriate.

Original text: "{request.text_to_cleanup}"

Please:
1. Fix grammar and punctuation
2. Make it more natural and conversational and complete if needed
3. Keep the same meaning and tone
4. Make it sound like natural speech appropriate for my context
5. Keep it concise and clear
6. The phrase should be structured like it is coming from me
7. Consider my current situation, recent activities, and personal context when cleaning up

For example:
- "dad beekeeping" → "My dad is a beekeeper"
- "want food hungry" → "I want food because I'm hungry"  
- "go store later" → "I want to go to the store later"

Return only the improved text, nothing else."""
        
        # Use caching function with proper signature
        cleaned_text = await _generate_gemini_content_with_caching(
            account_id=account_id,
            aac_user_id=aac_user_id,
            prompt_text=user_query_only,  # Use the full prompt as fallback if caching fails
            user_query_only=user_query_only,
            cache_manager=cache_manager,
            generation_config=None
        )
        
        # Clean up the response (remove quotes if present)
        cleaned_text = cleaned_text.strip().strip('"').strip("'")
        
        # If the LLM response is much longer or seems off, return original
        if len(cleaned_text) > len(request.text_to_cleanup) * 3:
            cleaned_text = request.text_to_cleanup
        
        logging.info(f"Cleaned up text with RAG context from '{request.text_to_cleanup}' to '{cleaned_text}' for account {account_id}, user {aac_user_id}")
        return JSONResponse(content={"cleaned_text": cleaned_text})
        
    except Exception as e:
        logging.error(f"Error cleaning up text for account {account_id}, user {aac_user_id}: {e}", exc_info=True)
        # Return original text if cleanup fails
        return JSONResponse(content={"cleaned_text": request.text_to_cleanup})


class FreestyleCategoryWordsRequest(BaseModel):
    category: str = Field(..., min_length=1, description="Category name for word generation")
    build_space_content: Optional[str] = Field("", description="Current build space content for context")
    exclude_words: Optional[List[str]] = Field(default_factory=list, description="Words to exclude from generation")

@app.post("/api/freestyle/category-words")
async def generate_category_words(
    request: FreestyleCategoryWordsRequest,
    current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]
):
    """
    Generates word options for a specific category using LLM with user context
    """
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    
    try:
        # Load user settings to get FreestyleOptions
        settings = await load_settings_from_file(account_id, aac_user_id)
        freestyle_options = settings.get("FreestyleOptions", 6)  # Default to 6 if not set
        
        # Load user context for better word generation
        user_info = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/user_narrative",
            default_data={"narrative": ""}
        )
        
        user_current = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_state",
            default_data=DEFAULT_USER_CURRENT.copy()
        )
        
        # Build exclude words clause
        exclude_clause = ""
        if request.exclude_words:
            exclude_words_str = ", ".join(request.exclude_words)
            exclude_clause = f" Do not include these words that were already shown: {exclude_words_str}."
        
        # Build context clause
        context_clause = ""
        if request.build_space_content:
            context_clause = f" Current message being built: '{request.build_space_content}'."
        
        # Get comprehensive user context
        user_context_parts = []
        if user_info.get("narrative"):
            user_context_parts.append(f"User info: {user_info['narrative']}")
        if user_current.get("location"):
            user_context_parts.append(f"Current location: {user_current['location']}")
        if user_current.get("people"):
            user_context_parts.append(f"People present: {user_current['people']}")
        if user_current.get("activity"):
            user_context_parts.append(f"Current activity: {user_current['activity']}")
            
        user_context = " | ".join(user_context_parts) if user_context_parts else "General conversation"
        
        # Create the prompt for word generation with enhanced context
        prompt = f"""Given the user context: '{user_context}' and category '{request.category}', generate {freestyle_options} single words for this category.{context_clause}{exclude_clause}

IMPORTANT: Use the user context to provide personalized, relevant words. For example:
- If category is "People" and user context mentions specific people, prioritize those names
- If category is "Places" and user has a current location, include relevant locations
- If category is "Activities" and user has a current activity, include related activities

Requirements:
- Provide exactly {freestyle_options} single words (no phrases)
- Words should be relevant to "{request.category}"
- Prioritize words from user context when applicable
- Words should be commonly used and appropriate for AAC communication
- Each word should be useful for building messages
- Return only the words, one per line, no numbering or formatting

Category: {request.category}"""

        # Generate words using LLM
        words_response = await _generate_gemini_content_with_fallback(prompt, None, account_id, aac_user_id)
        
        # Parse the response into individual words
        words = []
        if words_response:
            lines = words_response.strip().split('\n')
            for line in lines:
                word = line.strip().strip('-').strip('*').strip().strip('"').strip("'")
                if word and len(word.split()) == 1:  # Ensure single words only
                    words.append(word)
        
        # Ensure we have the right number of words
        if len(words) < freestyle_options:
            # If we don't have enough, pad with generic words for the category
            generic_words = get_generic_category_words(request.category)
            for generic_word in generic_words:
                if generic_word not in words and generic_word not in request.exclude_words:
                    words.append(generic_word)
                    if len(words) >= freestyle_options:
                        break
        
        # Trim to exact number requested
        words = words[:freestyle_options]
        
        logging.info(f"Generated {len(words)} words for category '{request.category}' for account {account_id}, user {aac_user_id}")
        return JSONResponse(content={"words": words})
        
    except Exception as e:
        logging.error(f"Error generating category words for account {account_id}, user {aac_user_id}: {e}", exc_info=True)
        return JSONResponse(content={"words": []})

def get_generic_category_words(category: str) -> List[str]:
    """Get generic fallback words for a category"""
    generic_words = {
        "People": ["mom", "dad", "friend", "teacher", "doctor", "family"],
        "Places": ["home", "school", "store", "park", "hospital", "library"],
        "Animals": ["dog", "cat", "bird", "fish", "horse", "rabbit"],
        "Around the House": ["kitchen", "bedroom", "bathroom", "living", "garage", "yard"],
        "In the Room": ["chair", "table", "bed", "lamp", "window", "door"],
        "General things": ["book", "phone", "keys", "bag", "water", "food"],
        "Actions": ["go", "come", "eat", "drink", "sleep", "play"],
        "Feelings & Emotions": ["happy", "sad", "angry", "excited", "tired", "scared"],
        "Questions & Comments": ["what", "where", "when", "how", "why", "please"],
        "Times and Dates": ["today", "tomorrow", "morning", "night", "week", "month"],
        "Activities & Hobbies": ["read", "music", "games", "sports", "art", "cooking"],
        "Medical & Health": ["medicine", "doctor", "hurt", "sick", "better", "hospital"],
        "Food & Drinks": ["water", "milk", "bread", "apple", "sandwich", "juice"],
        "Colors & Descriptions": ["red", "blue", "big", "small", "hot", "cold"],
        "Numbers & Quantities": ["one", "two", "many", "few", "more", "less"],
        "School & Learning": ["book", "pencil", "teacher", "class", "homework", "test"],
        "Transportation": ["car", "bus", "train", "bike", "walk", "plane"],
        "Weather": ["sunny", "rainy", "cold", "hot", "cloudy", "windy"],
        "Technology": ["computer", "phone", "tablet", "internet", "email", "game"],
        "Sports & Games": ["ball", "team", "play", "win", "run", "jump"]
    }
    return generic_words.get(category, ["thing", "stuff", "item", "object", "something", "anything"])


# --- ADMIN ENDPOINTS ---

class CopyProfilesBetweenAccountsRequest(BaseModel):
    source_email: str
    target_email: str
    admin_password: str = "admin123"  # Simple password protection

@app.post("/api/admin/copy-profiles-between-accounts")
async def copy_profiles_between_accounts(request: CopyProfilesBetweenAccountsRequest):
    """
    Admin endpoint to copy all AAC user profiles from one Firebase account to another.
    This is specifically for setting up the demo readonly account.
    """
    
    # Simple password protection
    if request.admin_password != "admin123":
        raise HTTPException(status_code=403, detail="Invalid admin password")
    
    try:
        logging.info(f"Starting profile copy from {request.source_email} to {request.target_email}")
        
        # Get account IDs from Firebase Auth
        source_account_id = None
        target_account_id = None
        
        try:
            source_user_record = auth.get_user_by_email(request.source_email)
            source_account_id = source_user_record.uid
            logging.info(f"Found source account ID: {source_account_id}")
        except auth.UserNotFoundError:
            raise HTTPException(status_code=404, detail=f"Source email {request.source_email} not found")
        
        try:
            target_user_record = auth.get_user_by_email(request.target_email)
            target_account_id = target_user_record.uid
            logging.info(f"Found target account ID: {target_account_id}")
        except auth.UserNotFoundError:
            raise HTTPException(status_code=404, detail=f"Target email {request.target_email} not found")
        
        # Get all users from source account
        source_users_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(source_account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
        source_users_docs = await asyncio.to_thread(source_users_ref.stream)
        
        source_users = []
        for doc in source_users_docs:
            user_data = doc.to_dict()
            user_data['aac_user_id'] = doc.id
            source_users.append(user_data)
        
        if not source_users:
            raise HTTPException(status_code=404, detail=f"No profiles found in source account {request.source_email}")
        
        logging.info(f"Found {len(source_users)} profiles to copy")
        
        # Check existing users in target account and clean them up
        target_users_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(target_account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
        existing_target_docs = await asyncio.to_thread(target_users_ref.stream)
        existing_target_users = list(existing_target_docs)
        existing_count = len(existing_target_users)
        
        # Clean up existing profiles in target account to avoid duplicates
        if existing_count > 0:
            logging.info(f"Found {existing_count} existing profiles in target account. Cleaning up before copying...")
            
            for existing_doc in existing_target_users:
                try:
                    # Delete all user data subcollections first
                    existing_user_id = existing_doc.id
                    
                    # Delete user data subcollections
                    subcollections = ['info', 'settings', 'favorites', 'threads', 'birthdays', 'user_current', 'user_narrative']
                    for subcoll in subcollections:
                        subcoll_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(target_account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION).document(existing_user_id).collection(subcoll)
                        docs = await asyncio.to_thread(subcoll_ref.stream)
                        for doc in docs:
                            await asyncio.to_thread(doc.reference.delete)
                    
                    # Delete the user document itself
                    await asyncio.to_thread(existing_doc.reference.delete)
                    logging.info(f"Deleted existing profile: {existing_doc.to_dict().get('display_name', existing_user_id)}")
                    
                except Exception as e:
                    logging.error(f"Error deleting existing profile {existing_user_id}: {e}")
            
            logging.info(f"Cleanup completed. Removed {existing_count} existing profiles.")
        else:
            logging.info("No existing profiles found in target account.")
        
        copied_profiles = []
        failed_profiles = []
        
        # Copy each user
        for user in source_users:
            display_name = user.get('display_name', 'Unknown')
            source_user_id = user['aac_user_id']
            
            try:
                logging.info(f"Copying profile: {display_name}")
                
                # Generate new user ID for target account
                new_user_id = str(uuid.uuid4())
                
                # Create user document in target account
                target_user_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(target_account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION).document(new_user_id)
                
                # Prepare user data (remove old aac_user_id)
                clean_user_data = {k: v for k, v in user.items() if k != 'aac_user_id'}
                clean_user_data['created_at'] = dt.now().isoformat()
                clean_user_data['last_updated'] = dt.now().isoformat()
                
                # Set the user document
                await asyncio.to_thread(target_user_ref.set, clean_user_data)
                
                # Copy all user data across accounts
                await _copy_user_data_cross_account(source_account_id, source_user_id, target_account_id, new_user_id)
                
                copied_profiles.append({
                    "display_name": display_name,
                    "source_id": source_user_id,
                    "target_id": new_user_id
                })
                
                logging.info(f"Successfully copied profile: {display_name}")
                
            except Exception as e:
                logging.error(f"Failed to copy profile {display_name}: {e}", exc_info=True)
                failed_profiles.append({
                    "display_name": display_name,
                    "error": str(e)
                })
        
        # Update target account user limit
        new_user_limit = existing_count + len(copied_profiles) + 2  # +2 for buffer
        target_account_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(target_account_id)
        await asyncio.to_thread(target_account_ref.update, {
            "num_users_allowed": new_user_limit,
            "last_updated": dt.now().isoformat()
        })
        
        logging.info(f"Profile copy complete. Copied {len(copied_profiles)} profiles, failed {len(failed_profiles)}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Successfully copied {len(copied_profiles)} out of {len(source_users)} profiles",
            "source_email": request.source_email,
            "target_email": request.target_email,
            "copied_count": len(copied_profiles),
            "failed_count": len(failed_profiles),
            "copied_profiles": copied_profiles,
            "failed_profiles": failed_profiles,
            "new_user_limit": new_user_limit
        })
        
    except Exception as e:
        logging.error(f"Error copying profiles between accounts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to copy profiles: {str(e)}")


class DebugUserInfoRequest(BaseModel):
    source_email: str
    target_email: str
    admin_password: str = "admin123"

@app.post("/api/admin/debug-user-info")
async def debug_user_info_endpoint(request: DebugUserInfoRequest):
    """Debug endpoint to check user info in both accounts"""
    
    # Check admin password
    if request.admin_password != "admin123":
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    try:
        # Get account IDs from Firebase Auth
        source_account_id = None
        target_account_id = None
        
        try:
            source_user_record = auth.get_user_by_email(request.source_email)
            source_account_id = source_user_record.uid
        except auth.UserNotFoundError:
            raise HTTPException(status_code=404, detail=f"Source email {request.source_email} not found")
        
        try:
            target_user_record = auth.get_user_by_email(request.target_email)
            target_account_id = target_user_record.uid
        except auth.UserNotFoundError:
            raise HTTPException(status_code=404, detail=f"Target email {request.target_email} not found")
        
        # Get users from source account
        source_users_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(source_account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
        source_docs = await asyncio.to_thread(source_users_ref.stream)
        source_users = []
        for doc in source_docs:
            user_data = doc.to_dict()
            user_data['aac_user_id'] = doc.id
            source_users.append(user_data)
        
        # Get users from target account
        target_users_ref = firestore_db.collection(FIRESTORE_ACCOUNTS_COLLECTION).document(target_account_id).collection(FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION)
        target_docs = await asyncio.to_thread(target_users_ref.stream)
        target_users = []
        for doc in target_docs:
            user_data = doc.to_dict()
            user_data['aac_user_id'] = doc.id
            target_users.append(user_data)
        
        # Check user info for a sample user from each account
        debug_info = {
            "source_account_id": source_account_id,
            "target_account_id": target_account_id,
            "source_users_count": len(source_users),
            "target_users_count": len(target_users),
            "source_sample_user_info": None,
            "target_sample_user_info": None
        }
        
        # Get user info for first user in source account
        if source_users:
            sample_source_user = source_users[0]
            source_user_info = await load_firestore_document(
                account_id=source_account_id,
                aac_user_id=sample_source_user['aac_user_id'],
                doc_subpath="info/user_info",
                default_data=DEFAULT_USER_INFO.copy()
            )
            debug_info["source_sample_user_info"] = {
                "display_name": sample_source_user.get('display_name', 'Unknown'),
                "user_id": sample_source_user['aac_user_id'],
                "user_info": source_user_info
            }
        
        # Get user info for first user in target account
        if target_users:
            sample_target_user = target_users[0]
            target_user_info = await load_firestore_document(
                account_id=target_account_id,
                aac_user_id=sample_target_user['aac_user_id'],
                doc_subpath="info/user_info",
                default_data=DEFAULT_USER_INFO.copy()
            )
            debug_info["target_sample_user_info"] = {
                "display_name": sample_target_user.get('display_name', 'Unknown'),
                "user_id": sample_target_user['aac_user_id'],
                "user_info": target_user_info
            }
        
        return JSONResponse(content=debug_info)
        
    except Exception as e:
        logging.error(f"Error debugging user info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to debug user info: {str(e)}")


@app.post("/api/admin/quick-user-info-check")
async def quick_user_info_check(request: Request):
    try:
        data = await request.json()
        admin_password = data.get('admin_password')
        source_email = data.get('source_email')
        target_email = data.get('target_email')
        
        if admin_password != "admin123":
            raise HTTPException(status_code=401, detail="Invalid admin password")
        
        if not source_email or not target_email:
            raise HTTPException(status_code=400, detail="Source and target emails required")
        
        result = {
            "source_email": source_email,
            "target_email": target_email,
            "timestamp": datetime.now().isoformat()
        }
        
        # Get account IDs from Firebase Auth
        try:
            source_user_record = auth.get_user_by_email(source_email)
            source_account_id = source_user_record.uid
            result["source_account_id"] = source_account_id
        except auth.UserNotFoundError:
            result["error"] = f"Source email {source_email} not found"
            return JSONResponse(content=result)
        
        try:
            target_user_record = auth.get_user_by_email(target_email)
            target_account_id = target_user_record.uid
            result["target_account_id"] = target_account_id
        except auth.UserNotFoundError:
            result["error"] = f"Target email {target_email} not found"
            return JSONResponse(content=result)
        
        # Quick check - get first user from each account
        source_users = load_firestore_collection(account_id=source_account_id, collection_name="user_settings")
        target_users = load_firestore_collection(account_id=target_account_id, collection_name="user_settings")
        
        source_user_count = len(source_users) if source_users else 0
        target_user_count = len(target_users) if target_users else 0
        
        result["source_user_count"] = source_user_count
        result["target_user_count"] = target_user_count
        
        if source_user_count > 0 and target_user_count > 0:
            # Get first user from each
            source_user = list(source_users.values())[0]
            target_user = list(target_users.values())[0]
            
            # Quick check of user info
            source_user_info = load_firestore_document(
                account_id=source_account_id,
                aac_user_id=source_user['aac_user_id'],
                doc_subpath="info/user_info",
                default_data=DEFAULT_USER_INFO.copy()
            )
            
            target_user_info = load_firestore_document(
                account_id=target_account_id,
                aac_user_id=target_user['aac_user_id'],
                doc_subpath="info/user_info",
                default_data=DEFAULT_USER_INFO.copy()
            )
            
            result["source_user_info_keys"] = list(source_user_info.keys()) if source_user_info else []
            result["target_user_info_keys"] = list(target_user_info.keys()) if target_user_info else []
            result["source_display_name"] = source_user_info.get('display_name', 'Not set') if source_user_info else 'No user info'
            result["target_display_name"] = target_user_info.get('display_name', 'Not set') if target_user_info else 'No user info'
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"Error in quick user info check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to check user info: {str(e)}")


# =============================================================================
# AAC IMAGE GENERATION SERVICE
# =============================================================================

# Import additional dependencies for image generation
try:
    from google.cloud import aiplatform, storage, secretmanager
    from google.cloud.aiplatform.gapic.schema import predict
    import base64
    import io
    from PIL import Image
    import uuid
    from datetime import datetime, timezone
    import asyncio
    VERTEX_AI_AVAILABLE = True
    
    # Initialize Vertex AI
    aiplatform.init(project=CONFIG['gcp_project_id'], location="us-central1")
    
    # Initialize storage client for AAC images
    storage_client = storage.Client(project=CONFIG['gcp_project_id'])
    AAC_IMAGES_BUCKET_NAME = f"{CONFIG['gcp_project_id']}-aac-images"
    
    # Initialize Secret Manager client
    secret_client = secretmanager.SecretManagerServiceClient()
    
except ImportError as e:
    logging.warning(f"Image generation dependencies not available: {e}")
    VERTEX_AI_AVAILABLE = False

class ImageGenerationRequest(BaseModel):
    concept: str
    variations: int = 10
    style: str = "Apple memoji style"

class ImageTaggingRequest(BaseModel):
    image_url: str
    concept: str
    subconcept: str

class ImageStoreRequest(BaseModel):
    images: List[Dict[str, str]]  # List of {image_url, concept, subconcept}

# Admin verification dependency
async def verify_admin_user(token_info: Annotated[Dict[str, str], Depends(verify_firebase_token_only)]) -> Dict[str, str]:
    """Verify that the authenticated user is admin@talkwithbravo.com"""
    if token_info.get("email") != "admin@talkwithbravo.com":
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    return token_info

async def get_gemini_api_key():
    """Get Gemini API key from Secret Manager or environment"""
    try:
        secret_name = f"projects/{CONFIG['gcp_project_id']}/secrets/bravo-google-api-key/versions/latest"
        response = await asyncio.to_thread(secret_client.access_secret_version, request={"name": secret_name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logging.warning(f"Could not access Secret Manager for Gemini API key: {e}")
        # Fallback to environment variable
        api_key = os.environ.get('GEMINI_API_KEY')
        if api_key:
            return api_key
        else:
            raise HTTPException(status_code=503, detail="Gemini API key not configured")

async def ensure_aac_images_bucket():
    """Ensure the AAC images bucket exists and is configured for public access"""
    try:
        bucket = storage_client.bucket(AAC_IMAGES_BUCKET_NAME)
        if not await asyncio.to_thread(bucket.exists):
            await asyncio.to_thread(bucket.create, location="US-CENTRAL1")
            logging.info(f"Created AAC images bucket: {AAC_IMAGES_BUCKET_NAME}")
            
            # For uniform bucket-level access, set the IAM policy to allow public read
            try:
                from google.cloud import storage
                policy = await asyncio.to_thread(bucket.get_iam_policy, requested_policy_version=3)
                policy.bindings.append({
                    "role": "roles/storage.objectViewer",
                    "members": ["allUsers"]
                })
                await asyncio.to_thread(bucket.set_iam_policy, policy)
                logging.info(f"Configured public read access for bucket: {AAC_IMAGES_BUCKET_NAME}")
            except Exception as iam_error:
                logging.warning(f"Could not set public IAM policy (bucket may already be configured): {iam_error}")
        
        return bucket
    except Exception as e:
        logging.error(f"Error ensuring AAC images bucket: {e}")
        raise HTTPException(status_code=500, detail=f"Storage service error: {str(e)}")

async def generate_subconcepts(concept: str, count: int) -> List[str]:
    """Use Gemini to generate subconcepts from a main concept"""
    api_key = await get_gemini_api_key()
    genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    prompt = f"""
    Generate {count} specific subconcepts related to "{concept}" that would be useful for AAC (Augmentative and Alternative Communication) purposes.
    
    Requirements:
    - Each subconcept should be 1-3 words maximum
    - Focus on common, everyday items/concepts that AAC users would communicate about
    - Make them diverse and representative of the broader concept
    - Return only the subconcepts, one per line, no numbering or formatting
    
    Example: If concept is "animals", return things like:
    dog
    cat
    bird
    fish
    rabbit
    """
    
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        subconcepts = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
        return subconcepts[:count]  # Ensure we don't exceed requested count
    except Exception as e:
        logging.error(f"Error generating subconcepts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate subconcepts: {str(e)}")

async def generate_image_with_vertex_imagen(prompt: str, max_retries: int = 2) -> bytes:
    """Generate image using Vertex AI Imagen (proven working approach from ImageCreator)"""
    for attempt in range(max_retries + 1):
        try:
            from google.auth.transport.requests import Request
            from google.auth import default
            
            logging.info(f"Attempting to generate image for prompt: {prompt} (attempt {attempt + 1}/{max_retries + 1})")
            
            # Get default credentials
            credentials, project = default()
            
            # Refresh credentials to get access token
            credentials.refresh(Request())
            access_token = credentials.token
            logging.info(f"Successfully obtained access token (attempt {attempt + 1})")
            
            # Use Vertex AI Imagen API (proven working endpoint)
            endpoint = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{CONFIG['gcp_project_id']}/locations/us-central1/publishers/google/models/imagegeneration@006:predict"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            # Enhanced prompt for AAC-appropriate images
            enhanced_prompt = f"""Create a high-quality, clear illustration of {prompt}. 
            Style requirements:
            - Simple, clean design suitable for AAC (Augmentative and Alternative Communication)
            - Clear, recognizable representation
            - Good contrast and visibility
            - Child-friendly and appropriate for all ages
            - Bright, clear colors
            - No text or words in the image
            - Square aspect ratio, centered composition
            - High contrast between subject and background for AAC clarity
            
            Subject: {prompt}
            Make it clear, simple, and easily recognizable for communication purposes."""
            
            data = {
                "instances": [{
                    "prompt": enhanced_prompt
                }],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "1:1",
                    "safetyFilterLevel": "block_some",
                    "personGeneration": "allow_adult"
                }
            }
            
            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=headers, json=data, timeout=120) as response:
                    logging.info(f"Vertex AI response status: {response.status} (attempt {attempt + 1})")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logging.warning(f"Error response (attempt {attempt + 1}): {error_text}")
                        if attempt < max_retries:
                            logging.info(f"Retrying in 2 seconds...")
                            await asyncio.sleep(2)
                            continue
                        raise Exception(f"Vertex AI API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    logging.info(f"API Response structure: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                    
                    # Extract image data from response
                    if 'predictions' in result and len(result['predictions']) > 0:
                        prediction = result['predictions'][0]
                        logging.info(f"Prediction keys: {list(prediction.keys()) if isinstance(prediction, dict) else 'Not a dict'}")
                        
                        # Check different possible response formats
                        if 'bytesBase64Encoded' in prediction:
                            logging.info(f"Found image in bytesBase64Encoded (attempt {attempt + 1})")
                            return base64.b64decode(prediction['bytesBase64Encoded'])
                        elif 'generated_image' in prediction:
                            logging.info(f"Found image in generated_image (attempt {attempt + 1})")
                            image_data = prediction['generated_image'].get('bytesBase64Encoded')
                            if image_data:
                                return base64.b64decode(image_data)
                        elif 'image' in prediction:
                            logging.info(f"Found image in image field (attempt {attempt + 1})")
                            return base64.b64decode(prediction['image'])
                        else:
                            logging.warning(f"Unexpected prediction format (attempt {attempt + 1}): {prediction}")
                    else:
                        logging.warning(f"Empty or no predictions in response (attempt {attempt + 1})")
                    
                    if attempt < max_retries:
                        logging.info(f"No valid image data found, retrying in 2 seconds...")
                        await asyncio.sleep(2)
                        continue
                    
                    raise Exception("No valid image data found in Vertex AI response after all retries")
        
        except Exception as e:
            logging.warning(f"Error generating image with Vertex AI Imagen (attempt {attempt + 1}): {e}")
            if attempt < max_retries:
                logging.info(f"Retrying in 3 seconds...")
                await asyncio.sleep(3)
                continue
            raise HTTPException(status_code=500, detail=f"Failed to generate image after {max_retries + 1} attempts: {str(e)}")

# Use Vertex AI Imagen for image generation (proven working approach)
generate_image_with_gemini = generate_image_with_vertex_imagen

async def upload_image_to_storage(image_bytes: bytes, filename: str) -> str:
    """Upload image to Google Cloud Storage and return public URL"""
    try:
        bucket = await ensure_aac_images_bucket()
        blob = bucket.blob(f"global/{filename}")
        
        # Upload image with public-read content
        await asyncio.to_thread(blob.upload_from_string, image_bytes, content_type='image/png')
        
        # For uniform bucket-level access, we construct the public URL directly
        # The bucket should already be configured for public access via IAM policies
        public_url = f"https://storage.googleapis.com/{bucket.name}/{blob.name}"
        
        logging.info(f"Successfully uploaded image: {filename} -> {public_url}")
        return public_url
    except Exception as e:
        logging.error(f"Error uploading image to storage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

async def generate_image_tags(image_url: str, concept: str, subconcept: str) -> List[str]:
    """Use Gemini to analyze image and generate relevant tags"""
    try:
        api_key = await get_gemini_api_key()
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""
        Analyze this image that represents the concept "{subconcept}" from the category "{concept}".
        
        Generate 8-12 relevant tags for AAC (Augmentative and Alternative Communication) purposes.
        
        Requirements:
        - Include the main concept and subconcept
        - Add descriptive words about appearance, function, context
        - Use simple, common words that AAC users might search for
        - Include both specific and general terms
        - Focus on communication-relevant aspects
        
        Return only the tags, separated by commas, no other text.
        
        Example format: dog, animal, pet, furry, four legs, companion, brown, sitting
        """
        
        # Download image for analysis
        import requests
        response = requests.get(image_url)
        if response.status_code == 200:
            # Convert to base64 for Gemini
            image_data = base64.b64encode(response.content).decode()
            
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt, {"mime_type": "image/png", "data": image_data}]
            )
            
            tags_text = response.text.strip()
            tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
            return tags
        else:
            # Fallback to basic tags if image analysis fails
            return [concept, subconcept, "aac", "communication"]
            
    except Exception as e:
        logging.warning(f"Error generating image tags: {e}")
        # Return basic tags as fallback
        return [concept, subconcept, "aac", "communication"]

@app.get("/imagecreator")
async def serve_image_creator():
    """Serve the AAC Image Creator interface with client-side auth check"""
    return FileResponse(os.path.join(static_file_path, "imagecreator.html"))

@app.post("/api/imagecreator/generate-subconcepts")
async def api_generate_subconcepts(
    request: ImageGenerationRequest,
    token_info: Annotated[Dict[str, str], Depends(verify_admin_user)]
):
    """Generate subconcepts for a given concept"""
    if not VERTEX_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="Image generation service not available")
    
    try:
        subconcepts = await generate_subconcepts(request.concept, request.variations)
        return {"concept": request.concept, "subconcepts": subconcepts}
    except Exception as e:
        logging.error(f"Error in generate subconcepts API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/imagecreator/generate-images")
async def api_generate_images(
    concept: str = Body(...),
    subconcepts: List[str] = Body(...),
    style: str = Body(default="Apple memoji style"),
    token_info: Annotated[Dict[str, str], Depends(verify_admin_user)] = None
):
    """Generate images for a list of subconcepts"""
    if not VERTEX_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="Image generation service not available")
    
    try:
        results = []
        
        for subconcept in subconcepts:
            # Create detailed prompt
            prompt = f"{style}, {subconcept}, {concept}, clean background, high quality, friendly appearance, suitable for AAC communication"
            
            # Generate image
            image_bytes = await generate_image_with_gemini(prompt)
            
            # Create filename
            filename = f"{concept}_{subconcept}_{uuid.uuid4().hex[:8]}.png"
            
            # Upload to storage
            image_url = await upload_image_to_storage(image_bytes, filename)
            
            results.append({
                "subconcept": subconcept,
                "image_url": image_url,
                "filename": filename
            })
        
        return {"concept": concept, "images": results}
        
    except Exception as e:
        logging.error(f"Error in generate images API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/imagecreator/store-images")
async def api_store_images(
    request: ImageStoreRequest,
    token_info: Annotated[Dict[str, str], Depends(verify_admin_user)]
):
    """Store selected images to Firestore with tags"""
    if not VERTEX_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="Image generation service not available")
    
    try:
        stored_images = []
        
        for image_data in request.images:
            # Generate tags
            tags = await generate_image_tags(
                image_data["image_url"],
                image_data["concept"],
                image_data["subconcept"]
            )
            
            # Create document data
            doc_data = {
                "concept": image_data["concept"],
                "subconcept": image_data["subconcept"],
                "tags": tags,
                "image_url": image_data["image_url"],
                "image_type": "global",
                "user_id": None,
                "created_at": datetime.now(timezone.utc),
                "created_by": "admin",
                "approved": True
            }
            
            # Store in Firestore
            doc_ref = firestore_db.collection("aac_images").add(doc_data)
            doc_id = doc_ref[1].id
            
            stored_images.append({
                "id": doc_id,
                **doc_data,
                "created_at": doc_data["created_at"].isoformat()
            })
        
        return {"stored_images": stored_images}
        
    except Exception as e:
        logging.error(f"Error in store images API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/imagecreator/images")
async def api_get_images(
    concept: str = None,
    tag: str = None,
    limit: int = 50,
    token_info: Annotated[Dict[str, str], Depends(verify_admin_user)] = None
):
    """Get stored AAC images with optional filtering"""
    try:
        query = firestore_db.collection("aac_images")
        
        # Add filters
        if concept:
            query = query.where("concept", "==", concept)
        
        if tag:
            query = query.where("tags", "array_contains", tag)
        
        # Limit results
        query = query.limit(limit)
        
        # Execute query
        docs = await asyncio.to_thread(query.get)
        
        images = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            if "created_at" in data and hasattr(data["created_at"], "isoformat"):
                data["created_at"] = data["created_at"].isoformat()
            images.append(data)
        
        return {"images": images}
        
    except Exception as e:
        logging.error(f"Error in get images API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/imagecreator/images/{image_id}")
async def api_delete_image(
    image_id: str,
    token_info: Annotated[Dict[str, str], Depends(verify_admin_user)]
):
    """Delete an AAC image"""
    try:
        # Get image document
        doc_ref = firestore_db.collection("aac_images").document(image_id)
        doc = await asyncio.to_thread(doc_ref.get)
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Delete from Firestore
        await asyncio.to_thread(doc_ref.delete)
        
        return {"success": True, "message": "Image deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in delete image API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/imagecreator/images/{image_id}/tags")
async def api_update_image_tags(
    image_id: str,
    tags: List[str] = Body(...),
    token_info: Annotated[Dict[str, str], Depends(verify_admin_user)] = None
):
    """Update tags for an AAC image"""
    try:
        doc_ref = firestore_db.collection("aac_images").document(image_id)
        doc = await asyncio.to_thread(doc_ref.get)
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Update tags
        await asyncio.to_thread(doc_ref.update, {"tags": tags})
        
        return {"success": True, "message": "Tags updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in update image tags API: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)