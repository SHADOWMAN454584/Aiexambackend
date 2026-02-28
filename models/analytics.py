from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import date


class OverviewAnalytics(BaseModel):
    total_tests_taken: int = 0
    average_score: float = 0.0
    best_score: float = 0.0
    total_time_spent_minutes: int = 0
    accuracy_percentage: float = 0.0
    total_questions_attempted: int = 0
    correct_answers: int = 0
    incorrect_answers: int = 0
    skipped_questions: int = 0
    subject_performance: Dict[str, float] = {}


class SubjectAnalytics(BaseModel):
    subject: str
    total_questions: int = 0
    correct: int = 0
    incorrect: int = 0
    skipped: int = 0
    accuracy: float = 0.0
    average_time_per_question: float = 0.0
    topic_breakdown: List[Dict] = []
    difficulty_breakdown: Dict[str, Dict] = {}


class WeeklyProgressOut(BaseModel):
    id: Optional[str] = None
    week_start: str
    average_score: Optional[float] = 0.0
    tests_taken: int = 0
    total_time_minutes: int = 0
    physics_avg: Optional[float] = 0.0
    chemistry_avg: Optional[float] = 0.0
    maths_avg: Optional[float] = 0.0
    biology_avg: Optional[float] = 0.0


class ProgressTrend(BaseModel):
    weeks: List[WeeklyProgressOut] = []
    overall_trend: str = "stable"  # improving, declining, stable


class RecommendationOut(BaseModel):
    id: str
    title: str
    description: str
    subject: str
    priority: str = "Medium"
    type: str = "practice"
    estimated_time: Optional[str] = None
    is_completed: bool = False
    created_at: Optional[str] = None


class ScannedPaperOut(BaseModel):
    id: str
    exam_type: str
    year: Optional[int] = None
    image_url: Optional[str] = None
    extracted_text: Optional[str] = None
    questions_extracted: int = 0
    status: str = "processing"
    created_at: Optional[str] = None


class DocumentOut(BaseModel):
    id: str
    filename: str
    file_url: Optional[str] = None
    file_size: int = 0
    mime_type: str
    page_count: int = 0
    extracted_text: Optional[str] = None
    subject: Optional[str] = None
    exam_type: str = "JEE Main"
    status: str = "processing"
    created_at: Optional[str] = None


class DocumentTestRequest(BaseModel):
    document_id: str
    num_questions: int = 10
    difficulty: str = "Medium"  # Easy | Medium | Hard | Mixed
    exam_type: str = "JEE Main"
    subject: Optional[str] = None  # override auto-detected subject
