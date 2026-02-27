"""
AI recommendation endpoints.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List

from models.analytics import RecommendationOut
from services import supabase_service as db
from services import ai_service
from utils.helpers import get_current_user_id

router = APIRouter()


@router.get("", response_model=List[RecommendationOut])
async def get_recommendations(user_id: str = Depends(get_current_user_id)):
    """Get AI-powered study recommendations based on performance."""
    try:
        # First check if there are existing fresh recommendations
        existing = db.get_recommendations(user_id)
        if existing:
            return [RecommendationOut(**r) for r in existing]

        # Generate new recommendations based on performance
        responses = db.get_user_responses_with_details(user_id)
        performance = ai_service.analyze_performance(responses)

        # Generate recommendations (uses AI if available, otherwise rule-based)
        new_recs = await ai_service.generate_recommendations_with_ai(user_id, performance)

        # Save to database
        if new_recs:
            saved = db.save_recommendations(new_recs)
            return [RecommendationOut(**r) for r in saved]

        return []
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recommendations: {str(e)}",
        )


@router.post("/refresh", response_model=List[RecommendationOut])
async def refresh_recommendations(user_id: str = Depends(get_current_user_id)):
    """Force regenerate recommendations based on latest performance."""
    try:
        responses = db.get_user_responses_with_details(user_id)
        performance = ai_service.analyze_performance(responses)

        new_recs = await ai_service.generate_recommendations_with_ai(user_id, performance)

        if new_recs:
            saved = db.save_recommendations(new_recs)
            return [RecommendationOut(**r) for r in saved]

        return []
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh recommendations: {str(e)}",
        )


@router.put("/{rec_id}/complete")
async def complete_recommendation(
    rec_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Mark a recommendation as completed."""
    try:
        result = db.mark_recommendation_complete(rec_id, user_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found",
            )
        return {"message": "Recommendation marked as completed", "id": rec_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete recommendation: {str(e)}",
        )
