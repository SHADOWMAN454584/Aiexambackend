"""
Document upload & AI-powered test generation endpoints.
Supports PDF and image uploads; extracts text and generates personalised MCQ tests.
"""
import uuid
import io
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from typing import Optional, List

from models.analytics import DocumentOut, DocumentTestRequest
from models.test import TestOut, Question
from services import supabase_service as db
from services import ai_service
from services import ocr_service
from utils.helpers import get_current_user_id

router = APIRouter()

# Maximum upload size: 4.5 MB (Vercel serverless body limit)
MAX_UPLOAD_BYTES = 4 * 1024 * 1024  # 4 MB to stay safely under Vercel's 4.5 MB limit

# Allowed MIME types
ALLOWED_TYPES = [
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/bmp",
]


def _extract_text_from_pdf(file_bytes: bytes) -> dict:
    """
    Extract text from a PDF using pdfplumber (pure Python, Vercel-compatible).
    """
    try:
        import pdfplumber
    except ImportError:
        return {
            "text": "[PDF] pdfplumber not installed. Install pdfplumber to enable PDF text extraction.",
            "page_count": 0,
        }

    try:
        pdf = pdfplumber.open(io.BytesIO(file_bytes))
        page_count = len(pdf.pages)
        pages_text = []

        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                pages_text.append(text.strip())

        pdf.close()
        return {
            "text": "\n\n".join(pages_text),
            "page_count": page_count,
        }
    except Exception as e:
        return {"text": f"[PDF Error] {str(e)}", "page_count": 0}


def _extract_text_from_upload(file_bytes: bytes, content_type: str) -> dict:
    """Route extraction to the right handler based on MIME type."""
    if content_type == "application/pdf":
        return _extract_text_from_pdf(file_bytes)
    else:
        # Image file — use existing OCR service
        text = ocr_service.extract_text_from_image(file_bytes)
        return {"text": text, "page_count": 1}


# ─── Endpoints ─────────────────────────────────────────────────────


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="PDF or image file to upload"),
    exam_type: str = Form(default="JEE Main", description="Target exam type"),
    subject: Optional[str] = Form(default=None, description="Subject (auto-detected if omitted)"),
    user_id: str = Depends(get_current_user_id),
):
    """
    Upload a PDF or image document.
    Extracts text and stores the document for later test generation.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    try:
        file_bytes = await file.read()

        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
            )

        # Upload to Supabase Storage
        file_ext = file.filename.split(".")[-1] if file.filename else "pdf"
        storage_path = f"documents/{user_id}/{uuid.uuid4().hex}.{file_ext}"
        try:
            file_url = db.upload_file_to_storage(
                "documents", storage_path, file_bytes, file.content_type
            )
        except Exception:
            file_url = None

        # Create the DB record (status = processing)
        doc = db.save_document(
            user_id=user_id,
            filename=file.filename or f"upload.{file_ext}",
            mime_type=file.content_type,
            file_size=len(file_bytes),
            file_url=file_url,
            exam_type=exam_type,
            subject=subject,
        )

        # Extract text
        extraction = _extract_text_from_upload(file_bytes, file.content_type)
        detected_subject = subject or ai_service._detect_subject(extraction["text"])

        updates = {
            "extracted_text": extraction["text"],
            "page_count": extraction["page_count"],
            "subject": detected_subject,
            "status": "completed" if extraction["text"] else "failed",
        }
        updated = db.update_document(doc["id"], updates)
        doc.update(updated or updates)

        return DocumentOut(**doc)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}",
        )


@router.get("", response_model=List[DocumentOut])
async def list_documents(user_id: str = Depends(get_current_user_id)):
    """Get all documents uploaded by the current user."""
    try:
        docs = db.get_user_documents(user_id)
        return [DocumentOut(**d) for d in docs]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch documents: {str(e)}",
        )


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: str, user_id: str = Depends(get_current_user_id)):
    """Get a specific document's details."""
    try:
        doc = db.get_document_by_id(doc_id)
        if not doc or doc.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Document not found")
        return DocumentOut(**doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch document: {str(e)}",
        )


@router.post("/generate-test", response_model=TestOut)
async def generate_test_from_document(
    request: DocumentTestRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Generate a personalised MCQ test from an uploaded document.
    Uses AI (OpenAI) when available, otherwise returns rule-based placeholder questions.
    """
    try:
        # Fetch the document
        doc = db.get_document_by_id(request.document_id)
        if not doc or doc.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Document not found")

        if doc.get("status") != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document is still processing or failed. Please wait or re-upload.",
            )

        extracted_text = doc.get("extracted_text", "")
        if not extracted_text or extracted_text.startswith("["):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No usable text could be extracted from this document.",
            )

        # Determine subject
        subject = request.subject or doc.get("subject") or ai_service._detect_subject(extracted_text)

        # Generate questions via AI
        questions = await ai_service.generate_test_from_document(
            extracted_text=extracted_text,
            num_questions=request.num_questions,
            difficulty=request.difficulty,
            exam_type=request.exam_type,
            subject=subject,
        )

        if not questions:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate questions from the document.",
            )

        # Calculate total marks
        total_marks = sum(q.get("marks", 4) for q in questions)
        duration = max(15, request.num_questions * 2)  # ~2 min per question

        # Create a test record linked to the document
        test = db.create_test_from_document(
            user_id=user_id,
            document_id=request.document_id,
            title=f"Test from {doc.get('filename', 'Document')}",
            exam_type=request.exam_type,
            duration_minutes=duration,
            total_marks=total_marks,
        )

        # Insert questions linked to the new test
        for q in questions:
            q["test_id"] = test["id"]

        db.bulk_insert_questions(questions)

        test["question_count"] = len(questions)
        return TestOut(**test)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test: {str(e)}",
        )


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, user_id: str = Depends(get_current_user_id)):
    """Delete a user's document."""
    try:
        doc = db.get_document_by_id(doc_id)
        if not doc or doc.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Document not found")

        client = db.get_client()
        client.table("documents").delete().eq("id", doc_id).execute()
        return {"message": "Document deleted", "id": doc_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )
