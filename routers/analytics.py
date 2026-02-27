"""
Analytics endpoints: overview, subject breakdown, weekly progress.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List

from models.analytics import (
    OverviewAnalytics, SubjectAnalytics, ProgressTrend, WeeklyProgressOut
)
from services import supabase_service as db
from services import ai_service
from utils.helpers import get_current_user_id

router = APIRouter()


@router.get("/overview", response_model=OverviewAnalytics)
async def get_overview(user_id: str = Depends(get_current_user_id)):
    """Get overall performance analytics for the user."""
    try:
        # Get all attempts
        attempts = db.get_user_attempts(user_id)
        if not attempts:
            return OverviewAnalytics()

        # Get all responses with question details
        responses = db.get_user_responses_with_details(user_id)

        # Calculate overview
        total_tests = len(attempts)
        scores = [a["percentage"] for a in attempts]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0
        best_score = max(scores) if scores else 0
        total_time = sum(a.get("time_taken_minutes", 0) or 0 for a in attempts)

        # Question-level stats
        total_questions = len(responses)
        correct = sum(1 for r in responses if r.get("is_correct"))
        skipped = sum(1 for r in responses if r.get("selected_option") is None)
        incorrect = total_questions - correct - skipped
        accuracy = round((correct / total_questions * 100) if total_questions > 0 else 0, 2)

        # Subject performance
        performance = ai_service.analyze_performance(responses)
        subject_perf = {}
        for subject, stats in performance.get("subjects", {}).items():
            subject_perf[subject] = stats["accuracy"]

        return OverviewAnalytics(
            total_tests_taken=total_tests,
            average_score=avg_score,
            best_score=best_score,
            total_time_spent_minutes=total_time,
            accuracy_percentage=accuracy,
            total_questions_attempted=total_questions,
            correct_answers=correct,
            incorrect_answers=incorrect,
            skipped_questions=skipped,
            subject_performance=subject_perf,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch analytics: {str(e)}",
        )


@router.get("/subject/{subject}", response_model=SubjectAnalytics)
async def get_subject_analytics(
    subject: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get detailed analytics for a specific subject."""
    try:
        responses = db.get_user_responses_with_details(user_id)

        # Filter by subject
        subject_responses = [
            r for r in responses
            if r.get("questions", {}).get("subject", "").lower() == subject.lower()
        ]

        if not subject_responses:
            return SubjectAnalytics(subject=subject)

        total = len(subject_responses)
        correct = sum(1 for r in subject_responses if r.get("is_correct"))
        skipped = sum(1 for r in subject_responses if r.get("selected_option") is None)
        incorrect = total - correct - skipped
        accuracy = round((correct / total * 100) if total > 0 else 0, 2)

        # Average time per question
        times = [r.get("time_spent_seconds", 0) or 0 for r in subject_responses]
        avg_time = round(sum(times) / len(times), 1) if times else 0

        # Topic breakdown
        from collections import defaultdict
        topic_stats = defaultdict(lambda: {"total": 0, "correct": 0})
        diff_stats = defaultdict(lambda: {"total": 0, "correct": 0, "incorrect": 0})

        for r in subject_responses:
            q = r.get("questions", {})
            topic = q.get("topic", "Unknown")
            diff = q.get("difficulty", "Medium")

            topic_stats[topic]["total"] += 1
            diff_stats[diff]["total"] += 1

            if r.get("is_correct"):
                topic_stats[topic]["correct"] += 1
                diff_stats[diff]["correct"] += 1
            elif r.get("selected_option") is not None:
                diff_stats[diff]["incorrect"] += 1

        topic_breakdown = [
            {
                "topic": topic,
                "total": stats["total"],
                "correct": stats["correct"],
                "accuracy": round((stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0, 1),
            }
            for topic, stats in topic_stats.items()
        ]
        topic_breakdown.sort(key=lambda x: x["accuracy"])

        difficulty_breakdown = {
            diff: {
                "total": stats["total"],
                "correct": stats["correct"],
                "incorrect": stats["incorrect"],
                "accuracy": round((stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0, 1),
            }
            for diff, stats in diff_stats.items()
        }

        return SubjectAnalytics(
            subject=subject,
            total_questions=total,
            correct=correct,
            incorrect=incorrect,
            skipped=skipped,
            accuracy=accuracy,
            average_time_per_question=avg_time,
            topic_breakdown=topic_breakdown,
            difficulty_breakdown=difficulty_breakdown,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch subject analytics: {str(e)}",
        )


@router.get("/progress", response_model=ProgressTrend)
async def get_progress(user_id: str = Depends(get_current_user_id)):
    """Get weekly progress data for the user."""
    try:
        weekly_data = db.get_weekly_progress(user_id, limit=12)

        weeks = [WeeklyProgressOut(**w) for w in weekly_data]

        # Determine overall trend
        trend = "stable"
        if len(weeks) >= 2:
            recent_scores = [w.average_score or 0 for w in weeks[:3]]
            older_scores = [w.average_score or 0 for w in weeks[3:6]] if len(weeks) > 3 else recent_scores
            recent_avg = sum(recent_scores) / len(recent_scores) if recent_scores else 0
            older_avg = sum(older_scores) / len(older_scores) if older_scores else 0

            if recent_avg > older_avg + 5:
                trend = "improving"
            elif recent_avg < older_avg - 5:
                trend = "declining"

        return ProgressTrend(weeks=weeks, overall_trend=trend)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch progress: {str(e)}",
        )


@router.get("/prediction")
async def get_score_prediction(
    exam_type: str = "JEE Main",
    user_id: str = Depends(get_current_user_id),
):
    """Get AI-powered score prediction for an exam."""
    try:
        responses = db.get_user_responses_with_details(user_id)
        if not responses:
            return {
                "message": "Not enough data for prediction. Take some tests first.",
                "predicted_score": None,
            }

        performance = ai_service.analyze_performance(responses)
        prediction = ai_service.predict_score(performance, exam_type)
        return prediction
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate prediction: {str(e)}",
        )
