from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
import os
import json
import math
import logging
# import re
from google import genai  # Assuming this is the correct import for the Gemini API client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not API_TOKEN:
    raise Exception("API_TOKEN is not set in environment variables.")
if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY is not set in environment variables.")

# Configure Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory setup
TRANSCRIPTS_DIR = Path("transcripts")
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# Helper: Split transcript into chunks
def split_transcript(transcript: str, max_words: int = 2000):
    words = transcript.split()
    num_chunks = math.ceil(len(words) / max_words)
    return [
        {
            "chunk_id": i + 1,
            "content": " ".join(words[i * max_words:(i + 1) * max_words])
        }
        for i in range(num_chunks)
    ]

# Helper: Clear transcript folder
def clear_transcript_folder():
    for file in TRANSCRIPTS_DIR.glob("*.json"):
        if file.is_file():
            file.unlink()

# Helper: Summarize transcript
def summarize_transcript(chunks: list[dict]) -> str:
    """
    Generates a detailed educational summary of transcript chunks using Gemini 2.5 Flash.
    
    Args:
        chunks (list[dict]): List of transcript chunks with 'content' field.
    
    Returns:
        str: A comprehensive, structured summary with excessive newlines removed.
    """
    combined_content = "\n\n".join(chunk["content"] for chunk in chunks)
    if not combined_content:
        return "No content to summarize."
    
    prompt = (
        "As a technical educator, summarize the following transcript into a detailed, structured summary for learners. "
        "Explain key concepts clearly and organize with sections or bullet points, focusing on educational value:\n\n"
        f"{combined_content}"
    )
    
    try:
        start_time = datetime.now()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        logger.info(f"Gemini API call took {(datetime.now() - start_time).total_seconds():.2f} seconds")
        # Remove excessive newlines (2 or more) and replace with a single space
        # Replace single newlines with a space for compact JSON output
        return response.text
    except Exception as e:
        logger.error(f"[Gemini API Error]: {e}")
        return "Failed to generate summary due to an internal error."

# Health check
@app.get("/")
def health_check():
    return {"message": "FastAPI Transcript API is running"}

# POST /transcript
@app.post("/transcript")
async def get_transcript(request: Request, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    
    token = authorization.split(" ")[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    try:
        body = await request.json()
        video_id = body.get("videoId")

        if not video_id:
            return JSONResponse(
                content={"success": False, "error": "Missing videoId in request."},
                status_code=400
            )

        # Fetch transcript
        start_time = datetime.now()
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        full_transcript = " ".join([segment["text"].strip() for segment in transcript_list])
        logger.info(f"Transcript fetch took {(datetime.now() - start_time).total_seconds():.2f} seconds")

        # Split and save
        chunks = split_transcript(full_transcript, max_words=2000)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        file_path = TRANSCRIPTS_DIR / f"{video_id}_{timestamp}_chunks.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"video_id": video_id, "chunks": chunks}, f, ensure_ascii=False, indent=4)

        return JSONResponse(
            content={"success": True, "transcript": full_transcript},
            status_code=200
        )

    except Exception as e:
        logger.error(f"[Transcript Error]: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

# POST /summarize
@app.post("/summarize")
async def summarize_transcript_route(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    
    token = authorization.split(" ")[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    try:
        # Find latest transcript file
        files = sorted(TRANSCRIPTS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
        if not files:
            return JSONResponse(
                content={"success": False, "error": "No transcript files found."},
                status_code=404
            )

        latest_file = files[0]
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        chunks = data.get("chunks", [])
        
        # Summarize transcript
        final_summary = summarize_transcript(chunks)
        
        # Clear transcript folder
        clear_transcript_folder()
        
        return JSONResponse(
            content={"success": True, "summary": final_summary},
            status_code=200
        )

    except Exception as e:
        logger.error(f"[Summarize Error]: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )
