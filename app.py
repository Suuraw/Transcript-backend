from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import BackgroundTasks
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
import os
import json
import math
import logging
import asyncio
import concurrent.futures
from google import genai  
import yt_dlp

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

# Global variables
latest_video_id = None
latest_transcript = None

# Create a thread pool executor for CPU-bound tasks (optional - can be removed if not needed)
# executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)

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

# Helper: Fetch video title (blocking operation)
def fetch_video_title(video_id: str) -> str:
    """Fetch video title synchronously"""
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get("title", f"Video {video_id}")
    except Exception as e:
        logger.error(f"Failed to fetch title for {video_id}: {e}")
        return f"Video {video_id}"

# Helper: Summarize transcript
def summarize_transcript(chunks: list[dict]) -> str:
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
        return response.text
    except Exception as e:
        logger.error(f"[Gemini API Error]: {e}")
        return "Failed to generate summary due to an internal error."

# Health check
@app.get("/")
def health_check():
    history = []
    try:
        with open("history.json", "r") as savedfile:
            history = json.load(savedfile)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []
        
    return JSONResponse(content={"message": "FastAPI Transcript API is running", "history": history}, status_code=200)

# Simple background task for saving transcript chunks only
def save_transcript_chunks(video_id: str, full_transcript: str):
    """Save transcript chunks without fetching title"""
    try:
        # Split into chunks
        chunks = split_transcript(full_transcript, max_words=2000)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        file_path = TRANSCRIPTS_DIR / f"{video_id}_{timestamp}_chunks.json"
        
        # Save chunks file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"video_id": video_id, "chunks": chunks}, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Saved transcript chunks for videoId: {video_id}")

    except Exception as e:
        logger.error(f"[Background Chunks Save Error]: {e}")

def update_history_with_title_and_summary(video_id: str, title: str, summary: str, transcript: str):
    """Update history with title and summary"""
    try:
        # Prepare history record
        transcript_data = {
            "videoId": video_id,
            "timestamp": datetime.now().timestamp(),
            "transcript": transcript,
            "summary": summary,
            "title": title
        }

        # Load/update history
        try:
            with open("history.json", "r") as infile:
                history = json.load(infile)
        except (json.JSONDecodeError, FileNotFoundError):
            history = []

        existing_index = next((i for i, entry in enumerate(history) if entry["videoId"] == video_id), None)
        if existing_index is not None:
            history[existing_index] = transcript_data
            logger.info(f"Updated history for videoId: {video_id}")
        else:
            history.append(transcript_data)
            logger.info(f"Added new history entry for videoId: {video_id}")

        with open("history.json", "w") as outfile:
            json.dump(history, outfile, indent=4)

    except Exception as e:
        logger.error(f"[History Update Error]: {e}")

# POST /transcript
@app.post("/transcript")
async def get_transcript(request: Request, background_tasks: BackgroundTasks, authorization: str = Header(None)):
    global latest_video_id, latest_transcript

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

        latest_video_id = video_id
        start_time = datetime.now()
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        full_transcript = " ".join([segment["text"].strip() for segment in transcript_list])
        latest_transcript = full_transcript  # Store transcript globally
        logger.info(f"Transcript fetch took {(datetime.now() - start_time).total_seconds():.2f} seconds")

        # 🔄 Schedule background task for saving transcript chunks only (fast)
        background_tasks.add_task(save_transcript_chunks, video_id, full_transcript)

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
    global latest_video_id, latest_transcript
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = authorization.split(" ")[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    try:
        # Find latest transcript chunks
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
        
        # Generate summary using Gemini API
        final_summary = summarize_transcript(chunks)
        
        # Fetch video title during summarization (since both are time-consuming)
        title = "Unknown Video"
        if latest_video_id:
            logger.info(f"Fetching title for video: {latest_video_id}")
            title = fetch_video_title(latest_video_id)
            logger.info(f"Retrieved title: {title}")

        # Clear the transcript folder
        clear_transcript_folder()

        # Update history with title and summary
        if latest_video_id and latest_transcript:
            update_history_with_title_and_summary(latest_video_id, title, final_summary, latest_transcript)

        return JSONResponse(
            content={"success": True, "summary": final_summary, "title": title},
            status_code=200
        )

    except Exception as e:
        logger.error(f"[Summarize Error]: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

from fastapi import Body  # Add this to existing imports
from questionnaire_generator import generate_questionnaire  # 👈 Import your logic

@app.post("/questionnaire")
async def generate_questionnaire_route(request: Request, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = authorization.split(" ")[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    try:
        body = await request.json()
        summary = body.get("summary", "").strip()
        
        if not summary:
            raise HTTPException(status_code=400, detail="Missing summary in request body.")

        result = generate_questionnaire(summary)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return JSONResponse(content={"success": True, "questionnaire": result}, status_code=200)

    except Exception as e:
        logger.error(f"[Questionnaire Generation Error]: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

from questionnaire_evaluator import evaluate_answers

@app.post("/evaluate")
async def evaluate_questionnaire_route(request: Request, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = authorization.split(" ")[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    try:
        body = await request.json()
        questionnaire = body.get("questionnaire")
        answers = body.get("answers")

        if not questionnaire or not answers:
            raise HTTPException(status_code=400, detail="Missing questionnaire or answers in request body.")

        evaluation = evaluate_answers(questionnaire, answers)
        print(evaluation)

        return JSONResponse(content={"success": True, "evaluation": evaluation}, status_code=200)

    except Exception as e:
        logger.error(f"[Evaluation Error]: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

# Cleanup executor on shutdown (optional - can be removed if executor is not used)
# @app.on_event("shutdown")
# def shutdown_event():
#     executor.shutdown(wait=True)