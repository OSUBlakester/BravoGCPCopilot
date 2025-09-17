#!/usr/bin/env python3
"""
LOCAL DEVELOPMENT VERSION - PiCom Symbol Processing
This version works locally without GCP dependencies for testing only
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Create a simple FastAPI app for local testing
app = FastAPI(title="PiCom Symbol Local Dev")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Local SQLite database instead of Firestore
def init_local_db():
    """Initialize local SQLite database"""
    conn = sqlite3.connect('local_symbols.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS symbols (
            symbol_id TEXT PRIMARY KEY,
            filename TEXT,
            name TEXT,
            description TEXT,
            categories TEXT,
            tags TEXT,
            difficulty_level TEXT,
            age_groups TEXT,
            image_url TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

@app.on_event("startup")
async def startup_event():
    init_local_db()

@app.get("/")
async def root():
    return FileResponse("static/symbol_admin.html")

@app.get("/health")
async def health():
    return {"status": "healthy", "environment": "local_dev"}

@app.post("/api/symbols/analyze-picom")
async def analyze_picom_local():
    """Local version - just check if analysis file exists"""
    analysis_file = Path("picom_ready_for_ai_analysis.json")
    
    if analysis_file.exists():
        with open(analysis_file) as f:
            data = json.load(f)
        return {
            "success": True,
            "message": "Analysis file found",
            "statistics": data.get("statistics", {}),
            "ready_for_ai": True
        }
    else:
        # Run the analysis
        import subprocess
        result = subprocess.run([
            "python3", "analyze_picom_smart.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and analysis_file.exists():
            with open(analysis_file) as f:
                data = json.load(f)
            return {
                "success": True, 
                "message": "Analysis completed",
                "statistics": data.get("statistics", {}),
                "ready_for_ai": True
            }
        else:
            raise HTTPException(status_code=500, detail="Analysis failed")

@app.post("/api/symbols/process-batch")
async def process_batch_local(request_data: dict):
    """Local version - save to SQLite instead of Firestore"""
    try:
        batch_size = request_data.get("batch_size", 10)
        start_index = request_data.get("start_index", 0)
        
        # Load analysis data
        analysis_file = Path("picom_ready_for_ai_analysis.json")
        if not analysis_file.exists():
            raise HTTPException(status_code=404, detail="Run analysis first")
        
        with open(analysis_file) as f:
            analysis_data = json.load(f)
        
        # Get batch
        batch = analysis_data['images'][start_index:start_index + batch_size]
        
        # Save to SQLite
        conn = sqlite3.connect('local_symbols.db')
        cursor = conn.cursor()
        
        processed_count = 0
        for image_data in batch:
            symbol_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT OR REPLACE INTO symbols 
                (symbol_id, filename, name, description, categories, tags, 
                 difficulty_level, age_groups, image_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol_id,
                image_data['filename'],
                image_data['description'],
                image_data['description'],
                json.dumps(image_data['categories']),
                json.dumps(image_data['tags']),
                image_data.get('difficulty', 'simple'),
                json.dumps(['all']),
                f"/PiComImages/{image_data['filename']}",
                datetime.now().isoformat()
            ))
            processed_count += 1
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "processed_count": processed_count,
            "total_requested": len(batch),
            "next_start_index": start_index + batch_size,
            "remaining": max(0, len(analysis_data['images']) - (start_index + batch_size))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/symbols/search")
async def search_symbols_local(
    query: str = "",
    category: str = None,
    limit: int = 20
):
    """Local version - search SQLite database"""
    try:
        conn = sqlite3.connect('local_symbols.db')
        cursor = conn.cursor()
        
        # Build query
        sql = "SELECT * FROM symbols"
        params = []
        
        conditions = []
        if query:
            conditions.append("(name LIKE ? OR tags LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        
        if category:
            conditions.append("categories LIKE ?")
            params.append(f"%{category}%")
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += f" LIMIT {limit}"
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        
        symbols = []
        for row in results:
            symbol = {
                "symbol_id": row[0],
                "filename": row[1],
                "name": row[2],
                "description": row[3],
                "categories": json.loads(row[4]) if row[4] else [],
                "tags": json.loads(row[5]) if row[5] else [],
                "difficulty_level": row[6],
                "age_groups": json.loads(row[7]) if row[7] else [],
                "image_url": row[8],
                "created_at": row[9]
            }
            symbols.append(symbol)
        
        return {
            "symbols": symbols,
            "total_found": len(symbols),
            "query": query,
            "filters": {"category": category}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/symbols/categories")
async def get_categories_local():
    """Local version - get categories from analysis file"""
    try:
        analysis_file = Path("picom_ready_for_ai_analysis.json")
        if analysis_file.exists():
            with open(analysis_file) as f:
                data = json.load(f)
            
            categories = data.get("statistics", {}).get("categories", {})
            category_list = [
                {"name": cat, "count": count, "description": f"{count} symbols"}
                for cat, count in categories.items()
            ]
            category_list.sort(key=lambda x: x["count"], reverse=True)
            
            return {"categories": category_list}
        
        return {"categories": []}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/symbols/stats")
async def get_stats_local():
    """Local version - get stats from analysis file and SQLite"""
    try:
        # Check SQLite for processed count
        conn = sqlite3.connect('local_symbols.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM symbols")
        processed_count = cursor.fetchone()[0]
        conn.close()
        
        # Get total from analysis file
        analysis_file = Path("picom_ready_for_ai_analysis.json")
        if analysis_file.exists():
            with open(analysis_file) as f:
                data = json.load(f)
            
            stats = data.get("statistics", {})
            stats["processed_symbols"] = processed_count
            
            return {
                "success": True,
                "statistics": stats,
                "source": "local_sqlite"
            }
        
        return {
            "success": True,
            "statistics": {"processed_symbols": processed_count},
            "source": "local_sqlite"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🏠 Starting LOCAL PiCom Symbol System")
    print("⚠️  This is for DEVELOPMENT ONLY - not production!")
    print("📊 Visit: http://localhost:3000")
    print("🎨 Admin: http://localhost:3000/static/symbol_admin.html")
    
    uvicorn.run(app, host="0.0.0.0", port=3000)