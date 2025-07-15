from pydantic import BaseModel
from typing import List, Optional, Literal

class Option(BaseModel):
    id: str
    text: str

class Question(BaseModel):
    id: str
    type: Literal["mcq", "short", "long"]
    question: str
    options: Optional[List[Option]] = None
    required: bool

class Answer(BaseModel):
    questionId: str
    answer: str

class QuestionnaireInput(BaseModel):
    summary: str

class EvaluationInput(BaseModel):
    questionnaire: dict  # Same as the output of generate_questionnaire
    answers: List[Answer]
