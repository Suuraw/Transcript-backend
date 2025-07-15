# llm/questionnaire_generator.py

import os
import uuid
import re
from google import genai
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def generate_questionnaire_prompt(summary: str) -> str:
    return (
        "You are an academic instructor creating a questionnaire from a video summary.\n\n"
        "Guidelines:\n"
        "- Dynamically decide the number and type of questions based on the length and complexity of the summary.\n"
        "- Randomly mix question types:\n"
        "   • Multiple Choice (MCQ) (4 options, one correct)\n"
        "   • Short Answer (1–2 sentence response)\n"
        "   • Long Answer (explanatory/analytical)\n"
        "- Return markdown with headers:\n"
        "   ### Multiple Choice Questions\n"
        "   ### Short Answer Questions\n"
        "   ### Long Answer Questions\n"
        "- Format:\n"
        "   **Q1:** What is ...?\n"
        "   - (a) Option A\n"
        "   - (b) Option B\n"
        "   - (c) Option C\n"
        "   - (d) Option D\n"
        "\nSummary:\n"
        f"{summary}"
    )

def parse_questionnaire_response(markdown: str) -> dict:
    questions = []
    section = None
    current_question = {}
    option_pattern = re.compile(r"- \((.)\)\s*(.+)")
    question_counter=1
    

    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("### Multiple Choice Questions"):
            section = "mcq"
            continue
        elif line.startswith("### Short Answer Questions"):
            section = "short"
            continue
        elif line.startswith("### Long Answer Questions"):
            section = "long"
            continue
        elif line.startswith("**Q"):
            if current_question:
                questions.append(current_question)
            current_question = {
                "id": f"q{question_counter}",
                "question": re.sub(r"\*\*Q\d+:\*\*", "", line).strip(),
                "type": section,
                "required": True,
                "options": [] if section == "mcq" else None,
            }
            question_counter += 1
        elif section == "mcq" and option_pattern.match(line):
            opt_id, opt_text = option_pattern.match(line).groups()
            current_question["options"].append({
            "id": f"{current_question['id']}{opt_id.strip().lower()}",
            "text": opt_text.strip()
    })


    if current_question:
        questions.append(current_question)

    return {
        "title": "Auto-Generated Questionnaire",
        "description": "Answer the following questions based on the video summary.",
        "questions": questions
    }

def generate_questionnaire(summary: str) -> dict:
    prompt = generate_questionnaire_prompt(summary)
    try:
        start_time = datetime.now()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        print(f"[Gemini Questionnaire Generation] Took {(datetime.now() - start_time).total_seconds()}s")
        return parse_questionnaire_response(response.text)
    except Exception as e:
        print(f"[Gemini Error - Questionnaire]: {e}")
        return {"error": "Failed to generate questionnaire."}
