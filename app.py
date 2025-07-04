# main.py
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
from gemini import summarize_transcript
import os

# Load environment variables
load_dotenv()

# Get the API token
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise Exception("API_TOKEN is not set in environment variables.")

# Initialize FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"message": "FastAPI Transcript API is running"}

# Route 1: Extract transcript from a YouTube video
@app.post("/transcript")
async def get_transcript(
    request: Request,
    authorization: str = Header(None)
):
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

        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        full_transcript = " ".join([segment["text"].strip() for segment in transcript_list])

        return JSONResponse(
            content={"success": True, "transcript": full_transcript},
            status_code=200
        )

    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

# Route 2: Summarize a transcript using Gemini
@app.post("/summarize")
async def summarize_transcript_route(
    request: Request,
    authorization: str = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = authorization.split(" ")[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    try:
        body = await request.json()
        transcript = body.get("transcript")

        if not transcript:
            return JSONResponse(
                content={"success": False, "error": "Missing transcript in request."},
                status_code=400
            )

        summary = summarize_transcript(transcript)

        return JSONResponse(
            content={"success": True, "summary": summary},
            status_code=200
        )

    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )
