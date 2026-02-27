# ExamAI Backend — Setup & Deployment Steps

## Prerequisites

| Tool       | Version   | Purpose                                       |
|------------|-----------|-----------------------------------------------|
| Python     | 3.11+     | Runtime for FastAPI backend                    |
| pip        | latest    | Python package manager                         |
| Tesseract  | 5.x       | OCR engine (scanned-paper processing)          |
| Docker     | 24+       | Containerised deployment                       |
| Supabase   | —         | Cloud Postgres DB + Auth + Storage             |
| OpenAI Key | (optional)| AI-powered study recommendations               |

---

## 1 — Local Development Setup

### 1.1 Clone the repository
```bash
git clone <repo-url>
cd Aiexambackend
```

### 1.2 Create & activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 1.3 Install dependencies
```bash
pip install -r requirements.txt
```

### 1.4 Install Tesseract OCR (local only — Docker image includes it)
- **Windows:** Download installer from https://github.com/UB-Mannheim/tesseract/wiki  
  Add the install path (e.g. `C:\Program Files\Tesseract-OCR`) to your system PATH.
- **macOS:** `brew install tesseract`
- **Ubuntu/Debian:** `sudo apt-get install tesseract-ocr`

### 1.5 Configure environment variables
```bash
cp .env.example .env
# Open .env and fill in your real values:
#   SUPABASE_URL
#   SUPABASE_SERVICE_ROLE_KEY
#   SECRET_KEY
#   ACCESS_TOKEN_EXPIRE_MINUTES  (default 1440 = 24 hours)
#   OPENAI_API_KEY               (optional)
```

### 1.6 Run the development server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
API docs will be available at:
- Swagger UI → `http://localhost:8000/docs`
- ReDoc     → `http://localhost:8000/redoc`

---

## 2 — Supabase Configuration

### 2.1 Create a Supabase project
1. Go to https://supabase.com and create a new project.
2. Copy your **Project URL** and **Service Role Key** from  
   *Settings → API*.

### 2.2 Database tables required

Create the following tables (via SQL editor or Supabase dashboard):

| Table               | Key Columns                                                               |
|---------------------|---------------------------------------------------------------------------|
| `profiles`          | id (uuid, FK → auth.users), full_name, email, target_exam, study_hours   |
| `tests`             | id, title, subject, total_questions, duration_minutes, difficulty         |
| `questions`         | id, test_id (FK), question_text, options (jsonb), correct_option, topic   |
| `test_attempts`     | id, user_id (FK), test_id (FK), score, total, percentage, time_taken     |
| `question_responses`| id, attempt_id (FK), question_id (FK), selected_option, is_correct       |
| `weekly_progress`   | id, user_id, week_start, tests_taken, avg_score, study_hours             |
| `recommendations`   | id, user_id, title, description, priority, category, is_completed        |
| `scanned_papers`    | id, user_id, image_url, extracted_text, parsed_questions (jsonb)          |

### 2.3 Storage bucket
Create a public bucket named **`scanned-papers`** for OCR image uploads.

---

## 3 — Docker Deployment

### 3.1 Build the Docker image
```bash
docker build -t examai-backend .
```

### 3.2 Run the container
```bash
docker run -d \
  --name examai-backend \
  -p 8000:8000 \
  --env-file .env \
  examai-backend
```

### 3.3 Verify it's running
```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"1.0.0"}
```

---

## 4 — API Endpoints Reference

| Method | Endpoint                                | Description                          |
|--------|-----------------------------------------|--------------------------------------|
| GET    | `/`                                     | Root — confirms API is running       |
| GET    | `/health`                               | Health check                         |
| POST   | `/api/auth/register`                    | Register a new user                  |
| POST   | `/api/auth/login`                       | Login & receive JWT                  |
| GET    | `/api/auth/profile`                     | Get current user profile             |
| PUT    | `/api/auth/profile`                     | Update user profile                  |
| GET    | `/api/tests/`                           | List all tests                       |
| GET    | `/api/tests/{test_id}`                  | Get test details                     |
| GET    | `/api/tests/{test_id}/questions`        | Get test questions                   |
| POST   | `/api/tests/submit`                     | Submit a test attempt                |
| GET    | `/api/tests/attempts/history`           | User's test attempt history          |
| GET    | `/api/tests/attempts/{attempt_id}/detail` | Detailed attempt result            |
| GET    | `/api/analytics/overview`               | Performance overview                 |
| GET    | `/api/analytics/subject/{subject}`      | Subject-level analytics              |
| GET    | `/api/analytics/progress`               | Weekly progress trend                |
| GET    | `/api/analytics/prediction`             | AI score prediction                  |
| GET    | `/api/recommendations/`                 | Get AI recommendations               |
| POST   | `/api/recommendations/refresh`          | Regenerate recommendations           |
| PUT    | `/api/recommendations/{rec_id}/complete`| Mark recommendation as done          |
| POST   | `/api/ocr/scan`                         | Upload & scan an answer sheet        |
| GET    | `/api/ocr/papers`                       | List scanned papers                  |
| GET    | `/api/ocr/papers/{paper_id}`            | Get scanned paper detail             |

---

## 5 — Production Checklist

- [ ] Set a **strong, unique `SECRET_KEY`** in `.env`
- [ ] Restrict `allow_origins` in CORS middleware to your Flutter app's domain
- [ ] Enable **Row Level Security (RLS)** on all Supabase tables
- [ ] Set `--workers` in the Dockerfile `CMD` to match your CPU count
- [ ] Configure HTTPS via a reverse proxy (Nginx / Caddy / cloud LB)
- [ ] Add structured logging (e.g. `loguru` or Python `logging`)
- [ ] Set up monitoring / alerting on the `/health` endpoint
- [ ] Pin the Docker base image digest for reproducible builds
- [ ] Run `pip audit` to check for known vulnerabilities

---

## 6 — Project Structure

```
Aiexambackend/
├── main.py                  # FastAPI app entry point
├── Dockerfile               # Multi-stage Docker build
├── .dockerignore            # Files excluded from Docker build
├── .env.example             # Template for environment variables
├── requirements.txt         # Pinned Python dependencies
├── models/                  # Pydantic request/response schemas
│   ├── user.py
│   ├── test.py
│   └── analytics.py
├── routers/                 # API route handlers
│   ├── auth.py
│   ├── tests.py
│   ├── analytics.py
│   ├── recommendations.py
│   └── ocr.py
├── services/                # Business logic & integrations
│   ├── ai_service.py        # Rule-based + OpenAI analysis
│   ├── ocr_service.py       # Tesseract OCR processing
│   └── supabase_service.py  # Supabase DB & Auth client
└── utils/
    └── helpers.py           # JWT, hashing, utility functions
```
