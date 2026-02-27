"""
Test/Quiz endpoints: list tests, get questions, submit answers.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List

from models.test import (
    TestOut, TestSubmission, TestAttemptOut, TestResultDetail, Question
)
from services import supabase_service as db
from utils.helpers import get_current_user_id, calculate_percentage

router = APIRouter()


@router.get("", response_model=List[TestOut])
async def list_tests(user_id: str = Depends(get_current_user_id)):
    """Get all available tests."""
    try:
        tests = db.get_all_tests()
        return [TestOut(**t) for t in tests]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tests: {str(e)}",
        )


@router.get("/{test_id}", response_model=TestOut)
async def get_test(test_id: str, user_id: str = Depends(get_current_user_id)):
    """Get a specific test by ID."""
    try:
        test = db.get_test_by_id(test_id)
        if not test:
            raise HTTPException(status_code=404, detail="Test not found")
        return TestOut(**test)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch test: {str(e)}",
        )


@router.get("/{test_id}/questions", response_model=List[Question])
async def get_test_questions(test_id: str, user_id: str = Depends(get_current_user_id)):
    """Get all questions for a specific test (without correct answers for active test)."""
    try:
        questions = db.get_questions_for_test(test_id)
        if not questions:
            raise HTTPException(status_code=404, detail="No questions found for this test")
        # Remove correct_option and explanation for active tests
        sanitized = []
        for q in questions:
            q_copy = dict(q)
            q_copy.pop("correct_option", None)
            q_copy.pop("explanation", None)
            sanitized.append(q_copy)
        return sanitized
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch questions: {str(e)}",
        )


@router.post("/submit", response_model=TestResultDetail)
async def submit_test(
    submission: TestSubmission,
    user_id: str = Depends(get_current_user_id),
):
    """Submit test answers and get results."""
    try:
        # Fetch the correct answers
        questions = db.get_questions_for_test(submission.test_id)
        if not questions:
            raise HTTPException(status_code=404, detail="Test not found or has no questions")

        # Build a lookup map: question_id -> question data
        q_map = {q["id"]: q for q in questions}

        # Grade the submission
        score = 0
        total_marks = 0
        graded_responses = []
        subject_breakdown = {}

        for resp in submission.responses:
            question = q_map.get(resp.question_id)
            if not question:
                continue

            is_correct = False
            marks_earned = 0

            if resp.selected_option is None:
                # Skipped
                marks_earned = 0
            elif resp.selected_option == question["correct_option"]:
                is_correct = True
                marks_earned = question.get("marks", 4)
            else:
                marks_earned = -question.get("negative_marks", 1)

            score += marks_earned
            total_marks += question.get("marks", 4)

            # Track subject breakdown
            subject = question.get("subject", "Unknown")
            if subject not in subject_breakdown:
                subject_breakdown[subject] = {
                    "total": 0, "correct": 0, "incorrect": 0,
                    "skipped": 0, "marks": 0, "total_marks": 0,
                }
            subject_breakdown[subject]["total"] += 1
            subject_breakdown[subject]["total_marks"] += question.get("marks", 4)
            if resp.selected_option is None:
                subject_breakdown[subject]["skipped"] += 1
            elif is_correct:
                subject_breakdown[subject]["correct"] += 1
                subject_breakdown[subject]["marks"] += marks_earned
            else:
                subject_breakdown[subject]["incorrect"] += 1
                subject_breakdown[subject]["marks"] += marks_earned

            graded_responses.append({
                "question_id": resp.question_id,
                "selected_option": resp.selected_option,
                "is_correct": is_correct,
                "correct_option": question["correct_option"],
                "time_spent_seconds": resp.time_spent_seconds,
                "marks_earned": marks_earned,
                "explanation": question.get("explanation"),
            })

        percentage = calculate_percentage(max(score, 0), total_marks)

        # Save to database
        attempt = db.save_test_attempt(
            user_id=user_id,
            test_id=submission.test_id,
            score=score,
            total_marks=total_marks,
            percentage=percentage,
            time_taken_minutes=submission.time_taken_minutes,
        )

        # Save individual responses
        db.save_question_responses(attempt["id"], graded_responses)

        return TestResultDetail(
            attempt=TestAttemptOut(
                id=attempt["id"],
                user_id=user_id,
                test_id=submission.test_id,
                score=score,
                total_marks=total_marks,
                percentage=percentage,
                time_taken_minutes=submission.time_taken_minutes,
                submitted_at=attempt.get("submitted_at"),
            ),
            responses=graded_responses,
            subject_breakdown=subject_breakdown,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit test: {str(e)}",
        )


@router.get("/attempts/history", response_model=List[TestAttemptOut])
async def get_attempt_history(user_id: str = Depends(get_current_user_id)):
    """Get the user's test attempt history."""
    try:
        attempts = db.get_user_attempts(user_id)
        return [TestAttemptOut(**a) for a in attempts]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch attempt history: {str(e)}",
        )


@router.get("/attempts/{attempt_id}/detail")
async def get_attempt_detail(
    attempt_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get detailed results for a specific test attempt."""
    try:
        responses = db.get_attempt_responses(attempt_id)
        return {"attempt_id": attempt_id, "responses": responses}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch attempt detail: {str(e)}",
        )
