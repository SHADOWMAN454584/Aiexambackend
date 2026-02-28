"""
Supabase client wrapper for database operations.
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Initialize Supabase client (service role for backend operations)
supabase: Client = create_client(url, key) if url and key else None


def get_client() -> Client:
    """Get the Supabase client instance."""
    if supabase is None:
        raise RuntimeError(
            "Supabase client not initialized. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env"
        )
    return supabase


# ─── Auth / Profiles ──────────────────────────────────────────────

def create_user_auth(email: str, password: str) -> dict:
    """Create a user via Supabase Auth."""
    client = get_client()
    res = client.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
    })
    return {"id": res.user.id, "email": res.user.email}


def sign_in_user(email: str, password: str) -> dict:
    """Sign in a user and return session data."""
    client = get_client()
    res = client.auth.sign_in_with_password({
        "email": email,
        "password": password,
    })
    return {
        "user_id": res.user.id,
        "email": res.user.email,
        "access_token": res.session.access_token,
    }


def create_profile(user_id: str, full_name: str, email: str, exam_target: str = "JEE Main") -> dict:
    """Create a user profile record."""
    client = get_client()
    data = {
        "id": user_id,
        "full_name": full_name,
        "email": email,
        "exam_target": exam_target,
    }
    res = client.table("profiles").insert(data).execute()
    return res.data[0] if res.data else data


def get_user_profile(user_id: str) -> dict:
    """Fetch a user profile by ID."""
    client = get_client()
    res = client.table("profiles").select("*").eq("id", user_id).single().execute()
    return res.data


def update_user_profile(user_id: str, updates: dict) -> dict:
    """Update a user profile."""
    client = get_client()
    updates["updated_at"] = "now()"
    res = client.table("profiles").update(updates).eq("id", user_id).execute()
    return res.data[0] if res.data else {}


# ─── Tests ─────────────────────────────────────────────────────────

def get_all_tests() -> list:
    """Get all available tests."""
    client = get_client()
    res = client.table("tests").select("*, questions(count)").execute()
    tests = []
    for t in res.data:
        t["question_count"] = t.pop("questions", [{}])[0].get("count", 0) if t.get("questions") else 0
        tests.append(t)
    return tests


def get_test_by_id(test_id: str) -> dict:
    """Get a single test by ID."""
    client = get_client()
    res = client.table("tests").select("*").eq("id", test_id).single().execute()
    return res.data


def get_questions_for_test(test_id: str) -> list:
    """Get all questions for a test."""
    client = get_client()
    res = (
        client.table("questions")
        .select("*")
        .eq("test_id", test_id)
        .execute()
    )
    return res.data


# ─── Test Attempts ─────────────────────────────────────────────────

def save_test_attempt(user_id: str, test_id: str, score: int, total_marks: int,
                      percentage: float, time_taken_minutes: int = None) -> dict:
    """Save a test attempt."""
    client = get_client()
    data = {
        "user_id": user_id,
        "test_id": test_id,
        "score": score,
        "total_marks": total_marks,
        "percentage": percentage,
    }
    if time_taken_minutes is not None:
        data["time_taken_minutes"] = time_taken_minutes
    res = client.table("test_attempts").insert(data).execute()
    return res.data[0] if res.data else data


def save_question_responses(attempt_id: str, responses: list) -> list:
    """Save individual question responses for an attempt."""
    client = get_client()
    records = []
    for r in responses:
        records.append({
            "attempt_id": attempt_id,
            "question_id": r["question_id"],
            "selected_option": r.get("selected_option"),
            "is_correct": r.get("is_correct", False),
            "time_spent_seconds": r.get("time_spent_seconds"),
        })
    if records:
        res = client.table("question_responses").insert(records).execute()
        return res.data
    return []


def get_user_attempts(user_id: str, limit: int = 50) -> list:
    """Get all test attempts for a user."""
    client = get_client()
    res = (
        client.table("test_attempts")
        .select("*, tests(title, exam_type)")
        .eq("user_id", user_id)
        .order("submitted_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


def get_attempt_responses(attempt_id: str) -> list:
    """Get all question responses for an attempt."""
    client = get_client()
    res = (
        client.table("question_responses")
        .select("*, questions(subject, topic, difficulty, correct_option, explanation)")
        .eq("attempt_id", attempt_id)
        .execute()
    )
    return res.data


# ─── Analytics ─────────────────────────────────────────────────────

def get_user_responses_with_details(user_id: str) -> list:
    """Get all question responses with question details for a user (for analytics)."""
    client = get_client()
    # Get all attempt IDs for the user
    attempts_res = (
        client.table("test_attempts")
        .select("id")
        .eq("user_id", user_id)
        .execute()
    )
    attempt_ids = [a["id"] for a in attempts_res.data]
    if not attempt_ids:
        return []

    # Get all responses for those attempts
    all_responses = []
    for aid in attempt_ids:
        res = (
            client.table("question_responses")
            .select("*, questions(subject, topic, difficulty, correct_option, marks, negative_marks)")
            .eq("attempt_id", aid)
            .execute()
        )
        all_responses.extend(res.data)
    return all_responses


def get_weekly_progress(user_id: str, limit: int = 12) -> list:
    """Get weekly progress snapshots for a user."""
    client = get_client()
    res = (
        client.table("weekly_progress")
        .select("*")
        .eq("user_id", user_id)
        .order("week_start", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


def upsert_weekly_progress(data: dict) -> dict:
    """Insert or update a weekly progress record."""
    client = get_client()
    res = client.table("weekly_progress").upsert(data).execute()
    return res.data[0] if res.data else data


# ─── Recommendations ──────────────────────────────────────────────

def get_recommendations(user_id: str, include_completed: bool = False) -> list:
    """Get AI recommendations for a user."""
    client = get_client()
    query = client.table("recommendations").select("*").eq("user_id", user_id)
    if not include_completed:
        query = query.eq("is_completed", False)
    res = query.order("created_at", desc=True).execute()
    return res.data


def save_recommendations(recommendations: list) -> list:
    """Save a batch of recommendations."""
    client = get_client()
    if recommendations:
        res = client.table("recommendations").insert(recommendations).execute()
        return res.data
    return []


def mark_recommendation_complete(rec_id: str, user_id: str) -> dict:
    """Mark a recommendation as completed."""
    client = get_client()
    res = (
        client.table("recommendations")
        .update({"is_completed": True})
        .eq("id", rec_id)
        .eq("user_id", user_id)
        .execute()
    )
    return res.data[0] if res.data else {}


# ─── Scanned Papers ───────────────────────────────────────────────

def save_scanned_paper(user_id: str, exam_type: str, year: int = None,
                       image_url: str = None) -> dict:
    """Save a scanned paper record."""
    client = get_client()
    data = {
        "user_id": user_id,
        "exam_type": exam_type,
        "status": "processing",
    }
    if year:
        data["year"] = year
    if image_url:
        data["image_url"] = image_url
    res = client.table("scanned_papers").insert(data).execute()
    return res.data[0] if res.data else data


def update_scanned_paper(paper_id: str, updates: dict) -> dict:
    """Update a scanned paper status/results."""
    client = get_client()
    res = client.table("scanned_papers").update(updates).eq("id", paper_id).execute()
    return res.data[0] if res.data else {}


def get_user_scanned_papers(user_id: str) -> list:
    """Get all scanned papers for a user."""
    client = get_client()
    res = (
        client.table("scanned_papers")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


def upload_file_to_storage(bucket: str, path: str, file_bytes: bytes, content_type: str = "image/png") -> str:
    """Upload a file to Supabase Storage and return the public URL."""
    client = get_client()
    client.storage.from_(bucket).upload(path, file_bytes, {"content-type": content_type})
    return client.storage.from_(bucket).get_public_url(path)


# ─── Documents ─────────────────────────────────────────────────────

def save_document(user_id: str, filename: str, mime_type: str, file_size: int = 0,
                  file_url: str = None, exam_type: str = "JEE Main",
                  subject: str = None) -> dict:
    """Save a document record."""
    client = get_client()
    data = {
        "user_id": user_id,
        "filename": filename,
        "mime_type": mime_type,
        "file_size": file_size,
        "exam_type": exam_type,
        "status": "processing",
    }
    if file_url:
        data["file_url"] = file_url
    if subject:
        data["subject"] = subject
    res = client.table("documents").insert(data).execute()
    return res.data[0] if res.data else data


def update_document(doc_id: str, updates: dict) -> dict:
    """Update a document record."""
    client = get_client()
    res = client.table("documents").update(updates).eq("id", doc_id).execute()
    return res.data[0] if res.data else {}


def get_document_by_id(doc_id: str) -> dict:
    """Fetch a single document by ID."""
    client = get_client()
    res = client.table("documents").select("*").eq("id", doc_id).single().execute()
    return res.data


def get_user_documents(user_id: str) -> list:
    """Get all documents for a user."""
    client = get_client()
    res = (
        client.table("documents")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


def create_test_from_document(user_id: str, document_id: str, title: str,
                              exam_type: str = "JEE Main", duration_minutes: int = 60,
                              total_marks: int = 40) -> dict:
    """Create a test record linked to a document."""
    client = get_client()
    data = {
        "title": title,
        "description": f"AI-generated test from uploaded document",
        "exam_type": exam_type,
        "duration_minutes": duration_minutes,
        "total_marks": total_marks,
        "document_id": document_id,
        "is_ai_generated": True,
    }
    res = client.table("tests").insert(data).execute()
    return res.data[0] if res.data else data


def bulk_insert_questions(questions: list) -> list:
    """Insert multiple questions at once."""
    client = get_client()
    if questions:
        res = client.table("questions").insert(questions).execute()
        return res.data
    return []
