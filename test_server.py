#!/usr/bin/env python3
"""
Minimal server for testing the custom avatar prototype locally.
This server only includes the essential routes needed for avatar testing.
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn

# Get the directory of this script
current_dir = Path(__file__).parent

# Configure paths
static_file_path = current_dir / "static"
templates_dir = current_dir / "templates" if (current_dir / "templates").exists() else static_file_path

app = FastAPI(title="Bravo Avatar Prototype Server", debug=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_file_path)), name="static")

# Template configuration
templates = Jinja2Templates(directory=str(templates_dir))

@app.get("/")
async def root():
    """Root endpoint - redirect to avatar prototype"""
    return {"message": "Bravo Avatar Prototype Server", "available_routes": ["/avatar-prototype"]}

@app.get("/avatar-prototype")
async def avatar_prototype():
    """Serve the custom avatar prototype page"""
    html_file = static_file_path / "custom-avatar-prototype.html"
    if html_file.exists():
        return FileResponse(str(html_file))
    else:
        return HTMLResponse("<h1>Error: custom-avatar-prototype.html not found</h1>", status_code=404)

@app.get("/custom-avatar-prototype")
async def custom_avatar_prototype():
    """Alternative route for the custom avatar prototype page"""
    return await avatar_prototype()

@app.get("/dicebear-avatar-system")
async def dicebear_avatar_system():
    """Serve the DiceBear professional avatar system page"""
    html_file = static_file_path / "dicebear-avatar-system.html"
    if html_file.exists():
        return FileResponse(str(html_file))
    else:
        return HTMLResponse("<h1>Error: dicebear-avatar-system.html not found</h1>", status_code=404)

@app.get("/professional-avatars")
async def professional_avatars():
    """Alternative route for the DiceBear avatar system"""
    return await dicebear_avatar_system()

@app.get("/dicebear-test")
async def dicebear_test():
    """Serve the DiceBear API test page"""
    html_file = static_file_path / "dicebear-test.html"
    if html_file.exists():
        return FileResponse(str(html_file))
    else:
        return HTMLResponse("<h1>Error: dicebear-test.html not found</h1>", status_code=404)

@app.get("/funko-creator")
async def funko_creator():
    """Serve the Funko Pop Avatar Creator"""
    html_file = static_file_path / "funko-avatar-creator.html"
    if html_file.exists():
        return FileResponse(str(html_file))
    else:
        return HTMLResponse("<h1>Error: funko-avatar-creator.html not found</h1>", status_code=404)

@app.get("/funko-avatars")
async def funko_avatars():
    """Alternative route for Funko Pop creator"""
    return await funko_creator()

@app.get("/modular-avatars")
async def modular_avatars():
    """Serve the Modular Avatar Creator"""
    html_file = static_file_path / "modular-avatar-creator.html"
    if html_file.exists():
        return FileResponse(str(html_file))
    else:
        return HTMLResponse("<h1>Error: modular-avatar-creator.html not found</h1>", status_code=404)

@app.get("/enhanced-avatar-selector")
async def enhanced_avatar_selector():
    """Serve the Enhanced Avatar Selector with improved emotions and DiceBear integration"""
    html_file = static_file_path / "enhanced-avatar-selector.html"
    if html_file.exists():
        return FileResponse(str(html_file))
    else:
        return HTMLResponse("<h1>Error: enhanced-avatar-selector.html not found</h1>", status_code=404)

@app.get("/avatar-selector")
async def avatar_selector():
    """Serve the original Avatar Selector"""
    html_file = static_file_path / "avatar-selector.html"
    if html_file.exists():
        return FileResponse(str(html_file))
    else:
        return HTMLResponse("<h1>Error: avatar-selector.html not found</h1>", status_code=404)

@app.get("/mood-avatar-integration")
async def mood_avatar_integration():
    """Serve the Mood-Avatar Integration Test page"""
    html_file = static_file_path / "mood-avatar-integration-test.html"
    if html_file.exists():
        return FileResponse(str(html_file))
    else:
        return HTMLResponse("<h1>Error: mood-avatar-integration-test.html not found</h1>", status_code=404)

@app.get("/mood-avatar-test")
async def mood_avatar_test():
    """Alternative route for Mood-Avatar Integration Test"""
    return await mood_avatar_integration()

@app.get("/api/settings")
async def mock_settings():
    """Mock settings endpoint for testing"""
    return {
        "enableMoodSelection": True,
        "ScanningOff": False,
        "scanDelay": 3500
    }

if __name__ == "__main__":
    print("🚀 Starting Bravo Avatar Prototype Server")
    print("   Available at: http://localhost:8001/avatar-prototype")
    print("   Static files: /static/")
    print("   Press Ctrl+C to stop")
    
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8001, 
        log_level="info"
    )