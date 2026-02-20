from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

# --- Dynamic Static Page Routes ---
# List of static HTML files to be served from the root path.
STATIC_PAGES = [
    "gridpage.html",
    "admin.html",
    "admin_pages.html",
    "admin_settings.html",
    "user_current_admin.html",
    "audio_admin.html",
    "missing_images.html",
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
    "threads.html",
    "tap_interface.html",
    "tap_interface_admin.html",
    "image_management.html",
    "help_admin.html",
    "avatar_admin.html",
    "jokes.html",
    "games.html",
    "mood.html",
    "symbol_admin.html",
    "accent_migration.html"
]

for page in STATIC_PAGES:
    @router.get(f"/{page}", include_in_schema=False)
    async def serve_static_page(page_name: str = page): # Use default argument to capture page name
        return FileResponse(f"static/{page_name}")
