import re
import json
from datetime import datetime
from google import genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def generate_evaluation_prompt(questions: list, answers: list) -> str:
    prompt = """You are a grading assistant.

Evaluate the following questionnaire responses. For each question:
- If MCQ: mark if the answer is correct and mention the correct option.
- If Short/Long Answer: assess clarity, correctness, depth, and give constructive feedback.
- Provide a score out of 10 for each question and optionally a comment.

Return an array of JSON objects like:
[
  {
    "questionId": "...",
    "type": "mcq" | "short" | "long",
    "question": "...",
    "answer": "...",
    "correctOption": "a",
    "isCorrect": true,
    "score": 8,
    "feedback": "..."
  }
]

Questions and answers:
"""

    for q in questions:
        ans = next((a["answer"] for a in answers if a["questionId"] == q["id"]), "")
        prompt += f"\nQ: {q['question']}\n"
        if q["type"] == "mcq" and q.get("options"):
            for o in q["options"]:
                prompt += f"- ({o['id']}) {o['text']}\n"
        prompt += f"A: {ans}\n"

    return prompt

def evaluate_answers(questionnaire: dict, answers: list) -> list:
    prompt = generate_evaluation_prompt(questionnaire["questions"], answers)
    try:
        start_time = datetime.now()
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt
        )
        print(f"[Gemini Answer Evaluation] Took {(datetime.now() - start_time).total_seconds()}s")

        match = re.search(r"\[.*\]", response.text, re.DOTALL)
        evaluation_json = json.loads(match.group(0)) if match else []
        return evaluation_json
    except Exception as e:
        print(f"[Gemini Error - Evaluation]: {e}")
        return []
