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

# Global variable for latest videoId
latest_video_id = None

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
    return {"message": "FastAPI Transcript API is running"}

# POST /transcript
@app.post("/transcript")
async def get_transcript(request: Request, authorization: str = Header(None)):
    global latest_video_id

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

        # Fetch transcript
        start_time = datetime.now()
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        full_transcript = " ".join([segment["text"].strip() for segment in transcript_list])
        logger.info(f"Transcript fetch took {(datetime.now() - start_time).total_seconds():.2f} seconds")

        # Split and save chunks
        chunks = split_transcript(full_transcript, max_words=2000)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        file_path = TRANSCRIPTS_DIR / f"{video_id}_{timestamp}_chunks.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"video_id": video_id, "chunks": chunks}, f, ensure_ascii=False, indent=4)

        # Prepare new transcript entry
        Transcript_data = {
            "videoId": video_id,
            "timestamp": datetime.now().timestamp(),
            "transcript": full_transcript,
            "summary": ""
        }

        # Load and update history.json
        try:
            with open("history.json", "r") as infile:
                history = json.load(infile)
        except (json.JSONDecodeError, FileNotFoundError):
            history = []

        # Update if videoId already exists, otherwise append
        existing_index = next((i for i, entry in enumerate(history) if entry["videoId"] == video_id), None)
        if existing_index is not None:
            history[existing_index] = Transcript_data
            logger.info(f"Updated existing transcript for videoId: {video_id}")
        else:
            history.append(Transcript_data)
            logger.info(f"Appended new transcript for videoId: {video_id}")

        with open("history.json", "w") as outfile:
            json.dump(history, outfile, indent=4)

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
        final_summary = summarize_transcript(chunks)

        # Clear the transcript folder
        clear_transcript_folder()

        # Update summary in history
        with open("history.json", "r") as infile:
            history = json.load(infile)

        updated = False
        for entry in history:
            if entry["videoId"] == latest_video_id:
                entry["summary"] = final_summary
                updated = True
                break

        if updated:
            with open("history.json", "w") as outfile:
                json.dump(history, outfile, indent=4)
            logger.info(f"Summary updated for videoId: {latest_video_id}")
        else:
            logger.warning(f"No matching videoId found: {latest_video_id}")

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
