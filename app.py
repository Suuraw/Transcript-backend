from fastapi import FastAPI, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
import os
from proxy_patch import patch_requests_with_proxy_url

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Proxy Setup
proxy_user = os.getenv("PROXY_USER")
proxy_pass = os.getenv("PROXY_PASS", "")
proxy_host = os.getenv("PROXY_HOST")
proxy_port = os.getenv("PROXY_PORT")

patch_requests_with_proxy_url(proxy_user, proxy_pass, proxy_host, proxy_port)

# Auth Token
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

@app.get("/")
def health_check():
    return {"message": "FastAPI YouTube Transcript API running"}

@app.post("/transcript")
async def get_transcript(request: Request, authorization: str = Header(None)):
    try:
        # Validate Authorization
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(content={"success": False, "error": "Missing or invalid Authorization header"}, status_code=401)

        token = authorization.split("Bearer ")[1]
        if token != SECRET_TOKEN:
            return JSONResponse(content={"success": False, "error": "Invalid token"}, status_code=403)

        body = await request.json()
        video_id = body.get("videoId")

        if not video_id:
            return JSONResponse(content={"success": False, "error": "Missing videoId in request."}, status_code=400)

        # Get transcript
        transcript_segments = YouTubeTranscriptApi.get_transcript(video_id)
        formatted_text = " ".join([seg["text"].strip() for seg in transcript_segments])


        return JSONResponse(content={"success": True, "transcript": formatted_text}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)
