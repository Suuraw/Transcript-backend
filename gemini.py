from google import genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def summarize_transcript(transcript: str) -> str:
    """
    Summarizes a given transcript using Gemini 2.5 Flash in bullet points.

    Args:
        transcript (str): The full transcript text to summarize.

    Returns:
        str: The summary returned by Gemini API.
    """
    prompt = (
        "You are an expert summarizer. Given the following YouTube transcript, summarize what the video is about "
        "in 4-6 bullet points. Be concise, insightful, and avoid unnecessary fluff.\n\n"
        f"{transcript}"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"[Gemini API Error]: {e}")
        return "Failed to generate summary due to an internal error."
