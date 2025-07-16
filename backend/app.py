from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import uuid
from .cracker import ZipCracker

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary storage
UPLOAD_DIR = "tmp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/crack")
async def crack_zip(file: UploadFile = File(...), max_length: Optional[int] = 10):
    """API endpoint for cracking ZIP passwords."""
    # Validate file
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "File must be a ZIP archive")
    
    if file.size > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(400, "File too large (max 5MB)")
    
    # Save the file
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.zip")
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # Start cracking
    cracker = ZipCracker(file_path)
    result = cracker.crack()
    
    # Clean up
    try:
        os.remove(file_path)
    except:
        pass
    
    return {
        "success": result.success,
        "password": result.password,
        "attempts": result.attempts,
        "time_taken": result.time_taken,
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}