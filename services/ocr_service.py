"""
OCR processing service for scanning PYQ papers.
Uses Pytesseract (Tesseract OCR) for text extraction from images.
"""
import io
import re
from typing import List, Dict, Optional

from PIL import Image

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Extract text from an image using Tesseract OCR.
    Falls back to a placeholder if Tesseract is not installed.
    """
    if not TESSERACT_AVAILABLE:
        return "[OCR] Tesseract not available. Install Tesseract OCR to enable image scanning."

    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Pre-process: convert to grayscale for better OCR accuracy
        image = image.convert("L")
        text = pytesseract.image_to_string(image, lang="eng")
        return text.strip()
    except Exception as e:
        return f"[OCR Error] Could not process image: {str(e)}"


def parse_questions_from_text(text: str) -> List[Dict]:
    """
    Attempt to parse structured questions from OCR-extracted text.
    Looks for patterns like:
      Q1. / 1. / Question 1:
      (A) / (a) / A) / a)
    """
    questions = []

    # Split by question markers
    # Matches patterns like: Q1., Q.1, 1., Question 1, etc.
    question_pattern = r'(?:Q\.?\s*\d+\.?|Question\s*\d+\.?:?|\d+\.\s)'
    parts = re.split(question_pattern, text, flags=re.IGNORECASE)

    for i, part in enumerate(parts):
        part = part.strip()
        if not part or len(part) < 10:
            continue

        question_data = {
            "question_number": i,
            "raw_text": part,
            "question_text": "",
            "options": {},
        }

        # Try to extract options
        option_pattern = r'\(?([A-Da-d])\)?\s*\.?\s*(.+?)(?=\(?[A-Da-d]\)|\Z)'
        option_matches = re.findall(option_pattern, part, re.DOTALL)

        if option_matches:
            # Text before first option is the question
            first_option_match = re.search(r'\(?[A-Da-d]\)', part)
            if first_option_match:
                question_data["question_text"] = part[:first_option_match.start()].strip()

            for opt_letter, opt_text in option_matches:
                question_data["options"][opt_letter.upper()] = opt_text.strip()
        else:
            question_data["question_text"] = part

        if question_data["question_text"]:
            questions.append(question_data)

    return questions


def process_scanned_image(image_bytes: bytes) -> Dict:
    """
    Full pipeline: extract text from image and parse questions.
    Returns extracted text, parsed questions, and count.
    """
    extracted_text = extract_text_from_image(image_bytes)
    questions = parse_questions_from_text(extracted_text)

    return {
        "extracted_text": extracted_text,
        "questions": questions,
        "questions_extracted": len(questions),
        "status": "completed" if questions else "completed_no_questions",
    }
