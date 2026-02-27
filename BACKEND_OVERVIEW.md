# ExamAI Backend — Full Technical Overview

## Table of Contents

1. [Project Summary](#1-project-summary)
2. [Technology Stack](#2-technology-stack)
3. [Architecture Overview](#3-architecture-overview)
4. [Project Structure](#4-project-structure)
5. [Environment & Configuration](#5-environment--configuration)
6. [Entry Point — main.py](#6-entry-point--mainpy)
7. [Routers (API Layer)](#7-routers-api-layer)
   - 7.1 [Auth Router](#71-auth-router--apiauthpy)
   - 7.2 [Tests Router](#72-tests-router--apitestspy)
   - 7.3 [Analytics Router](#73-analytics-router--apianalyticspy)
   - 7.4 [Recommendations Router](#74-recommendations-router--apirecommendationspy)
   - 7.5 [OCR Router](#75-ocr-router--apiocrpy)
8. [Services (Business Logic Layer)](#8-services-business-logic-layer)
   - 8.1 [Supabase Service](#81-supabase-service)
   - 8.2 [AI Service](#82-ai-service)
   - 8.3 [OCR Service](#83-ocr-service)
9. [Models (Pydantic Schemas)](#9-models-pydantic-schemas)
10. [Utilities](#10-utilities)
11. [Database Schema](#11-database-schema)
12. [Authentication & Security](#12-authentication--security)
13. [Complete API Endpoint Reference](#13-complete-api-endpoint-reference)
14. [Test Scoring Logic](#14-test-scoring-logic)
15. [AI & Recommendation Engine](#15-ai--recommendation-engine)
16. [OCR Pipeline](#16-ocr-pipeline)
17. [Docker & Deployment](#17-docker--deployment)
18. [Dependencies](#18-dependencies)
19. [Production Checklist](#19-production-checklist)

---

## 1. Project Summary

**ExamAI Backend** is a RESTful API built with **FastAPI (Python)** that powers an AI-driven competitive exam preparation platform. It is designed for students preparing for exams such as **JEE Main, JEE Advanced, NEET**, and similar competitive tests.

### Core Capabilities

| Feature | Description |
|---|---|
| User Auth | Registration, login, and profile management via Supabase Auth + custom JWT |
| Test Engine | Serve MCQ tests, grade submissions with ±marks logic, persist results |
| Analytics | Per-user performance overview, subject-level breakdown, weekly trend tracking |
| AI Recommendations | Rule-based + optional OpenAI-powered study recommendations |
| OCR Scanning | Upload PYQ (Previous Year Question) paper images; extract & parse questions via Tesseract |

---

## 2. Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Web Framework | FastAPI | 0.133.1 |
| ASGI Server | Uvicorn | latest |
| Data Validation | Pydantic | 2.12.5 |
| Database | Supabase (PostgreSQL) | — |
| Auth | Supabase Auth + PyJWT / python-jose | 2.11.0 / 3.5.0 |
| Password Hashing | Passlib + bcrypt | 1.7.4 / 5.0.0 |
| AI (optional) | OpenAI API | — |
| OCR | Pytesseract + Tesseract 5.x | 0.3.13 |
| Image Processing | Pillow | 12.1.1 |
| HTTP Client | HTTPX | 0.28.1 |
| Containerisation | Docker (multi-stage) | 24+ |
| Runtime | Python | 3.11+ |

---

## 3. Architecture Overview

```
Flutter App (Client)
        │
        │  HTTPS / REST (JSON)
        ▼
┌───────────────────────────────────────────────┐
│              FastAPI Application               │
│                                               │
│  ┌──────────┐  ┌────────┐  ┌──────────────┐  │
│  │  /auth   │  │/tests  │  │ /analytics   │  │
│  │  /ocr    │  │        │  │/recommend.   │  │
│  └──────────┘  └────────┘  └──────────────┘  │
│         │            │            │           │
│         └────────────┴────────────┘           │
│                      │                        │
│          ┌───────────┴────────────┐           │
│          │        Services        │           │
│          │  supabase_service.py   │           │
│          │  ai_service.py         │           │
│          │  ocr_service.py        │           │
│          └───────────┬────────────┘           │
└──────────────────────┼────────────────────────┘
                       │
          ┌────────────┴──────────┐
          │       Supabase        │
          │  PostgreSQL · Auth    │
          │  Storage (images)     │
          └───────────────────────┘
```

---

## 4. Project Structure

```
Aiexambackend/
├── main.py                    # FastAPI app entry point, CORS, router registration
├── Dockerfile                 # Multi-stage Docker build (builder + production)
├── requirements.txt           # All pinned Python dependencies
├── database.sql               # SQL schema / seed scripts for Supabase
├── STEPS.md                   # Setup & deployment guide
│
├── models/                    # Pydantic request/response schemas
│   ├── __init__.py
│   ├── user.py                # UserRegister, UserLogin, UserProfile, TokenResponse
│   ├── test.py                # TestOut, TestSubmission, TestResultDetail, Question
│   └── analytics.py           # OverviewAnalytics, SubjectAnalytics, WeeklyProgressOut,
│                              #   RecommendationOut, ScannedPaperOut
│
├── routers/                   # Route handlers (thin controllers)
│   ├── __init__.py
│   ├── auth.py                # /api/auth/*
│   ├── tests.py               # /api/tests/*
│   ├── analytics.py           # /api/analytics/*
│   ├── recommendations.py     # /api/recommendations/*
│   └── ocr.py                 # /api/ocr/*
│
├── services/                  # Business logic & third-party integrations
│   ├── __init__.py
│   ├── supabase_service.py    # All Supabase DB + Auth + Storage calls
│   ├── ai_service.py          # Performance analysis + recommendation engine (+ OpenAI)
│   └── ocr_service.py         # Image-to-text extraction and question parsing
│
└── utils/
    ├── __init__.py
    └── helpers.py             # JWT creation/decoding, password hashing, math helpers
```

---

## 5. Environment & Configuration

The app is configured entirely through environment variables (loaded with `python-dotenv`).

| Variable | Required | Default | Description |
|---|---|---|---|
| `SUPABASE_URL` | Yes | — | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | — | Service role key (bypasses RLS) |
| `SECRET_KEY` | Yes | `default-secret-key-change-in-production` | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` (24 h) | JWT token lifetime |
| `OPENAI_API_KEY` | No | — | Enable AI-enhanced recommendations |

Create a `.env` file at the project root with these values before running the server.

---

## 6. Entry Point — `main.py`

```
FastAPI app (title: "ExamAI Backend", version: 1.0.0)
  ├── CORS middleware — allow_origins=["*"] (restrict in production)
  ├── GET  /          → {"message": "ExamAI API is running"}
  ├── GET  /health    → {"status": "healthy", "version": "1.0.0"}
  ├── Router: auth         prefix=/api/auth
  ├── Router: tests        prefix=/api/tests
  ├── Router: analytics    prefix=/api/analytics
  ├── Router: recommendations prefix=/api/recommendations
  └── Router: ocr          prefix=/api/ocr
```

Interactive documentation is auto-generated at:
- Swagger UI → `http://localhost:8000/docs`
- ReDoc      → `http://localhost:8000/redoc`

---

## 7. Routers (API Layer)

All protected routes use `Depends(get_current_user_id)` which validates the `Authorization: Bearer <token>` header and extracts `user_id` from the JWT payload.

---

### 7.1 Auth Router — `routers/auth.py`

**Prefix:** `/api/auth` | **Tag:** `Auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | Public | Create account → returns JWT + profile |
| POST | `/login` | Public | Sign in → returns JWT + profile |
| GET | `/profile` | Required | Get current user's profile |
| PUT | `/profile` | Required | Update name / avatar / exam target |

**Registration flow:**
1. Create user in Supabase Auth (`admin.create_user` with `email_confirm: true`)
2. Insert a row in the `profiles` table with `id`, `full_name`, `email`, `exam_target`
3. Sign and return a custom JWT (`sub` = user UUID)

**Login flow:**
1. Sign in via Supabase `sign_in_with_password`
2. Fetch the user's `profiles` row
3. Issue a custom JWT

**Error handling:**
- `409 Conflict` — email already exists on register
- `401 Unauthorized` — wrong credentials on login
- `400 Bad Request` — any other registration/login failure

---

### 7.2 Tests Router — `routers/tests.py`

**Prefix:** `/api/tests` | **Tag:** `Tests`

| Method | Path | Description |
|---|---|---|
| GET | `/` | List all available tests (with question count) |
| GET | `/{test_id}` | Get a specific test's metadata |
| GET | `/{test_id}/questions` | Get questions — **correct_option and explanation are stripped** |
| POST | `/submit` | Submit answers, grade, persist attempt + responses |
| GET | `/attempts/history` | All past attempts for the user |
| GET | `/attempts/{attempt_id}/detail` | Full result with per-question breakdown |

**Submission & Grading Logic:**

```
For each response in submission:
  ┌─ selected_option == None    → marks_earned = 0          (skipped)
  ├─ selected_option == correct → marks_earned = +4          (default, from DB)
  └─ selected_option != correct → marks_earned = -1          (negative marking)

score     = sum of marks_earned  (can be negative)
total_marks = sum of max marks per question
percentage  = max(score, 0) / total_marks × 100
```

Subject-level breakdown (correct / incorrect / skipped / marks) is computed per subject and returned in `TestResultDetail`. The full graded response list (with `correct_option` + `explanation` revealed) is also returned.

---

### 7.3 Analytics Router — `routers/analytics.py`

**Prefix:** `/api/analytics` | **Tag:** `Analytics`

| Method | Path | Description |
|---|---|---|
| GET | `/overview` | Aggregate stats across all attempts |
| GET | `/subject/{subject}` | Deep analytics for one subject |
| GET | `/progress` | Weekly progress trend |
| GET | `/prediction` | AI score prediction |

**Overview Analytics fields:**
- `total_tests_taken`, `average_score`, `best_score`, `total_time_spent_minutes`
- `accuracy_percentage`, `total_questions_attempted`
- `correct_answers`, `incorrect_answers`, `skipped_questions`
- `subject_performance` — dict of `{subject: accuracy%}`

**Subject Analytics fields:**
- `total_questions`, `correct`, `incorrect`, `skipped`, `accuracy`
- `average_time_per_question`
- `topic_breakdown` — list sorted by ascending accuracy (weakest topics first)
- `difficulty_breakdown` — stats split by Easy / Medium / Hard

---

### 7.4 Recommendations Router — `routers/recommendations.py`

**Prefix:** `/api/recommendations` | **Tag:** `Recommendations`

| Method | Path | Description |
|---|---|---|
| GET | `/` | Return cached recommendations or generate new ones |
| POST | `/refresh` | Force-regenerate recommendations from latest data |
| PUT | `/{rec_id}/complete` | Mark a recommendation as completed |

**Generation flow:**
1. Check DB for existing (un-completed) recommendations
2. If none, fetch all question responses with question details
3. Call `ai_service.analyze_performance()` → weakness analysis
4. Call `ai_service.generate_recommendations_with_ai()` → if `OPENAI_API_KEY` set, uses GPT; otherwise falls back to rule-based engine
5. Persist to `recommendations` table and return

---

### 7.5 OCR Router — `routers/ocr.py`

**Prefix:** `/api/ocr` | **Tag:** `OCR`

| Method | Path | Description |
|---|---|---|
| POST | `/scan` | Upload image, run OCR, save results |
| GET | `/papers` | List all scanned papers for the user |
| GET | `/papers/{paper_id}` | Get paper detail + re-parsed questions |

**Scan flow:**
1. Validate MIME type (PNG / JPEG / WebP / BMP only)
2. Enforce 10 MB file size limit
3. Upload image to Supabase Storage bucket `pyq-scans` (optional — non-fatal)
4. Create a `scanned_papers` DB record with status `processing`
5. Run `ocr_service.process_scanned_image()` → extract text + parse questions
6. Update DB record with `extracted_text`, `questions_extracted`, `status: completed`

---

## 8. Services (Business Logic Layer)

### 8.1 Supabase Service

**File:** `services/supabase_service.py`

Single source of truth for all database and auth operations. Uses the **service role key** (bypasses Row Level Security) so all queries run as superuser.

| Function Group | Functions |
|---|---|
| Auth / Profiles | `create_user_auth`, `sign_in_user`, `create_profile`, `get_user_profile`, `update_user_profile` |
| Tests | `get_all_tests`, `get_test_by_id`, `get_questions_for_test` |
| Attempts | `save_test_attempt`, `save_question_responses`, `get_user_attempts`, `get_attempt_detail` |
| Analytics | `get_user_responses_with_details`, `get_weekly_progress`, `save_weekly_progress` |
| Recommendations | `get_recommendations`, `save_recommendations`, `mark_recommendation_complete` |
| OCR | `save_scanned_paper`, `update_scanned_paper`, `get_user_scanned_papers` |
| Storage | `upload_file_to_storage` |

The client is initialized once at module level:
```python
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
```
If either env var is missing, the client is `None` and `get_client()` raises a `RuntimeError`.

---

### 8.2 AI Service

**File:** `services/ai_service.py`

Dual-mode engine: **rule-based** (always available) + **OpenAI-enhanced** (requires `OPENAI_API_KEY`).

#### `analyze_performance(responses)` → `dict`

Processes all of a user's `question_responses` (joined with question metadata) into:

```
{
  "total_questions": int,
  "overall_accuracy": float,          # percentage
  "subjects": {
    "<subject>": {
      "total": int, "correct": int, "incorrect": int, "skipped": int,
      "accuracy": float,
      "difficulty_breakdown": { "Easy"|"Medium"|"Hard": {...} }
    }
  },
  "weak_topics": [...],               # accuracy < 50%, sorted ascending
  "strong_topics": [...]              # accuracy >= 80%, sorted descending
}
```

A topic must have at least **2 questions** to be classified as weak or strong.

#### `generate_recommendations(user_id, performance)` → `list[dict]`

Rule-based recommendation generator (4 priority tiers):

| Priority | Trigger | Recommendation Type |
|---|---|---|
| 1 — Urgent | Topic accuracy < 50% | Practice specific weak topic |
| 2 — High | Subject accuracy < 50% (≥5 questions) | Revise subject fundamentals |
| 3 — Medium | Hard-question accuracy < 40% (≥3 hard Qs) | Practice hard problems |
| 4 — General | Overall accuracy < 60% | Take a full mock test |

If overall accuracy ≥ 80% with no weak topics, a "keep it up" encouragement is generated instead.

#### `generate_recommendations_with_ai(user_id, performance)` → `list[dict]` (async)

- If `OPENAI_API_KEY` is set: calls OpenAI Chat API with a structured prompt; parses JSON response
- Falls back to `generate_recommendations()` on any failure / if key absent

---

### 8.3 OCR Service

**File:** `services/ocr_service.py`

Built on **Tesseract 5** via `pytesseract`. Gracefully degrades — if Tesseract is not installed, returns a placeholder message rather than crashing.

#### `extract_text_from_image(image_bytes)` → `str`

1. Opens image with Pillow
2. Converts to **grayscale** (improves OCR accuracy on printed text)
3. Runs `pytesseract.image_to_string()` with `lang="eng"`

#### `parse_questions_from_text(text)` → `list[dict]`

Regex-based parser that:
1. Splits text on question markers: `Q1.`, `Q.1`, `1.`, `Question 1:`
2. Within each chunk, finds option markers: `(A)` / `A)` / `(a)` through D
3. Extracts question stem (text before first option) and all options into a structured dict

Returns:
```python
[
  {
    "question_number": int,
    "raw_text": str,
    "question_text": str,
    "options": {"A": str, "B": str, "C": str, "D": str}
  },
  ...
]
```

#### `process_scanned_image(image_bytes)` → `dict`

Full pipeline combining both functions above:
```python
{
  "extracted_text": str,
  "questions": list,
  "questions_extracted": int,
  "status": "completed" | "completed_no_questions"
}
```

---

## 9. Models (Pydantic Schemas)

### `models/user.py`

| Model | Purpose |
|---|---|
| `UserRegister` | POST /register body — `email`, `password` (min 6), `full_name` (min 2), `exam_target` |
| `UserLogin` | POST /login body — `email`, `password` |
| `UserProfile` | Response — `id`, `full_name`, `email`, `avatar_url`, `exam_target`, `created_at` |
| `UserProfileUpdate` | PUT /profile body — all fields optional |
| `TokenResponse` | Login/register response — `access_token`, `token_type`, `user: UserProfile` |

### `models/test.py`

| Model | Purpose |
|---|---|
| `TestOut` | Test listing — `id`, `title`, `subject`, `total_questions`, `duration_minutes`, `difficulty` |
| `Question` | Question object (sanitized — no `correct_option` during active test) |
| `QuestionResponse` | Single answer in a submission — `question_id`, `selected_option`, `time_spent_seconds` |
| `TestSubmission` | POST /submit body — `test_id`, `responses[]`, `time_taken_minutes` |
| `TestResultDetail` | Graded result — score, percentage, `subject_breakdown`, `responses[]` with explanations |
| `TestAttemptOut` | History item — `id`, `test_id`, `score`, `percentage`, `created_at` |

### `models/analytics.py`

| Model | Purpose |
|---|---|
| `OverviewAnalytics` | Dashboard stats — totals, averages, accuracy, `subject_performance` dict |
| `SubjectAnalytics` | Per-subject deep dive — `topic_breakdown[]`, `difficulty_breakdown{}` |
| `WeeklyProgressOut` | One week's stats — `week_start`, `tests_taken`, `avg_score`, subject averages |
| `ProgressTrend` | List of `WeeklyProgressOut` + `overall_trend` string |
| `RecommendationOut` | Recommendation card — `title`, `description`, `subject`, `priority`, `type`, `estimated_time`, `is_completed` |
| `ScannedPaperOut` | OCR scan record — `exam_type`, `year`, `image_url`, `extracted_text`, `questions_extracted`, `status` |

---

## 10. Utilities

**File:** `utils/helpers.py`

| Function | Description |
|---|---|
| `hash_password(password)` | bcrypt hash via passlib |
| `verify_password(plain, hashed)` | bcrypt compare |
| `create_access_token(data, expires_delta)` | HS256 JWT with `exp` claim |
| `decode_access_token(token)` | Validates + decodes JWT; raises `401` on failure |
| `get_current_user_id(credentials)` | FastAPI dependency — extracts `sub` from bearer token |
| `calculate_percentage(score, total)` | Safe division → float percentage |
| `get_week_start(dt)` | Returns ISO date string of the Monday of the given datetime |
| `format_duration(minutes)` | `90` → `"1h 30m"`, `45` → `"45m"` |

---

## 11. Database Schema

All tables reside in a **Supabase (PostgreSQL)** project.

| Table | Key Columns |
|---|---|
| `profiles` | `id` (uuid, FK → auth.users), `full_name`, `email`, `exam_target`, `avatar_url`, `created_at`, `updated_at` |
| `tests` | `id`, `title`, `subject`, `total_questions`, `duration_minutes`, `difficulty` |
| `questions` | `id`, `test_id` (FK), `question_text`, `options` (jsonb), `correct_option`, `topic`, `subject`, `difficulty`, `marks`, `negative_marks`, `explanation` |
| `test_attempts` | `id`, `user_id` (FK), `test_id` (FK), `score`, `total_marks`, `percentage`, `time_taken_minutes`, `created_at` |
| `question_responses` | `id`, `attempt_id` (FK), `question_id` (FK), `selected_option`, `is_correct`, `time_spent_seconds` |
| `weekly_progress` | `id`, `user_id`, `week_start`, `tests_taken`, `avg_score`, `study_hours`, `physics_avg`, `chemistry_avg`, `maths_avg`, `biology_avg` |
| `recommendations` | `id`, `user_id`, `title`, `description`, `subject`, `priority`, `type`, `estimated_time`, `is_completed`, `created_at` |
| `scanned_papers` | `id`, `user_id`, `exam_type`, `year`, `image_url`, `extracted_text`, `questions_extracted`, `status`, `created_at` |

**Storage bucket:** `pyq-scans` (public) — stores uploaded PYQ images at path `{user_id}/{uuid}.{ext}`.

---

## 12. Authentication & Security

### JWT Flow

```
Client                          Backend
  │                                │
  │── POST /api/auth/login ────────►│
  │                                │── Supabase sign_in_with_password
  │                                │── create_access_token({sub: user_id, email})
  │◄── { access_token, user } ─────│
  │                                │
  │── GET /api/analytics/overview ─►│
  │   Authorization: Bearer <token>│
  │                                │── get_current_user_id(credentials)
  │                                │   └─ decode JWT → extract sub
  │◄── OverviewAnalytics ──────────│
```

- Algorithm: **HS256**
- Default expiry: **1440 minutes (24 hours)**
- Token payload: `{ "sub": "<user_uuid>", "email": "<email>", "exp": <timestamp> }`

### Security Notes

- The backend uses **service role key** (admin access) — keep it secret and never expose to clients.
- Passwords are hashed via **bcrypt** (passlib) with auto-upgrade of deprecated hashes.
- CORS is currently permissive (`allow_origins=["*"]`) — restrict to production domain.
- Supabase RLS is recommended on all tables in production (backend bypasses it via service role).

---

## 13. Complete API Endpoint Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Liveness check — `{"message": "ExamAI API is running"}` |
| GET | `/health` | No | Health check — `{"status": "healthy", "version": "1.0.0"}` |
| **Auth** | | | |
| POST | `/api/auth/register` | No | Register new user; returns `TokenResponse` |
| POST | `/api/auth/login` | No | Login; returns `TokenResponse` |
| GET | `/api/auth/profile` | Yes | Get `UserProfile` |
| PUT | `/api/auth/profile` | Yes | Update profile fields |
| **Tests** | | | |
| GET | `/api/tests/` | Yes | List all `TestOut[]` |
| GET | `/api/tests/{test_id}` | Yes | Single `TestOut` |
| GET | `/api/tests/{test_id}/questions` | Yes | `Question[]` (answers redacted) |
| POST | `/api/tests/submit` | Yes | Submit `TestSubmission`; returns `TestResultDetail` |
| GET | `/api/tests/attempts/history` | Yes | `TestAttemptOut[]` |
| GET | `/api/tests/attempts/{attempt_id}/detail` | Yes | Full `TestResultDetail` |
| **Analytics** | | | |
| GET | `/api/analytics/overview` | Yes | `OverviewAnalytics` |
| GET | `/api/analytics/subject/{subject}` | Yes | `SubjectAnalytics` |
| GET | `/api/analytics/progress` | Yes | `ProgressTrend` |
| GET | `/api/analytics/prediction` | Yes | AI score prediction (AI-generated) |
| **Recommendations** | | | |
| GET | `/api/recommendations/` | Yes | `RecommendationOut[]` |
| POST | `/api/recommendations/refresh` | Yes | Force-regenerate recommendations |
| PUT | `/api/recommendations/{rec_id}/complete` | Yes | Mark recommendation done |
| **OCR** | | | |
| POST | `/api/ocr/scan` | Yes | Upload image; returns `ScannedPaperOut` |
| GET | `/api/ocr/papers` | Yes | `ScannedPaperOut[]` |
| GET | `/api/ocr/papers/{paper_id}` | Yes | `{paper, parsed_questions}` |

---

## 14. Test Scoring Logic

The platform uses the standard **JEE-style marking scheme** (configurable per question):

```
+4  for a correct answer        (question.marks, default 4)
−1  for a wrong answer          (question.negative_marks, default 1)
 0  if the question is skipped
```

- `score` can go negative (sum of all `marks_earned`)
- `total_marks` = sum of `question.marks` for all questions in the test
- `percentage` = `max(score, 0) / total_marks × 100` (floored at 0 for display)

The graded response saved to `question_responses` includes `is_correct`, `selected_option`, and `time_spent_seconds` — all used later in analytics.

---

## 15. AI & Recommendation Engine

### Performance Analysis Pipeline

```
question_responses (with joined question metadata)
        │
        ▼
  analyze_performance()
        │
        ├── Per-subject tallies (total / correct / incorrect / skipped)
        ├── Per-topic tallies   (min 2 questions to classify)
        ├── Per-difficulty breakdown (Easy / Medium / Hard)
        │
        ▼
  {
    overall_accuracy,
    subjects: { "<subject>": { accuracy, difficulty_breakdown } },
    weak_topics:   [ topics with accuracy < 50% ]  ← sorted worst first
    strong_topics: [ topics with accuracy ≥ 80% ]  ← sorted best first
  }
```

### Recommendation Priority Tiers

```
Tier 1 — Weak Topic Practice      (High/Medium priority, 30 mins)
Tier 2 — Subject Fundamentals     (High priority, 1 hour)
Tier 3 — Hard Question Drilling   (Medium priority, 45 mins)
Tier 4 — Full Mock Test           (Medium priority, 3 hours)
Tier 5 — Encouragement            (Low, only when overall accuracy ≥ 80%)
```

### OpenAI Integration

When `OPENAI_API_KEY` is present, the engine sends a structured prompt to the Chat API asking for JSON-formatted recommendations tailored to the user's specific performance data. On any API error or parse failure, it seamlessly falls back to the rule-based engine.

---

## 16. OCR Pipeline

```
Client uploads image
        │
        ▼
  Validate MIME type (PNG / JPEG / WebP / BMP)
  Validate size ≤ 10 MB
        │
        ▼
  Upload to Supabase Storage → pyq-scans/{user_id}/{uuid}.{ext}
        │
        ▼
  Save DB record (status: "processing")
        │
        ▼
  PIL.Image.open() → convert to grayscale
        │
        ▼
  pytesseract.image_to_string(lang="eng")
        │
        ▼
  parse_questions_from_text()
    ├── Regex split on question markers (Q1., 1., Question 1:)
    └── Regex extract options (A) / (a) ... (D) / (d)
        │
        ▼
  Update DB record:
    extracted_text, questions_extracted, status: "completed"
        │
        ▼
  Return ScannedPaperOut to client
```

**Graceful degradation:** If Tesseract is not installed, `TESSERACT_AVAILABLE = False` and a placeholder string is returned — the app continues to function without crashing.

---

## 17. Docker & Deployment

### Multi-Stage Dockerfile

**Stage 1 (builder):** Installs all Python packages into `/install` using `python:3.11-slim`.

**Stage 2 (production):**
- Base: `python:3.11-slim`
- Installs `tesseract-ocr` via `apt-get`
- Copies pre-built packages from builder (keeps image lean)
- Creates a non-root user `appuser:appgroup` for security
- Exposes port `8000`
- Health check polls `/health` every 30 seconds

```bash
# Build
docker build -t examai-backend .

# Run
docker run -d \
  --name examai-backend \
  -p 8000:8000 \
  --env-file .env \
  examai-backend

# Verify
curl http://localhost:8000/health
# → {"status":"healthy","version":"1.0.0"}
```

### Local Development

```bash
python -m venv venv
venv\Scripts\activate           # Windows
pip install -r requirements.txt
cp .env.example .env            # fill in your values
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 18. Dependencies

Key packages from `requirements.txt`:

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.133.1 | Web framework |
| `uvicorn` | — | ASGI server |
| `pydantic` | 2.12.5 | Data validation & serialisation |
| `supabase` + `postgrest` | latest | Supabase Python client |
| `python-jose` | 3.5.0 | JWT encode/decode |
| `PyJWT` | 2.11.0 | JWT utilities |
| `passlib` | 1.7.4 | Password hashing (bcrypt) |
| `bcrypt` | 5.0.0 | bcrypt algorithm |
| `pytesseract` | 0.3.13 | Tesseract OCR wrapper |
| `pillow` | 12.1.1 | Image processing |
| `httpx` | 0.28.1 | Async HTTP client |
| `python-dotenv` | 1.2.1 | `.env` file loader |
| `python-multipart` | 0.0.22 | File upload support |
| `openai` | — | Optional GPT integration |

---

## 19. Production Checklist

- [ ] Set a strong, unique `SECRET_KEY` in `.env` (never use the default)
- [ ] Restrict `allow_origins` in CORS middleware to your Flutter app's domain
- [ ] Enable **Row Level Security (RLS)** on all Supabase tables
- [ ] Set `--workers` in Docker `CMD` to match your server's CPU count
- [ ] Put the API behind HTTPS (Nginx / Caddy / cloud load balancer)
- [ ] Add structured logging (`loguru` or Python `logging`)
- [ ] Monitor the `/health` endpoint with an uptime service
- [ ] Pin Docker base image by digest for reproducible builds
- [ ] Run `pip audit` to check for known CVEs in dependencies
- [ ] Rotate `SUPABASE_SERVICE_ROLE_KEY` if it is ever exposed
- [ ] Set `ACCESS_TOKEN_EXPIRE_MINUTES` to an appropriate short value in production
