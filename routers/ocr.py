"""
OCR endpoints: upload and scan PYQ images.
"""
import uuid
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from typing import Optional, List

from models.analytics import ScannedPaperOut
from services import supabase_service as db
from services import ocr_service
from utils.helpers import get_current_user_id

router = APIRouter()


@router.post("/scan", response_model=ScannedPaperOut)
async def scan_pyq(
    file: UploadFile = File(..., description="PYQ image to scan"),
    exam_type: str = Form(default="JEE Main", description="Exam type"),
    year: Optional[int] = Form(default=None, description="Year of the paper"),
    user_id: str = Depends(get_current_user_id),
):
    """Upload and scan a PYQ (Previous Year Question) image."""
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp", "image/bmp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(allowed_types)}",
        )

    try:
        # Read image bytes
        image_bytes = await file.read()

        # Limit file size (10MB)
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum size is 10MB.",
            )

        # Upload to Supabase Storage
        file_ext = file.filename.split(".")[-1] if file.filename else "png"
        storage_path = f"{user_id}/{uuid.uuid4().hex}.{file_ext}"
        try:
            image_url = db.upload_file_to_storage("pyq-scans", storage_path, image_bytes, file.content_type)
        except Exception:
            image_url = None  # Storage upload is optional

        # Create database record
        paper = db.save_scanned_paper(
            user_id=user_id,
            exam_type=exam_type,
            year=year,
            image_url=image_url,
        )

        # Process OCR
        ocr_result = ocr_service.process_scanned_image(image_bytes)

        # Update the record with OCR results
        updates = {
            "extracted_text": ocr_result["extracted_text"],
            "questions_extracted": ocr_result["questions_extracted"],
            "status": "completed",
        }
        updated_paper = db.update_scanned_paper(paper["id"], updates)

        # Merge for response
        paper.update(updated_paper or updates)

        return ScannedPaperOut(**paper)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process scan: {str(e)}",
        )


@router.get("/papers", response_model=List[ScannedPaperOut])
async def list_scanned_papers(user_id: str = Depends(get_current_user_id)):
    """Get all scanned papers for the current user."""
    try:
        papers = db.get_user_scanned_papers(user_id)
        return [ScannedPaperOut(**p) for p in papers]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch scanned papers: {str(e)}",
        )


@router.get("/papers/{paper_id}")
async def get_scanned_paper_detail(
    paper_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get detailed info and extracted questions for a scanned paper."""
    try:
        papers = db.get_user_scanned_papers(user_id)
        paper = next((p for p in papers if p["id"] == paper_id), None)

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scanned paper not found",
            )

        # Re-parse questions from extracted text if available
        questions = []
        if paper.get("extracted_text"):
            questions = ocr_service.parse_questions_from_text(paper["extracted_text"])

        return {
            "paper": ScannedPaperOut(**paper),
            "parsed_questions": questions,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch paper detail: {str(e)}",
        )
