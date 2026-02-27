from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Question(BaseModel):
    id: Optional[str] = None
    test_id: Optional[str] = None
    subject: str
    topic: str
    difficulty: str = "Medium"
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str = Field(..., pattern="^[A-D]$")
    explanation: Optional[str] = None
    marks: int = 4
    negative_marks: int = 1
    created_at: Optional[str] = None


class QuestionResponse(BaseModel):
    question_id: str
    selected_option: Optional[str] = Field(None, pattern="^[A-D]$")
    time_spent_seconds: Optional[int] = None


class TestCreate(BaseModel):
    title: str
    description: Optional[str] = None
    exam_type: str = "JEE Main"
    duration_minutes: int = 180
    total_marks: int = 300


class TestOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    exam_type: str
    duration_minutes: int
    total_marks: int
    created_at: Optional[str] = None
    question_count: Optional[int] = None


class TestSubmission(BaseModel):
    test_id: str
    responses: List[QuestionResponse]
    time_taken_minutes: Optional[int] = None


class TestAttemptOut(BaseModel):
    id: str
    user_id: str
    test_id: str
    score: int
    total_marks: int
    percentage: float
    time_taken_minutes: Optional[int] = None
    submitted_at: Optional[str] = None


class TestResultDetail(BaseModel):
    attempt: TestAttemptOut
    responses: List[dict]
    subject_breakdown: dict
