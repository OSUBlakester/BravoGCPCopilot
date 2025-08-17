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
        ALLOWED_ORIGINS = ['https://talkwithbravo.com']
        DOMAIN = os.getenv('DOMAIN', 'talkwithbravo.com')
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
        stats = cache_manager.get_cache_stats()
        return JSONResponse(content={
            "status": "success",
            "cache_stats": stats,
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
        
        logging.info(f"Serving frontend config with projectId: {client_config.get('projectId', 'unknown')}")
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
            {"row": 0,"col": 3,"text": "Jokes", "LLMQuery": "Generate #LLMOptions random, unique jokes or one-liners. Each joke should include both the question and punchline together in the format 'Question? Punchline!' with just a question mark between them. Do NOT split questions and punchlines into separate options.", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
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
            {"row": 0,"col": 2,"text": "My Upcoming Plans", "LLMQuery": "Based on the user diary, generate #LLMOptions statements based on any upcoming planned activities. Each statement should be phrased conversationally as if they are coming from the user and telling someone nearby what the user has done recently.", "targetPage": "home", "queryType": "", "speechPhrase": None, "hidden": False},
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

        return {"account_id": target_account_id, "aac_user_id": x_user_id}

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





# --- Logging Setup ---
if not logging.getLogger().hasHandlers(): # Add basic config if no handlers are set
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
print("DEBUG: Attempting to configure logging...") # For visibility during startup

# The force=True argument (Python 3.8+) ensures that your basicConfig call
# will remove any existing handlers on the root logger and apply this configuration.
# This is often necessary when running within frameworks like Uvicorn that might
# also try to configure logging.
try:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
except TypeError:
    # Fallback for Python < 3.8 (force argument not available)
    # You might need to manually remove handlers if basicConfig is still ineffective:
    # for handler in logging.root.handlers[:]: logging.root.removeHandler(handler)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("DEBUG: Logging configured. This INFO message should appear in the terminal if setup is correct.")
print("DEBUG: Logging configuration attempt finished.")


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


# --- Dynamic Static Page Routes ---
# List of static HTML files to be served from the root path.
STATIC_PAGES = [
    "gridpage.html",
    "admin.html",
    "admin_pages.html",
    "admin_settings.html",
    "user_current_admin.html",
    "audio_admin.html",
    "currentevents.html",
    "user_info_admin.html",
    "user_favorites_admin.html",
    "favorites_admin.html",
    "favorites.html",
    "web_scraping_help_page.html",
    "admin_nav.html",
    "admin_audit_report.html",
    "auth.html",
    "user_diary_admin.html",
    "freestyle.html",
    "threads.html"
]

for page in STATIC_PAGES:
    @app.get(f"/{page}")
    async def serve_static_page(page_name: str = page): # Use default argument to capture page name
        return FileResponse(f"static/{page_name}")
    

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
        await cache_manager.invalidate_by_endpoint(account_id, aac_user_id, "/pages")
        
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
        await cache_manager.invalidate_by_endpoint(account_id, aac_user_id, "/pages")
        
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
        await cache_manager.invalidate_by_endpoint(account_id, aac_user_id, "/pages")
        
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
        await cache_manager.invalidate_by_endpoint(account_id, aac_user_id, "/user_current")
        
        # Update USER_PROFILE cache with new current state
        # Get user info to maintain complete cache structure
        user_info_content_dict = await load_firestore_document(
            account_id, aac_user_id, "info/user_narrative"
        )
        user_info_content = user_info_content_dict.get("narrative", "") if user_info_content_dict else ""
        
        await cache_manager.store_cached_context(account_id, aac_user_id, "USER_PROFILE", {
            "user_info": user_info_content,
            "user_current": current_state_content,
            "updated_at": saved_at
        })
        logging.info(f"Updated USER_PROFILE cache with new current state for account {account_id} and user {aac_user_id}")
    
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

DEFAULT_USER_INFO = {"narrative": "Default user info."}
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
    "enableMoodSelection": False,  # Default mood selection disabled
    "currentMood": None,  # Default no mood selected
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
class CacheType:
    """Cache type constants"""
    USER_PROFILE = "user_profile"
    LOCATION_DATA = "location_data" 
    FRIENDS_FAMILY = "friends_family"
    USER_SETTINGS = "user_settings"
    HOLIDAYS_BIRTHDAYS = "holidays_birthdays"
    RAG_CONTEXT = "rag_context"
    CONVERSATION_SESSION = "conversation_session"
    BUTTON_ACTIVITY = "button_activity"

class GeminiCacheManager:
    """Manages Gemini context caching and conversation sessions for performance optimization"""
    
    def __init__(self):
        self.gemini_caches = {}  # {user_key: {cache_type: gemini_cache_object}}
        self.conversation_sessions = {}  # {user_key: conversation_chat_session}
        self.cache_refresh_times = {}  # {user_key: {cache_type: last_refresh_timestamp}}
        
        # Cache invalidation rules - which admin changes invalidate which caches
        self.invalidation_rules = {
            "/update-user-info": [CacheType.USER_PROFILE, CacheType.RAG_CONTEXT],
            "/user_current": [CacheType.USER_PROFILE, CacheType.LOCATION_DATA, CacheType.RAG_CONTEXT],
            "/update-user-favorites": [CacheType.RAG_CONTEXT],
            "/api/favorites": [CacheType.RAG_CONTEXT],
            "/api/user-current-favorites": [CacheType.RAG_CONTEXT],
            "/pages": [CacheType.RAG_CONTEXT],  # Page layout changes might affect context
            "/api/audit/log-button-click": [CacheType.BUTTON_ACTIVITY],  # Button clicks invalidate activity cache
        }
        
        # Cache TTL settings (in seconds)
        self.cache_ttl = {
            CacheType.USER_PROFILE: 24 * 3600,      # 24 hours - changes rarely
            CacheType.LOCATION_DATA: 6 * 3600,      # 6 hours - changes moderately  
            CacheType.FRIENDS_FAMILY: 12 * 3600,    # 12 hours - changes rarely
            CacheType.USER_SETTINGS: 1 * 3600,      # 1 hour - changes more often
            CacheType.HOLIDAYS_BIRTHDAYS: 24 * 3600, # 24 hours - daily refresh
            CacheType.RAG_CONTEXT: 1 * 3600,        # 1 hour - depends on other data
            CacheType.CONVERSATION_SESSION: 4 * 3600, # 4 hours - conversation session
            CacheType.BUTTON_ACTIVITY: 6 * 3600     # 6 hours - recent button activity
        }
    
    def _get_user_key(self, account_id: str, aac_user_id: str) -> str:
        """Generate unique key for user cache storage"""
        return f"{account_id}_{aac_user_id}"
    
    async def is_cache_valid(self, account_id: str, aac_user_id: str, cache_type: str) -> bool:
        """Check if cache is still valid based on TTL"""
        user_key = self._get_user_key(account_id, aac_user_id)
        
        if user_key not in self.cache_refresh_times:
            return False
            
        if cache_type not in self.cache_refresh_times[user_key]:
            return False
            
        last_refresh = self.cache_refresh_times[user_key][cache_type]
        ttl = self.cache_ttl.get(cache_type, 3600)  # Default 1 hour
        
        return (dt.now().timestamp() - last_refresh) < ttl
    
    async def store_cached_context(self, account_id: str, aac_user_id: str, cache_type: str, context) -> bool:
        """Store context using Gemini caching API with fallback to local cache"""
        # Try Gemini caching first for better performance
        if await self.store_cached_context_with_gemini(account_id, aac_user_id, cache_type, context):
            return True
        
        # Fallback to local caching if Gemini caching fails
        try:
            user_key = self._get_user_key(account_id, aac_user_id)
            
            # Initialize user cache if needed
            if user_key not in self.gemini_caches:
                self.gemini_caches[user_key] = {}
            if user_key not in self.cache_refresh_times:
                self.cache_refresh_times[user_key] = {}
            
            # Store cache info locally as fallback
            self.gemini_caches[user_key][cache_type] = {
                "context": context,
                "created_at": dt.now().timestamp(),
                "ttl": self.cache_ttl.get(cache_type, 3600)
            }
            
            # Update refresh time
            self.cache_refresh_times[user_key][cache_type] = dt.now().timestamp()
            
            context_length = len(str(context)) if isinstance(context, (dict, list)) else len(context)
            logging.info(f"Cached context locally for {user_key}/{cache_type} (length: {context_length})")
            return True
            
        except Exception as e:
            logging.error(f"Error storing cached context for {account_id}/{aac_user_id}/{cache_type}: {e}")
            return False
    
    async def invalidate_cache(self, account_id: str, aac_user_id: str, cache_types: List[str], endpoint: str = None):
        """Invalidate specific cache types for a user"""
        user_key = self._get_user_key(account_id, aac_user_id)
        
        invalidated = []
        for cache_type in cache_types:
            if user_key in self.gemini_caches and cache_type in self.gemini_caches[user_key]:
                del self.gemini_caches[user_key][cache_type]
                invalidated.append(cache_type)
            
            if user_key in self.cache_refresh_times and cache_type in self.cache_refresh_times[user_key]:
                del self.cache_refresh_times[user_key][cache_type]
        
        if invalidated:
            logging.info(f"Cache invalidated for {user_key} by {endpoint}: {invalidated}")
        
        # Special handling for RAG context refresh
        if CacheType.RAG_CONTEXT in cache_types:
            await self.refresh_rag_context(account_id, aac_user_id)
    
    async def invalidate_by_endpoint(self, account_id: str, aac_user_id: str, endpoint: str):
        """Invalidate caches based on admin endpoint that was called"""
        cache_types = self.invalidation_rules.get(endpoint, [])
        if cache_types:
            await self.invalidate_cache(account_id, aac_user_id, cache_types, endpoint)
    
    async def refresh_rag_context(self, account_id: str, aac_user_id: str):
        """Refresh RAG context when user data changes"""
        try:
            # This would rebuild and update ChromaDB vectors based on new user data
            # For now, we'll just log the refresh
            logging.info(f"Refreshing RAG context for {account_id}/{aac_user_id}")
            # TODO: Implement RAG context refresh logic
            return True
        except Exception as e:
            logging.error(f"Error refreshing RAG context for {account_id}/{aac_user_id}: {e}")
            return False

    async def create_gemini_cached_content(self, cache_name: str, content: str, ttl_hours: int = 24) -> Optional[str]:
        """Create a Gemini cached content object and return cache name"""
        try:
            # Ensure content is a string
            content_str = str(content) if not isinstance(content, str) else content
            
            # Estimate token count (roughly 4 characters per token)
            estimated_tokens = len(content_str) // 4
            min_required_tokens = 2048
            
            if estimated_tokens < min_required_tokens:
                logging.info(f"Skipping cache creation for {cache_name}: estimated {estimated_tokens} tokens < {min_required_tokens} minimum")
                return None
            
            logging.info(f"Creating Gemini cached content: {cache_name} (content length: {len(content_str)}, estimated tokens: {estimated_tokens}, TTL: {ttl_hours}h)")
            
            # Format content for Gemini caching API - use genai.Content instead of dict
            import google.generativeai as genai
            
            # Create content using Gemini's Content class
            try:
                content_part = genai.Part.from_text(content_str)
                content_obj = genai.Content(parts=[content_part], role='user')
                formatted_content = [content_obj]
                
                logging.info(f"Attempting to create cached content with model: {GEMINI_PRIMARY_MODEL}")
                logging.info(f"Content formatted with genai.Content class")
                
            except Exception as content_error:
                logging.error(f"Error formatting content with genai.Content: {content_error}")
                # Fallback to simple dict format
                formatted_content = [{
                    'role': 'user',
                    'parts': [{'text': content_str}]
                }]
                logging.info(f"Using fallback dict format for content")
            
            # Create cached content using Gemini's caching API
            cached_content = caching.CachedContent.create(
                model=GEMINI_PRIMARY_MODEL,  # Use the configured primary model
                display_name=cache_name,
                contents=formatted_content,
                ttl=timedelta(hours=ttl_hours)  # Use timedelta directly, not dt.timedelta
            )
            
            logging.info(f"Successfully created Gemini cached content: {cache_name} -> {cached_content.name}")
            return cached_content.name
            
        except Exception as e:
            logging.error(f"Error creating Gemini cached content {cache_name}: {e}")
            return None
    
    async def get_gemini_cached_content(self, cache_name: str) -> Optional[str]:
        """Retrieve Gemini cached content by name"""
        try:
            cached_content = caching.CachedContent.get(cache_name)
            if cached_content:
                logging.info(f"Retrieved Gemini cached content: {cache_name}")
                return cached_content.name
            return None
        except Exception as e:
            logging.error(f"Error retrieving Gemini cached content {cache_name}: {e}")
            return None
    
    async def delete_gemini_cached_content(self, cache_name: str) -> bool:
        """Delete Gemini cached content"""
        try:
            cached_content = caching.CachedContent.get(cache_name)
            if cached_content:
                cached_content.delete()
                logging.info(f"Deleted Gemini cached content: {cache_name}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error deleting Gemini cached content {cache_name}: {e}")
            return False
    
    async def store_cached_context_with_gemini(self, account_id: str, aac_user_id: str, cache_type: str, context) -> bool:
        """Store context using actual Gemini caching API with batching for efficiency"""
        try:
            from datetime import datetime
            user_key = self._get_user_key(account_id, aac_user_id)
            
            # Store locally first for batching (direct local storage to avoid recursion)
            if user_key not in self.gemini_caches:
                self.gemini_caches[user_key] = {}
            if user_key not in self.cache_refresh_times:
                self.cache_refresh_times[user_key] = {}
            
            # Store cache info locally as fallback
            self.gemini_caches[user_key][cache_type] = {
                "context": context,
                "created_at": datetime.now().timestamp(),
                "ttl": self.cache_ttl.get(cache_type, 3600)
            }
            self.cache_refresh_times[user_key][cache_type] = datetime.now().timestamp()
            context_length = len(str(context)) if isinstance(context, (dict, list)) else len(context)
            logging.info(f"Cached context locally for {user_key}/{cache_type} (length: {context_length})")
            
            # Get all cached contexts for this user
            all_contexts = {}
            # Check all possible context types, not just a few
            for ctx_type in [CacheType.USER_PROFILE, CacheType.FRIENDS_FAMILY, CacheType.LOCATION_DATA, 
                           CacheType.USER_SETTINGS, CacheType.HOLIDAYS_BIRTHDAYS, CacheType.CONVERSATION_SESSION]:
                # Get context directly from local cache to avoid recursion
                if user_key in self.gemini_caches and ctx_type in self.gemini_caches[user_key]:
                    cache_entry = self.gemini_caches[user_key][ctx_type]
                    
                    # Extract context from cache entry structure
                    if isinstance(cache_entry, dict) and "context" in cache_entry:
                        ctx_content = cache_entry["context"]
                    else:
                        ctx_content = cache_entry
                    
                    # Handle both dictionary and string contexts
                    if isinstance(ctx_content, dict):
                        # For USER_PROFILE cache, properly format the dictionary
                        if ctx_type == CacheType.USER_PROFILE:
                            formatted_content = ""
                            if "user_info" in ctx_content:
                                formatted_content += f"User Info: {ctx_content['user_info']}\n"
                            if "user_current" in ctx_content:
                                formatted_content += f"Current State: {ctx_content['user_current']}\n"
                            all_contexts[ctx_type] = formatted_content.strip()
                        else:
                            # For other dictionary contexts, convert to readable format
                            import json
                            all_contexts[ctx_type] = json.dumps(ctx_content, indent=2)
                    elif isinstance(ctx_content, str) and not ctx_content.startswith("cachedContents/"):
                        all_contexts[ctx_type] = ctx_content
            
            # Combine contexts into a single larger content block
            if all_contexts:
                # Start with system instruction for Bravo
                combined_content = """You are Bravo, an AI communication assistant designed for AAC (Augmentative and Alternative Communication) users. You help users communicate by providing relevant response options based on their context, relationships, location, activities, and conversation history.

Your role is to:
- Generate 3-7 contextually appropriate response options
- Consider the user's current mood, location, people present, and recent activities
- Take into account relationships with friends and family
- Be aware of upcoming events, birthdays, and holidays
- Reference recent conversations and diary entries when relevant
- Format responses as a JSON array with "option" and "summary" keys

Context Information:
"""
                
                for ctx_type, ctx_content in all_contexts.items():
                    combined_content += f"\n## {ctx_type.replace('_', ' ').title()}\n{ctx_content}\n"
                
                logging.info(f"DEBUG: Combined content length: {len(combined_content)} chars, {len(all_contexts)} context types")
                
                # Only create cache if combined content is large enough (lowered threshold)
                estimated_tokens = len(combined_content) // 4
                if estimated_tokens >= 512:  # Lowered from 2048 to 512 tokens
                    cache_name = f"{user_key}_COMBINED_{int(dt.now().timestamp())}"
                    
                    # Create cached content with Gemini
                    gemini_cache_name = await self.create_gemini_cached_content(
                        cache_name=cache_name,
                        content=combined_content,
                        ttl_hours=1  # 1 hour TTL for combined cache
                    )
                    
                    if gemini_cache_name:
                        # Initialize user cache if needed
                        if user_key not in self.gemini_caches:
                            self.gemini_caches[user_key] = {}
                        if user_key not in self.cache_refresh_times:
                            self.cache_refresh_times[user_key] = {}
                        
                        # Store Gemini cache reference for COMBINED cache
                        self.gemini_caches[user_key]["COMBINED"] = {
                            "gemini_cache_name": gemini_cache_name,
                            "created_at": dt.now().timestamp(),
                            "ttl": 3600,  # 1 hour
                            "content_preview": f"Combined contexts ({len(all_contexts)} types, {estimated_tokens} est. tokens)"
                        }
                        
                        # Update refresh time
                        self.cache_refresh_times[user_key]["COMBINED"] = dt.now().timestamp()
                        
                        logging.info(f"Created combined Gemini cache for {account_id}/{aac_user_id}: {gemini_cache_name}")
                        return True
                    else:
                        logging.warning(f"Failed to create Gemini cached content for {account_id}/{aac_user_id}")
                        return False
                else:
                    logging.info(f"Combined content too small for caching: {estimated_tokens} tokens < 512 minimum for {account_id}/{aac_user_id}")
                    return False
            else:
                logging.info(f"No contexts available for combined cache creation for {account_id}/{aac_user_id}")
                return False
            
            return False
            
        except Exception as e:
            logging.error(f"Error storing Gemini cached context {cache_type} for {account_id}/{aac_user_id}: {e}")
            return False
            
        except Exception as e:
            logging.error(f"Error storing context in Gemini cache for {account_id}/{aac_user_id}/{cache_type}: {e}")
            return False

    async def get_cached_context(self, account_id: str, aac_user_id: str, cache_type: str) -> Optional[str]:
        """Retrieve cached context - updated to work with Gemini caching"""
        if not await self.is_cache_valid(account_id, aac_user_id, cache_type):
            return None
            
        user_key = self._get_user_key(account_id, aac_user_id)
        cache_info = self.gemini_caches.get(user_key, {}).get(cache_type)
        
        if not cache_info:
            return None
            
        try:
            # If we have a Gemini cache name, return it for use in generation
            if "gemini_cache_name" in cache_info:
                gemini_cache_name = cache_info["gemini_cache_name"]
                # Verify cache still exists in Gemini
                if await self.get_gemini_cached_content(gemini_cache_name):
                    return gemini_cache_name  # Return cache reference for use in generation
                else:
                    # Cache expired in Gemini, remove local reference
                    del self.gemini_caches[user_key][cache_type]
                    return None
            
            # Fallback to local cache
            return cache_info.get("context")
            
        except Exception as e:
            logging.error(f"Error retrieving cached context for {user_key}/{cache_type}: {e}")
            return None
    
    async def get_or_create_conversation_session(self, account_id: str, aac_user_id: str):
        """Get existing conversation session or create new one with cached context"""
        user_key = self._get_user_key(account_id, aac_user_id)
        
        # Check if session exists and is valid
        if user_key in self.conversation_sessions:
            session_info = self.conversation_sessions[user_key]
            session_age = dt.now().timestamp() - session_info.get("created_at", 0)
            
            if session_age < self.cache_ttl[CacheType.CONVERSATION_SESSION]:
                return session_info.get("session")
        
        # Create new session with cached static context
        try:
            # Build static context using cached content references
            cached_content_refs = await self.build_cached_context_references(account_id, aac_user_id)
            
            # Create actual Gemini chat session with cached content
            if cached_content_refs:
                # Use cached content for session creation
                model = genai.GenerativeModel(
                    model_name=GEMINI_PRIMARY_MODEL.replace("models/", ""),
                    cached_content=cached_content_refs[0] if cached_content_refs else None
                )
                chat_session = model.start_chat()
                
                session_info = {
                    "chat_session": chat_session,
                    "model": model,
                    "cached_content_refs": cached_content_refs,
                    "created_at": dt.now().timestamp(),
                    "message_count": 0
                }
                
                self.conversation_sessions[user_key] = session_info
                logging.info(f"Created Gemini chat session for {user_key} with {len(cached_content_refs)} cached content refs")
                
                return chat_session
            else:
                # Fallback: create session without cached content
                model = genai.GenerativeModel(GEMINI_PRIMARY_MODEL.replace("models/", ""))
                chat_session = model.start_chat()
                
                session_info = {
                    "chat_session": chat_session,
                    "model": model,
                    "cached_content_refs": [],
                    "created_at": dt.now().timestamp(),
                    "message_count": 0
                }
                
                self.conversation_sessions[user_key] = session_info
                logging.info(f"Created Gemini chat session for {user_key} without cached content")
                
                return chat_session
            
        except Exception as e:
            logging.error(f"Error creating Gemini chat session for {account_id}/{aac_user_id}: {e}")
            return None
    
    async def build_cached_context_references(self, account_id: str, aac_user_id: str) -> List[str]:
        """Build list of Gemini cached content references for session creation"""
        user_key = self._get_user_key(account_id, aac_user_id)
        cached_refs = []
        
        # First check for combined cache (new batched approach)
        if user_key in self.gemini_caches and "COMBINED" in self.gemini_caches[user_key]:
            combined_cache = self.gemini_caches[user_key]["COMBINED"]
            
            # Check if cache is still valid
            cache_age = dt.now().timestamp() - combined_cache.get("created_at", 0)
            if cache_age < combined_cache.get("ttl", 3600):
                cached_refs.append(combined_cache["gemini_cache_name"])
                logging.info(f"Using combined Gemini cache for {account_id}/{aac_user_id}")
                return cached_refs
        
        # Fallback: Try to get individual cached content references (legacy)
        for cache_type in [CacheType.USER_PROFILE, CacheType.FRIENDS_FAMILY, 
                          CacheType.LOCATION_DATA, CacheType.USER_SETTINGS, 
                          CacheType.HOLIDAYS_BIRTHDAYS]:
            
            cached_ref = await self.get_cached_context(account_id, aac_user_id, cache_type)
            if cached_ref and cached_ref.startswith("cachedContents/"):  # Gemini cache reference
                cached_refs.append(cached_ref)
        
        return cached_refs
    
    async def build_static_context(self, account_id: str, aac_user_id: str) -> str:
        """Build static context from cached components"""
        context_parts = []
        
        # Try to get cached contexts, build if missing
        for cache_type in [CacheType.USER_PROFILE, CacheType.FRIENDS_FAMILY, 
                          CacheType.LOCATION_DATA, CacheType.USER_SETTINGS, 
                          CacheType.HOLIDAYS_BIRTHDAYS]:
            
            cached_context = await self.get_cached_context(account_id, aac_user_id, cache_type)
            if cached_context:
                context_parts.append(cached_context)
            else:
                # Cache miss - would need to rebuild this context
                logging.info(f"Cache miss for {cache_type}, would need to rebuild")
        
        return "\n\n".join(context_parts)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring"""
        total_users = len(self.gemini_caches)
        total_caches = sum(len(caches) for caches in self.gemini_caches.values())
        
        cache_types_count = {}
        for user_caches in self.gemini_caches.values():
            for cache_type in user_caches.keys():
                cache_types_count[cache_type] = cache_types_count.get(cache_type, 0) + 1
        
        return {
            "total_users": total_users,
            "total_caches": total_caches,
            "cache_types": cache_types_count,
            "active_sessions": len(self.conversation_sessions)
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



@app.post("/api/user-data/delete-aac-user-profile") # Renamed endpoint for clarity
async def delete_aac_user_profile_endpoint(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    account_id = current_ids["account_id"]
    aac_user_id = current_ids["aac_user_id"]

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
                # Calculate token savings
                full_prompt_tokens = len(prompt_text.split())  # Rough estimate
                user_query_tokens = len(user_query_only.split())  # Rough estimate
                token_savings = full_prompt_tokens - user_query_tokens
                token_savings_percent = (token_savings / full_prompt_tokens) * 100 if full_prompt_tokens > 0 else 0
                
                logging.info(f"TOKEN SAVINGS: Using chat session with cached content for {account_id}/{aac_user_id}")
                logging.info(f"TOKEN SAVINGS: Full context would be ~{full_prompt_tokens} tokens, sending only ~{user_query_tokens} tokens")
                logging.info(f"TOKEN SAVINGS: Estimated savings: ~{token_savings} tokens ({token_savings_percent:.1f}% reduction)")
                
                # Send only the user query - context is cached in the session
                response = await asyncio.to_thread(chat_session.send_message, user_query_only)
            else:
                # Fallback: send full prompt if no user_query_only provided
                logging.info(f"No user_query_only provided, sending full prompt to chat session for {account_id}/{aac_user_id}")
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
                    # Get the first cached content reference
                    cached_content = caching.CachedContent.get(cached_refs[0])
                    model = genai.GenerativeModel(
                        model_name=GEMINI_PRIMARY_MODEL.replace("models/", ""),
                        cached_content=cached_content
                    )
                    
                    # Calculate token savings
                    full_prompt_tokens = len(prompt_text.split())  # Rough estimate
                    user_query_tokens = len(user_query_only.split())  # Rough estimate
                    token_savings = full_prompt_tokens - user_query_tokens
                    token_savings_percent = (token_savings / full_prompt_tokens) * 100 if full_prompt_tokens > 0 else 0
                    
                    logging.info(f"TOKEN SAVINGS: Using cached content for {account_id}/{aac_user_id}")
                    logging.info(f"TOKEN SAVINGS: Full context would be ~{full_prompt_tokens} tokens, sending only ~{user_query_tokens} tokens")
                    logging.info(f"TOKEN SAVINGS: Estimated savings: ~{token_savings} tokens ({token_savings_percent:.1f}% reduction)")
                    
                    # Only send the user query - the context is already cached on Gemini's servers
                    response = await asyncio.to_thread(model.generate_content, user_query_only, generation_config=generation_config)
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
async def _generate_gemini_content_with_fallback(prompt_text: str, generation_config: Optional[Dict] = None) -> str: # <--- THIS LINE IS CRITICAL
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
        logging.info(f"Attempting LLM generation with primary model: {primary_llm_model_instance.model_name}")
        response = await asyncio.to_thread(primary_llm_model_instance.generate_content, prompt_text, generation_config=generation_config) # <--- THIS CALL
        return (await get_text_from_response(response)).strip()
    except (google.api_core.exceptions.ResourceExhausted, google.api_core.exceptions.ServiceUnavailable) as e_primary:
        logging.warning(f"Primary LLM ({primary_llm_model_instance.model_name}) failed with {type(e_primary).__name__}: {e_primary}. Attempting fallback.")
        if fallback_llm_model_instance:
            try:
                logging.info(f"Attempting LLM generation with fallback model: {fallback_llm_model_instance.model_name}")
                response_fallback = await asyncio.to_thread(fallback_llm_model_instance.generate_content, prompt_text, generation_config=generation_config) # <--- THIS CALL
                return (await get_text_from_response(response_fallback)).strip()
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


@app.get("/api/cache/stats")
async def get_cache_stats(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """Get cache statistics for the current user"""
    cache_manager = GeminiCacheManager()
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    
    stats = cache_manager.get_cache_stats(account_id, aac_user_id)
    return JSONResponse(content=stats)


@app.post("/api/cache/refresh")
async def refresh_user_cache(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    """Manually refresh all cache entries for the current user"""
    cache_manager = GeminiCacheManager()
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    
    # Clear all cache entries for this user
    cache_types = ["USER_PROFILE", "LOCATION_DATA", "FRIENDS_FAMILY", "USER_SETTINGS", 
                  "HOLIDAYS_BIRTHDAYS", "RAG_CONTEXT", "CONVERSATION_SESSION"]
    
    cleared_count = 0
    for cache_type in cache_types:
        if cache_manager.invalidate_cache(account_id, aac_user_id, cache_type):
            cleared_count += 1
    
    logging.info(f"Manual cache refresh: Cleared {cleared_count} cache entries for account {account_id} and user {aac_user_id}")
    
    return JSONResponse(content={
        "message": f"Cache refreshed for user {aac_user_id}",
        "cleared_entries": cleared_count,
        "cache_types": cache_types
    })


# --- LLM Endpoint (MODIFIED RAG Context Processing for user-specificity) ---
@app.post("/llm")

async def get_llm_response_endpoint(request: Request, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    
    global sentence_transformer_model, primary_llm_model_instance, fallback_llm_model_instance, CONTEXT_N_RESULTS

    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    # Check if LLM is initialized (sentence transformer is optional since we're not using RAG)
    if not primary_llm_model_instance:
        logging.error("LLM endpoint: Primary LLM model not initialized.")
        raise HTTPException(status_code=503, detail="Backend LLM service unavailable.")

    # Log request headers for debugging
    logging.info(f"/llm endpoint request headers: {dict(request.headers)}")

    try: 
        data = await request.json()
        user_prompt_content = data.get("prompt")
    except Exception as e: 
        logging.error(f"Error parsing request JSON for account {account_id} and user {aac_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid request body.")

    if not user_prompt_content: raise HTTPException(status_code=400, detail="Missing 'prompt'.")
    logging.info(f"LLM request received for account {account_id} and user {aac_user_id}. Prompt length: {len(user_prompt_content)}")

    # Load user settings to get LLMOptions value for placeholder replacement
    user_settings = await load_settings_from_file(account_id, aac_user_id)
    llm_options_value = user_settings.get("LLMOptions", DEFAULT_LLM_OPTIONS)
    current_mood = user_settings.get("currentMood")  # Get current mood from settings
    
    # Replace #LLMOptions placeholder in the prompt
    if "#LLMOptions" in user_prompt_content:
        original_prompt = user_prompt_content
        user_prompt_content = user_prompt_content.replace("#LLMOptions", str(llm_options_value))
        logging.info(f"Replaced #LLMOptions in prompt: '{original_prompt}' -> '{user_prompt_content}'")
    else:
        logging.info(f"No #LLMOptions placeholder found in prompt: '{user_prompt_content[:100]}...'")

    current_date = date.today(); current_date_str = current_date.isoformat()

    # --- Initialize Cache Manager ---
    cache_manager = GeminiCacheManager()
    
    # --- OPTIMIZED: Try to get context from cache first ---
    cached_user_profile = await cache_manager.get_cached_context(account_id, aac_user_id, "USER_PROFILE")
    cached_location_data = await cache_manager.get_cached_context(account_id, aac_user_id, "LOCATION_DATA")
    cached_friends_family = await cache_manager.get_cached_context(account_id, aac_user_id, "FRIENDS_FAMILY")
    cached_user_settings = await cache_manager.get_cached_context(account_id, aac_user_id, "USER_SETTINGS")
    cached_holidays_birthdays = await cache_manager.get_cached_context(account_id, aac_user_id, "HOLIDAYS_BIRTHDAYS")
    cached_rag_context = await cache_manager.get_cached_context(account_id, aac_user_id, "RAG_CONTEXT")
    cached_button_activity = await cache_manager.get_cached_context(account_id, aac_user_id, "BUTTON_ACTIVITY")

    # --- AWAIT all Firestore data loading calls (only if not cached) ---
    if cached_holidays_birthdays:
        logging.info(f"Using cached holidays/birthdays for account {account_id} and user {aac_user_id}")
        upcoming_holidays_list = cached_holidays_birthdays.get("holidays", [])
        upcoming_birthdays_list = cached_holidays_birthdays.get("birthdays", [])
    else:
        logging.info(f"Loading fresh holidays/birthdays for account {account_id} and user {aac_user_id}")
        upcoming_holidays_list = await get_upcoming_holidays_and_observances(account_id, aac_user_id, days_ahead=14)
        upcoming_birthdays_list = await get_upcoming_birthdays(account_id, aac_user_id, days_ahead=14)
        # Cache the results
        await cache_manager.store_cached_context(account_id, aac_user_id, "HOLIDAYS_BIRTHDAYS", {
            "holidays": upcoming_holidays_list,
            "birthdays": upcoming_birthdays_list
        })

    # Load diary entries (always fresh due to frequent updates)
    diary_entries = await load_diary_entries(account_id, aac_user_id)
    
    if cached_friends_family:
        logging.info(f"Using cached friends/family for account {account_id} and user {aac_user_id}")
        friends_family_data = cached_friends_family
    else:
        logging.info(f"Loading fresh friends/family for account {account_id} and user {aac_user_id}")
        friends_family_data = await load_friends_family_from_file(account_id, aac_user_id)
        await cache_manager.store_cached_context(account_id, aac_user_id, "FRIENDS_FAMILY", friends_family_data)

    chroma_context_str = cached_rag_context or ""
    generation_config = {
        "response_mime_type": "application/json", # CRITICAL: Force JSON output
        "temperature": 0.7, # Adjust as needed
        # "top_p": 1,        # You can add these
        # "top_k": 1         # as needed
    }

    past_diary_context = []; future_diary_context = []
    for entry in diary_entries:
        try:
            # Ensure entry is a dictionary before accessing 'date' or 'entry'
            if not isinstance(entry, dict): 
                logging.warning(f"Skipping non-dictionary diary entry for account {account_id} and user {aac_user_id}: {entry!r}")
                continue
            entry_date = date.fromisoformat(entry.get('date','')); entry_text = entry.get('entry', '')
            if not entry_text: continue
            if entry_date <= current_date and len(past_diary_context) < MAX_DIARY_CONTEXT:
                days_ago = (current_date - entry_date).days; relative_day = f" ({days_ago} days ago)" if days_ago > 1 else (" (Yesterday)" if days_ago == 1 else " (Today)")
                past_diary_context.append(f"Date: {entry['date']}{relative_day}\nEntry: {entry_text}")
            elif entry_date > current_date :
                days_ahead_entry = (entry_date - current_date).days
                relative_day = f" (in {days_ahead_entry} days)" if days_ahead_entry > 1 else (" (Tomorrow!)" if days_ahead_entry == 1 else " (Today - planned)")
                future_diary_context.append({'date_obj': entry_date, 'text': f"Date: {entry['date']}{relative_day}\nEntry: {entry_text}"})
        except Exception: # Catch any error during processing, log and skip
            logging.warning(f"Error processing diary entry for account {account_id} and user {aac_user_id}: {entry!r}", exc_info=True)

    future_diary_context.sort(key=lambda x: x['date_obj']); 
    future_diary_context = [item['text'] for item in future_diary_context[:MAX_DIARY_CONTEXT]]

    # --- OPTIMIZED: Use cached conversation session if available ---
    cached_conversation = await cache_manager.get_cached_context(account_id, aac_user_id, "CONVERSATION_SESSION")
    if cached_conversation and len(cached_conversation.get("chat_history", [])) >= len(chat_history):
        logging.info(f"Using cached conversation session for account {account_id} and user {aac_user_id}")
        recent_chat_context = cached_conversation.get("recent_context", [])
    else:
        logging.info(f"Building fresh conversation context for account {account_id} and user {aac_user_id}")
        chat_history = await load_chat_history(account_id, aac_user_id)

        recent_chat_context = []
        for chat in reversed(chat_history[-MAX_CHAT_CONTEXT:]):
            # Ensure 'chat' is a dictionary before using .get()
            if not isinstance(chat, dict):
                logging.warning(f"Skipping non-dictionary chat item for account {account_id} and user {aac_user_id}: {chat!r}")
                continue
            q = chat.get('question', '').strip().replace('Q: ', '').strip("' "); 
            r = chat.get('response', '').strip().replace('A: ', '').strip("' ")
            if q and r: recent_chat_context.append(f"Previous Turn: Q: {q} / A: {r}")
        
        # Cache the conversation session
        await cache_manager.store_cached_context(account_id, aac_user_id, "CONVERSATION_SESSION", {
            "chat_history": chat_history,
            "recent_context": recent_chat_context
        })

    # --- OPTIMIZED: Use cached user info if available ---
    if cached_user_profile:
        logging.info(f"Using cached user profile for account {account_id} and user {aac_user_id}")
        user_info_content = cached_user_profile.get("user_info", "")
        user_current_content = cached_user_profile.get("user_current", "")
    else:
        logging.info(f"Loading fresh user profile for account {account_id} and user {aac_user_id}")
        # User Info Content
        user_info_content_dict = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/user_narrative",
            default_data=DEFAULT_USER_INFO.copy()
        )
        user_info_content = user_info_content_dict.get("narrative", "").strip()

        # User Current Content
        user_current_content_dict = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_state",
            default_data=DEFAULT_USER_CURRENT.copy()
        )
        user_current_content = (
            f"Location: {user_current_content_dict.get('location', '')}\n"
            f"People Present: {user_current_content_dict.get('people', '')}\n"
            f"Activity: {user_current_content_dict.get('activity', '')}"
        ).strip()
        
        # Cache the user profile data
        await cache_manager.store_cached_context(account_id, aac_user_id, "USER_PROFILE", {
            "user_info": user_info_content,
            "user_current": user_current_content
        })

    # --- Context Assembly (RAG disabled) ---
    logging.info(f"DEBUG LLM Context: RAG functionality disabled (sentence transformer not available)")

    context_parts = []

    # Add basic info
    context_parts.insert(0, f"Current Date: {current_date_str}")
    
    # Add mood context if available
    if current_mood:
        mood_context = f"User's Current Mood: {current_mood} - Please tailor responses to be appropriate for someone feeling {current_mood.lower()}."
        context_parts.append(mood_context)
        logging.info(f"Added mood context to LLM prompt: {mood_context}")
    
    if user_info_content.strip(): # Only add if not empty after strip
        context_parts.append(f"General User Information:\n{user_info_content}")
    if user_current_content.strip(): # Only add if not empty after strip
        context_parts.append(f"User's Current State:\n{user_current_content}")

    # Add friends and family context
    friends_family_list = friends_family_data.get('friends_family', [])
    logging.info(f"DEBUG friends_family: Raw data loaded for account {account_id} and user {aac_user_id}: {friends_family_data}")
    logging.info(f"DEBUG friends_family: Extracted list length: {len(friends_family_list)} items")
    
    if friends_family_list:
        friends_family_entries = []
        for i, person in enumerate(friends_family_list):
            logging.info(f"DEBUG friends_family: Processing person {i}: {person}")
            if isinstance(person, dict):
                name = person.get('name', 'Unknown')
                relationship = person.get('relationship', 'Unknown')
                details = person.get('details', '')
                entry = f"{name} ({relationship})"
                if details.strip():
                    entry += f": {details}"
                friends_family_entries.append(entry)
                logging.info(f"DEBUG friends_family: Added entry {i}: {entry}")
        
        if friends_family_entries:
            friends_family_context = f"Friends & Family:\n" + "\n".join(friends_family_entries)
            context_parts.append(friends_family_context)
            logging.info(f"DEBUG friends_family: Final context added (length {len(friends_family_context)} chars): {friends_family_context}")
        else:
            logging.info(f"DEBUG friends_family: No valid entries found after processing")
    else:
        logging.info(f"DEBUG friends_family: No friends_family list found or list is empty")

    # --- OPTIMIZED: Load recent button activity for context ---
    if cached_button_activity:
        logging.info(f"Using cached button activity for account {account_id} and user {aac_user_id}")
        recent_button_activity = cached_button_activity.get("recent_activity", [])
    else:
        logging.info(f"Loading fresh button activity for account {account_id} and user {aac_user_id}")
        try:
            # Load button activity log from last 7 days
            from datetime import datetime, timedelta, timezone
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            
            button_activity_log = await load_button_activity_log(account_id, aac_user_id)
            recent_button_activity = []
            
            logging.info(f"Found {len(button_activity_log)} total button activity entries for account {account_id} and user {aac_user_id}")
            
            # Filter for recent activity and organize by page/category
            activity_by_page = {}
            filtered_count = 0
            for entry in button_activity_log:
                if isinstance(entry, dict):
                    timestamp_str = entry.get('timestamp', '')
                    try:
                        # Parse timestamp (assuming ISO format)
                        if timestamp_str:
                            entry_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if entry_time >= seven_days_ago:
                                filtered_count += 1
                                page_name = entry.get('page_name', 'Unknown')
                                button_text = entry.get('button_text', 'Unknown')
                                
                                if page_name not in activity_by_page:
                                    activity_by_page[page_name] = []
                                activity_by_page[page_name].append(button_text)
                    except (ValueError, TypeError) as e:
                        logging.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
                        continue
            
            logging.info(f"After filtering for last 7 days: {filtered_count} entries from {len(button_activity_log)} total")
            
            # Convert to structured format for context
            for page_name, buttons in activity_by_page.items():
                # Get unique buttons (remove duplicates but keep order)
                unique_buttons = []
                seen = set()
                for button in reversed(buttons):  # Most recent first
                    if button not in seen:
                        unique_buttons.append(button)
                        seen.add(button)
                
                if unique_buttons:
                    recent_button_activity.append({
                        'page': page_name,
                        'buttons': unique_buttons[:10]  # Limit to 10 most recent per page
                    })
            
            logging.info(f"After deduplication: {len(recent_button_activity)} pages with activity")
            for page_activity in recent_button_activity:
                logging.info(f"  Page '{page_activity['page']}': {len(page_activity['buttons'])} unique buttons")
            
            # Cache the results
            await cache_manager.store_cached_context(account_id, aac_user_id, "BUTTON_ACTIVITY", {
                "recent_activity": recent_button_activity
            })
            
        except Exception as e:
            logging.error(f"Error loading button activity for account {account_id} and user {aac_user_id}: {e}", exc_info=True)
            recent_button_activity = []

    # Add recent button activity context
    if recent_button_activity:
        activity_lines = []
        for page_activity in recent_button_activity:
            page_name = page_activity.get('page', 'Unknown')
            buttons = page_activity.get('buttons', [])
            if buttons:
                # Format: "Page: button1, button2, button3"
                button_list = ", ".join(buttons[:5])  # Show up to 5 per page in context
                activity_lines.append(f"{page_name}: {button_list}")
        
        if activity_lines:
            button_activity_context = f"Recently Used Options (last 7 days - avoid repeating these):\n" + "\n".join(activity_lines)
            context_parts.append(button_activity_context)
            logging.info(f"Added button activity context: {len(activity_lines)} pages with recent activity")
    else:
        logging.info(f"No recent button activity found for account {account_id} and user {aac_user_id}")

    # Add holidays, birthdays, diary, chat history contexts
    if upcoming_holidays_list and upcoming_holidays_list[0] != f"No major holidays or observances found in the next {14} days for {DEFAULT_COUNTRY_CODE}.":
        context_parts.append(f"Upcoming Holidays/Observances (approx. next 2 weeks):\n" + "\n".join(upcoming_holidays_list))

    if upcoming_birthdays_list and upcoming_birthdays_list[0] != f"No birthdays found in the next {14} days.":
        # Birthday context might include user's age as first line
        # Check if it's just the "User's age" line, and skip "Upcoming Birthdays:" header
        is_just_user_age = (len(upcoming_birthdays_list) == 1 and upcoming_birthdays_list[0].startswith("User's current age:"))
        if is_just_user_age:
            context_parts.append(upcoming_birthdays_list[0])
        else:
            # All other cases mean there are actual upcoming birthdays (or an error message)
            context_parts.append(f"Birthday Info & Upcoming Birthdays (approx. next 2 weeks):\n" + "\n".join(upcoming_birthdays_list))

    if past_diary_context: context_parts.append(f"Recent Diary Entries (most recent first, max {MAX_DIARY_CONTEXT}):\n---\n" + "\n---\n".join(past_diary_context))
    if future_diary_context: context_parts.append(f"Upcoming Diary Plans (soonest first, max {MAX_DIARY_CONTEXT}):\n---\n" + "\n---\n".join(future_diary_context))
    if recent_chat_context: context_parts.append(f"Recent Conversation History (most recent first, max {MAX_CHAT_CONTEXT}):\n" + "\n".join(recent_chat_context))

    # Add RAG context if available
    if chroma_context_str:
        context_parts.append(f"Additional Context (from RAG):\n{chroma_context_str}")

    # Final LLM Prompt construction
    logging.info(f"LLM Final Context Parts (before join): {len(context_parts)} parts.")
    for i, part in enumerate(context_parts):
        part_preview = part[:100].replace('\n', '\\n') if part else 'EMPTY'
        logging.info(f"DEBUG context_parts[{i}]: {part_preview}...")
    
    final_llm_prompt = "\n\n".join(c.strip() for c in context_parts if c.strip()) + f"\n\nUser Request (follow instructions carefully):\n{user_prompt_content}"

    if not final_llm_prompt.strip():
        logging.warning(f"Final LLM Prompt is empty after stripping for account {account_id} and user {aac_user_id}. Returning empty response.")
        raise HTTPException(status_code=500, detail="LLM Prompt could not be generated.")

    # Log a more detailed preview of the final prompt
    prompt_preview = final_llm_prompt[:1000].replace('\n', '\\n')
    logging.info(f"DEBUG Final LLM Prompt preview (first 1000 chars): {prompt_preview}...")
    print(f'Final LLM Prompt for account {account_id} and user {aac_user_id}:\n{final_llm_prompt[:500]}...') # Print first 500 chars
    logging.info(f"--- Sending Prompt to LLM for account {account_id} and user {aac_user_id} (Length: {len(final_llm_prompt)}) ---")

    # --- PERFORMANCE: Log cache effectiveness ---
    cache_hits = sum([
        1 for cache in [cached_user_profile, cached_location_data, cached_friends_family, 
                       cached_user_settings, cached_holidays_birthdays, cached_rag_context, cached_conversation]
        if cache is not None
    ])
    total_cache_types = 7
    cache_hit_rate = (cache_hits / total_cache_types) * 100
    logging.info(f"PERFORMANCE: Cache hit rate: {cache_hit_rate:.1f}% ({cache_hits}/{total_cache_types}) for account {account_id} and user {aac_user_id}")
    
    # Estimate performance improvement
    if cache_hit_rate > 0:
        estimated_speedup = 1 + (cache_hit_rate / 100) * 0.9  # Up to 90% improvement
        logging.info(f"PERFORMANCE: Estimated speedup: {estimated_speedup:.2f}x with {cache_hit_rate:.1f}% cache hit rate")

    # Get user's LLM provider preference
    llm_provider = user_settings.get("llm_provider", "gemini").lower()
    logging.info(f"Using LLM provider: {llm_provider} for account {account_id} and user {aac_user_id}")

    # Add JSON format instructions for both OpenAI and Gemini
    json_format_instructions = """

CRITICAL: Format your response as a JSON list where each item has "option" and "summary" keys.
If the generated option is more than 5 words, the "summary" key should be a 3-5 word abbreviation of each option, including the exact key words from the option. If the option is 5 words or less, the "summary" key should contain the exact same FULL text as the "option" key.
The "option" key should contain the FULL option text.

IMPORTANT FOR JOKES: If generating jokes, ALWAYS include both the question AND punchline in the SAME "option". Format them as: "Question? Punchline!" with just a question mark between the question and punchline. DO NOT split jokes into separate options.

Example: [{"option": "Hello there, how are you doing today?", "summary": "Hello how are you"}, {"option": "Goodbye!", "summary": "Goodbye!"}]
Joke Example: [{"option": "Why don't scientists trust atoms? Because they make up everything!", "summary": "scientists trust atoms"}]

Return ONLY valid JSON - no other text before or after the JSON array."""
    
    final_llm_prompt += json_format_instructions
    logging.info(f"Added JSON format instructions for {llm_provider} (length: {len(json_format_instructions)})")

    # Route to appropriate LLM based on user preference
    if llm_provider == "chatgpt":
        llm_response_json_str = await _generate_openai_content_with_fallback(final_llm_prompt)
    else:  # Default to Gemini for "gemini" or any unrecognized value
        # Prepare user query with JSON format instructions for cached content
        user_query_with_instructions = f"User Request (follow instructions carefully):\n{user_prompt_content}{json_format_instructions}"
        
        # Use cached generation for significant performance and cost improvements
        llm_response_json_str = await _generate_gemini_content_with_caching(
            account_id, aac_user_id, final_llm_prompt, 
            generation_config=generation_config, 
            cache_manager=cache_manager,
            user_query_only=user_query_with_instructions
        )
    logging.info(f"--- LLM Final JSON Response Text for account {account_id} and user {aac_user_id} (Length: {len(llm_response_json_str)}) ---")

    def extract_json_from_response(response_text: str) -> str:
        """Extract JSON from LLM response, handling markdown code blocks"""
        # Remove any leading/trailing whitespace
        response_text = response_text.strip()
        
        # Check if response is wrapped in markdown code blocks
        if response_text.startswith('```json') and response_text.endswith('```'):
            # Extract content between ```json and ```
            lines = response_text.split('\n')
            json_lines = []
            in_json_block = False
            
            for line in lines:
                if line.strip().startswith('```json'):
                    in_json_block = True
                    continue
                elif line.strip() == '```' and in_json_block:
                    break
                elif in_json_block:
                    json_lines.append(line)
            
            return '\n'.join(json_lines).strip()
        
        # Check for other markdown variations
        elif response_text.startswith('```') and response_text.endswith('```'):
            # Extract content between ``` blocks (without json specifier)
            lines = response_text.split('\n')
            if len(lines) >= 3:
                return '\n'.join(lines[1:-1]).strip()
        
        # If no markdown blocks, return as-is
        return response_text

    # Extract clean JSON from the response
    clean_json_str = extract_json_from_response(llm_response_json_str)
    logging.info(f"--- Extracted clean JSON for account {account_id} and user {aac_user_id} (Original length: {len(llm_response_json_str)}, Clean length: {len(clean_json_str)}) ---")

    try:
        parsed_llm_output = json.loads(clean_json_str)
        logging.info(f"--- Parsed LLM JSON Output for account {account_id} and user {aac_user_id} ---")

        # --- CRITICAL FIX: Robust extraction of the options list ---
        # Initialize extracted_options_list before any conditions
        extracted_options_list = []

        if isinstance(parsed_llm_output, dict):
            # Try to find a list within the dictionary. Common keys can be hardcoded or iterate values.
            # Since you've seen "greetings_goodbyes_starters" specifically, we can target it.
            # However, the general robust way is to find *any* list value.
            for key, value in parsed_llm_output.items():
                if isinstance(value, list):
                    extracted_options_list = value
                    logging.info(f"Extracted list from LLM response dictionary using key: '{key}'")
                    break # Take the first list we find

            if not extracted_options_list: # If no list found after iterating through dict values
                logging.warning(f"LLM returned a dictionary but no inner list of options found: {parsed_llm_output.keys()}")
                raise HTTPException(status_code=500, detail="LLM response was a dictionary but contained no list of options.")

        elif isinstance(parsed_llm_output, list):
            extracted_options_list = parsed_llm_output # Directly use the list if it's already a list
        else:
            # Top-level is not a dict or a list, which is unexpected
            logging.error(f"LLM returned unexpected top-level type: {type(parsed_llm_output)} - Content: {llm_response_json_str}")
            raise HTTPException(status_code=500, detail="LLM response was not valid (not a list or a dict containing a list).")

        # Final validation: Ensure that what we extracted is actually a list
        # This check will now reliably catch if the above logic failed to set it to a list.
        if not isinstance(extracted_options_list, list): # This line is 921 based on previous errors
            logging.error(f"Logic Error: After processing, extracted LLM options were not a list: {type(extracted_options_list)} - Content: {llm_response_json_str}")
            raise HTTPException(status_code=500, detail="Internal server error: Failed to extract LLM options as a list.")

        # Return the parsed Python list, which FastAPI will convert to JSON response.
        return JSONResponse(content=extracted_options_list)

    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse LLM response as JSON: {e}. Original Raw: {llm_response_json_str[:500]}... Clean Raw: {clean_json_str[:500]}...", exc_info=True)
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
        await cache_manager.invalidate_by_endpoint(account_id, aac_user_id, "/update-user-info")
    
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
        await cache_manager.invalidate_by_endpoint(account_id, aac_user_id, "/update-user-favorites")
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
            await cache_manager.invalidate_by_endpoint(account_id, aac_user_id, "/api/favorites")
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
    LLMOptions: Optional[int] = Field(None, description="Number of options returned by LLM (e.g., 1-50)", gt=1, lt=50) 
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
    currentMood: Optional[str] = Field(None, description="Currently selected mood for the session.", max_length=50)
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
    # Load current settings first to merge and retain unspecified fields
    current_settings = await load_settings_from_file(account_id, aac_user_id)
    # Remove any keys not defined in DEFAULT_SETTINGS before merging to avoid storing junk
    sanitized_data_to_save = {k: v for k, v in settings_data_to_save.items() if k in DEFAULT_SETTINGS}
    # Merge (update existing defaults with new sanitized data)
    current_settings.update(sanitized_data_to_save)

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

    update_data = settings_update.model_dump(exclude_unset=True)
    logging.info(f"POST /api/settings request received for account {account_id} and user {aac_user_id} with update data: {update_data}")
    # Await save_settings_to_file and check its boolean result
    success = await save_settings_to_file(account_id, aac_user_id, update_data)

    if success:
        # Await load_settings_from_file to get the actual dictionary
        saved_settings_dict = await load_settings_from_file(account_id, aac_user_id)
        
        # Update the RAG cache with new user settings
        try:
            await cache_manager.store_cached_context(
                account_id, 
                aac_user_id, 
                saved_settings_dict, 
                CacheType.USER_SETTINGS
            )
            logging.info(f"Updated USER_SETTINGS cache for user {aac_user_id}")
        except Exception as e:
            logging.error(f"Failed to update USER_SETTINGS cache: {e}")
        
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
        # Update HOLIDAYS_BIRTHDAYS cache with new data
        await cache_manager.store_cached_context(account_id, aac_user_id, "HOLIDAYS_BIRTHDAYS", data_to_save)
        logging.info(f"Updated HOLIDAYS_BIRTHDAYS cache for account {account_id} and user {aac_user_id}")
        
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
        # Update FRIENDS_FAMILY cache with new data
        await cache_manager.store_cached_context(account_id, aac_user_id, "FRIENDS_FAMILY", data_to_save)
        logging.info(f"Updated FRIENDS_FAMILY cache for account {account_id} and user {aac_user_id}")
        
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
    return JSONResponse(content={"userInfo": user_info_content_dict.get("narrative", "")})

@app.post("/api/user-info")
async def save_user_info_api(request: Dict, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    logging.info(f"POST /api/user-info request received for account {account_id} and user {aac_user_id}.")
    
    user_info = request.get("userInfo", "")
    success = await save_firestore_document(
        account_id=account_id,
        aac_user_id=aac_user_id,
        doc_subpath="info/user_narrative",
        data_to_save={"narrative": user_info}
    )
    
    if success:
        # Update USER_PROFILE cache with new user info
        from datetime import datetime, timezone
        
        # Get current user state to maintain complete cache structure
        user_current_content_dict = await load_firestore_document(
            account_id, aac_user_id, "current"
        )
        user_current_content = ""
        if user_current_content_dict:
            user_current_content = (
                f"Location: {user_current_content_dict.get('location', '')}\n"
                f"People Present: {user_current_content_dict.get('people', '')}\n"
                f"Activity: {user_current_content_dict.get('activity', '')}"
            ).strip()
        
        await cache_manager.store_cached_context(account_id, aac_user_id, "USER_PROFILE", {
            "user_info": user_info,
            "user_current": user_current_content,
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        logging.info(f"Updated USER_PROFILE cache for account {account_id} and user {aac_user_id}")
        
        return JSONResponse(content={"userInfo": user_info})
    else:
        raise HTTPException(status_code=500, detail="Failed to save user info.")


# /api/diary-entries
@app.get("/api/diary-entries", response_model=List[DiaryEntryOutput])
async def get_diary_entries_endpoint(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]): # ADD user_id
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    logging.info(f"GET /api/diary-entries request received for user {aac_user_id}.")
    raw_entries = await load_diary_entries(account_id, aac_user_id) 

    valid_entries = []
    for entry in raw_entries:
        # Explicitly check for required fields for a valid diary entry display
        if isinstance(entry, dict) and \
           isinstance(entry.get('date'), str) and \
           isinstance(entry.get('entry'), str) and \
           isinstance(entry.get('id'), str):
            valid_entries.append(entry)
        else:
            logging.warning(f"Skipping malformed diary entry during backend processing for user {aac_user_id}: {entry}")
            
    try:
        # Sort only the valid entries
        valid_entries.sort(key=lambda x: dt.strptime(x.get('date'), '%Y-%m-%d').date(), reverse=True)
    except ValueError as e:
        logging.error(f"Error sorting diary entries by date for account {account_id} and user {aac_user_id}: {e}")
    return JSONResponse(content=valid_entries)





@app.post("/api/diary-entry", response_model=DiaryEntryOutput, status_code=201)
async def add_or_update_diary_entry(entry_data: DiaryEntryInput, response: Response, current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)]):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    logging.info(f"POST /api/diary-entry received for account {account_id} and user {aac_user_id}: {entry_data}")

    # Initialize new_entry_dict before the loop to ensure it's always defined
    new_entry_dict = entry_data.model_dump()
    new_entry_dict['id'] = uuid.uuid4().hex  # Assign a new ID

    entries = await load_diary_entries(account_id, aac_user_id) # Load current entries (guaranteed to be a list)

    existing_entry_index = -1
    for i, entry in enumerate(entries):
        if isinstance(entry, dict) and entry.get('date') == new_entry_dict['date']:
            existing_entry_index = i
            logging.info(f"Found existing entry for date {new_entry_dict['date']}, will replace.")
            # If updating, preserve the existing ID on the new_entry_dict
            new_entry_dict['id'] = entry.get('id', new_entry_dict['id'])
            break

    current_status = 201 # Default for new entry
    if existing_entry_index != -1:
        entries[existing_entry_index] = new_entry_dict
        current_status = 200 # Set status for update
    else:
        entries.append(new_entry_dict) # Add the new entry

    # Attempt to delete a placeholder document if it exists, now that we have real entries
    try:
        placeholder_doc_ref = firestore_db.collection(f"{FIRESTORE_ACCOUNTS_COLLECTION}/{account_id}/{FIRESTORE_ACCOUNT_USERS_SUBCOLLECTION}/{aac_user_id}/diary_entries").document("placeholder")
        await asyncio.to_thread(placeholder_doc_ref.delete)
        logging.info(f"Attempted to delete placeholder diary entry for account {account_id}, user {aac_user_id}.")
    except Exception as e_placeholder:
        logging.warning(f"Could not delete placeholder diary entry (it might not exist or another error occurred): {e_placeholder}")

    if await save_diary_entries(account_id, aac_user_id, entries): # This now returns True/False
        # Direct return new_entry_dict as it holds the correct, saved state
        # The previous `next()` lookup is unnecessary and caused the error.
        return JSONResponse(content=new_entry_dict, status_code=current_status)
    else:
        logging.error(f"save_diary_entries function returned False for account {account_id} and user {aac_user_id}")
        raise HTTPException(status_code=500, detail="Failed to save diary entry.")




@app.delete("/api/diary-entry/{entry_id}")
async def delete_diary_entry(current_ids: Annotated[Dict[str, str], Depends(get_current_account_and_user_ids)], entry_id: str = Path(..., description="The ID of the diary entry to delete")):
    aac_user_id = current_ids["aac_user_id"]
    account_id = current_ids["account_id"]
    logging.info(f"DELETE /api/diary-entry/{entry_id} request received for account {account_id} and user {aac_user_id}.")
    entries = await load_diary_entries(account_id, aac_user_id) # Pass user_id
    initial_length = len(entries)
    entries_after_delete = [entry for entry in entries if entry.get('id') != entry_id]
    if len(entries_after_delete) < initial_length:
        if await save_diary_entries(account_id, aac_user_id, entries_after_delete): # Pass user_id
            logging.info(f"Deleted diary entry with ID: {entry_id} for account {account_id} and user {aac_user_id}")
            return JSONResponse(content={"message": "Diary entry deleted successfully."})
        else: raise HTTPException(status_code=500, detail="Failed to save diary file after deletion.")
    else: logging.warning(f"Diary entry with ID {entry_id} not found for deletion for account {account_id} and user {aac_user_id}."); raise HTTPException(status_code=404, detail="Diary entry not found.")





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
            
            # Update the RAG cache with new conversation data
            try:
                await cache_manager.store_cached_context(
                    account_id, 
                    aac_user_id, 
                    history, 
                    CacheType.CONVERSATION_SESSION
                )
                logging.info(f"Updated CONVERSATION_SESSION cache for user {aac_user_id}")
            except Exception as e:
                logging.error(f"Failed to update CONVERSATION_SESSION cache: {e}")
            
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
            
            # Invalidate button activity cache when new clicks are logged
            cache_manager = GeminiCacheManager()
            await cache_manager.invalidate_by_endpoint(account_id, aac_user_id, "/api/audit/log-button-click")
            
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
            prompt = f"Given the user context: '{user_context}' and the existing text: '{context_text}', provide 5 complete words that start with '{partial_word}'. The words should be contextually appropriate and commonly used. Return only the complete words, one per line."
        else:
            prompt = f"Given the user context: '{user_context}', provide 5 complete words that start with '{partial_word}'. The words should be commonly used. Return only the complete words, one per line."
        
        # Use LLM to generate predictions
        response_text = await _generate_gemini_content_with_fallback(prompt)
        
        # Parse predictions - ensure they are complete words starting with the partial word
        raw_predictions = [line.strip() for line in response_text.split('\n') if line.strip()]
        predictions = []
        
        for pred in raw_predictions[:8]:  # Get extra to filter
            # Ensure the prediction starts with the partial word and is a complete word
            if pred.lower().startswith(partial_word.lower()) and len(pred) > len(partial_word):
                predictions.append(pred)
            elif not partial_word and pred:  # If no partial word, just add valid predictions
                predictions.append(pred)
        
        # Limit to 5 predictions
        predictions = predictions[:5]
        
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
            variation_text = "different and alternative" if request.request_different_options else ""
            prompt = f"Given this context: {context_str} and the partial sentence '{build_space_text}', provide 20 {variation_text} useful words or short phrases that would logically complete or continue this communication. Focus on words that would naturally follow what's already written. Return only the words/phrases, one per line."
        else:
            # If no build space text, provide conversation starters
            variation_text = "different and alternative" if request.request_different_options else ""
            prompt = f"Given this context: {context_str}, provide 20 {variation_text} useful words or short phrases to START AAC communication. Include common conversation starters like 'I', 'You', 'Where', 'Who', 'What', 'Can', 'Want', 'Need', etc. Return only the words/phrases, one per line."
        
        logging.info(f"Generated prompt for LLM: {prompt}")

        # Use LLM to generate options
        response_text = await _generate_gemini_content_with_fallback(prompt)
        
        # Parse options
        options = [line.strip() for line in response_text.split('\n') if line.strip()][:20]
        
        logging.info(f"Generated {len(options)} word options for build space: '{build_space_text}' with context: {context_str}")
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
        # Load comprehensive user context (same as LLM endpoint)
        current_date = date.today()
        current_date_str = current_date.strftime("%A, %B %d, %Y")
        
        # Load user settings
        user_settings = await load_settings_from_file(account_id, aac_user_id)
        
        # Load holidays and birthdays
        upcoming_holidays_list = await get_upcoming_holidays_and_observances(account_id, aac_user_id, days_ahead=14)
        upcoming_birthdays_list = await get_upcoming_birthdays(account_id, aac_user_id, days_ahead=14)
        
        # Load diary entries
        diary_entries = await load_diary_entries(account_id, aac_user_id)
        
        # Process diary entries into past and future context
        past_diary_context = []
        future_diary_context = []
        for entry in diary_entries:
            try:
                if not isinstance(entry, dict): 
                    continue
                entry_date = date.fromisoformat(entry.get('date',''))
                entry_text = entry.get('entry', '')
                if not entry_text: continue
                
                if entry_date <= current_date and len(past_diary_context) < MAX_DIARY_CONTEXT:
                    days_ago = (current_date - entry_date).days
                    relative_day = f" ({days_ago} days ago)" if days_ago > 1 else (" (Yesterday)" if days_ago == 1 else " (Today)")
                    past_diary_context.append(f"Date: {entry['date']}{relative_day}\nEntry: {entry_text}")
                elif entry_date > current_date:
                    days_ahead_entry = (entry_date - current_date).days
                    relative_day = f" (in {days_ahead_entry} days)" if days_ahead_entry > 1 else (" (Tomorrow!)" if days_ahead_entry == 1 else " (Today - planned)")
                    future_diary_context.append({'date_obj': entry_date, 'text': f"Date: {entry['date']}{relative_day}\nEntry: {entry_text}"})
            except Exception:
                continue
        
        future_diary_context.sort(key=lambda x: x['date_obj'])
        future_diary_context = [item['text'] for item in future_diary_context[:MAX_DIARY_CONTEXT]]
        
        # Load chat history
        chat_history = await load_chat_history(account_id, aac_user_id)
        recent_chat_context = []
        for chat in reversed(chat_history[-MAX_CHAT_CONTEXT:]):
            if not isinstance(chat, dict):
                continue
            q = chat.get('question', '').strip().replace('Q: ', '').strip("' ")
            r = chat.get('response', '').strip().replace('A: ', '').strip("' ")
            if q and r: recent_chat_context.append(f"Previous Turn: Q: {q} / A: {r}")
        
        # Load user info and current state
        user_info_content_dict = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/user_narrative",
            default_data=DEFAULT_USER_INFO.copy()
        )
        user_info_content = user_info_content_dict.get("narrative", "").strip()
        
        user_current_content_dict = await load_firestore_document(
            account_id=account_id,
            aac_user_id=aac_user_id,
            doc_subpath="info/current_state",
            default_data=DEFAULT_USER_CURRENT.copy()
        )
        user_current_content = (
            f"Location: {user_current_content_dict.get('location', '')}\n"
            f"People Present: {user_current_content_dict.get('people', '')}\n"
            f"Activity: {user_current_content_dict.get('activity', '')}"
        ).strip()
        
        # Build context for personalized cleanup
        context_parts = []
        context_parts.append(f"Current Date: {current_date_str}")
        
        if user_info_content.strip():
            context_parts.append(f"General User Information:\n{user_info_content}")
        if user_current_content.strip():
            context_parts.append(f"User's Current State:\n{user_current_content}")
        
        # Add holidays and birthdays if available
        if upcoming_holidays_list and upcoming_holidays_list[0] != f"No major holidays or observances found in the next {14} days for {DEFAULT_COUNTRY_CODE}.":
            context_parts.append(f"Upcoming Holidays/Observances (approx. next 2 weeks):\n" + "\n".join(upcoming_holidays_list))
        
        if upcoming_birthdays_list and upcoming_birthdays_list[0] != f"No birthdays found in the next {14} days.":
            is_just_user_age = (len(upcoming_birthdays_list) == 1 and upcoming_birthdays_list[0].startswith("User's current age:"))
            if is_just_user_age:
                context_parts.append(upcoming_birthdays_list[0])
            else:
                context_parts.append(f"Birthday Info & Upcoming Birthdays (approx. next 2 weeks):\n" + "\n".join(upcoming_birthdays_list))
        
        # Add diary and chat context if available
        if past_diary_context:
            context_parts.append(f"Recent Diary Entries (most recent first):\n---\n" + "\n---\n".join(past_diary_context))
        if future_diary_context:
            context_parts.append(f"Upcoming Diary Plans (soonest first):\n---\n" + "\n---\n".join(future_diary_context))
        if recent_chat_context:
            context_parts.append(f"Recent Conversation History (most recent first):\n" + "\n".join(recent_chat_context))
        
        # Build personalized context
        personalized_context = "\n\n".join(c.strip() for c in context_parts if c.strip())
        
        # Create enhanced cleanup prompt with RAG context
        prompt = f"""{personalized_context}

Clean up and improve this text while preserving the original meaning and intent. Use the context above to make the cleanup more personalized and appropriate for this specific user.

Original text: "{request.text_to_cleanup}"

Please:
1. Fix grammar and punctuation
2. Make it more natural and conversational and complete if needed
3. Keep the same meaning and tone
4. Make it sound like natural speech appropriate for this user's context
5. Keep it concise and clear
6. The phrase should be structured like it is coming from the user
7. Consider the user's current situation, recent activities, and personal context when cleaning up

For example:
- "dad beekeeping" → "My dad is a beekeeper"
- "want food hungry" → "I want food because I'm hungry"
- "go store later" → "I want to go to the store later"

Return only the improved text, nothing else."""
        
        # Use LLM to cleanup text with personalized context
        cleaned_text = await _generate_gemini_content_with_fallback(prompt)
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)