-- ============================================================
-- ExamAI — Supabase Database Schema
-- Run this entire file in the Supabase SQL Editor once.
-- ============================================================

-- Enable UUID extension (already on by default in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. PROFILES
--    One row per auth.users entry — created on registration.
-- ============================================================
CREATE TABLE IF NOT EXISTS profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    full_name       TEXT        NOT NULL,
    email           TEXT        NOT NULL UNIQUE,
    avatar_url      TEXT,
    exam_target     TEXT        NOT NULL DEFAULT 'JEE Main',
    study_hours     INT         DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at on every row change
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 2. TESTS
--    Mock exam papers available within the platform.
-- ============================================================
CREATE TABLE IF NOT EXISTS tests (
    id               UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    title            TEXT        NOT NULL,
    description      TEXT,
    exam_type        TEXT        NOT NULL DEFAULT 'JEE Main',
    duration_minutes INT         NOT NULL DEFAULT 180,
    total_marks      INT         NOT NULL DEFAULT 300,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 3. QUESTIONS
--    Individual MCQ questions belonging to a test.
-- ============================================================
CREATE TABLE IF NOT EXISTS questions (
    id               UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id          UUID        NOT NULL REFERENCES tests (id) ON DELETE CASCADE,
    subject          TEXT        NOT NULL,   -- Physics | Chemistry | Maths | Biology
    topic            TEXT        NOT NULL,
    difficulty       TEXT        NOT NULL DEFAULT 'Medium', -- Easy | Medium | Hard
    question_text    TEXT        NOT NULL,
    option_a         TEXT        NOT NULL,
    option_b         TEXT        NOT NULL,
    option_c         TEXT        NOT NULL,
    option_d         TEXT        NOT NULL,
    correct_option   CHAR(1)     NOT NULL CHECK (correct_option IN ('A','B','C','D')),
    explanation      TEXT,
    marks            INT         NOT NULL DEFAULT 4,
    negative_marks   INT         NOT NULL DEFAULT 1,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_questions_test_id  ON questions (test_id);
CREATE INDEX IF NOT EXISTS idx_questions_subject   ON questions (subject);

-- ============================================================
-- 4. TEST ATTEMPTS
--    One row every time a user submits a test.
-- ============================================================
CREATE TABLE IF NOT EXISTS test_attempts (
    id                   UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id              UUID        NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    test_id              UUID        NOT NULL REFERENCES tests (id) ON DELETE CASCADE,
    score                INT         NOT NULL DEFAULT 0,
    total_marks          INT         NOT NULL DEFAULT 0,
    percentage           NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    time_taken_minutes   INT,
    submitted_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_test_attempts_user_id  ON test_attempts (user_id);
CREATE INDEX IF NOT EXISTS idx_test_attempts_test_id  ON test_attempts (test_id);

-- ============================================================
-- 5. QUESTION RESPONSES
--    Individual answer selected by the user in one attempt.
-- ============================================================
CREATE TABLE IF NOT EXISTS question_responses (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    attempt_id          UUID        NOT NULL REFERENCES test_attempts (id) ON DELETE CASCADE,
    question_id         UUID        NOT NULL REFERENCES questions (id) ON DELETE CASCADE,
    selected_option     CHAR(1)     CHECK (selected_option IN ('A','B','C','D')),  -- NULL = skipped
    is_correct          BOOLEAN     NOT NULL DEFAULT FALSE,
    time_spent_seconds  INT
);

CREATE INDEX IF NOT EXISTS idx_qresponses_attempt_id  ON question_responses (attempt_id);
CREATE INDEX IF NOT EXISTS idx_qresponses_question_id ON question_responses (question_id);

-- ============================================================
-- 6. WEEKLY PROGRESS
--    Aggregated per-week snapshot used for trend charts.
-- ============================================================
CREATE TABLE IF NOT EXISTS weekly_progress (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID        NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    week_start          DATE        NOT NULL,
    average_score       NUMERIC(5,2) DEFAULT 0.00,
    tests_taken         INT          DEFAULT 0,
    total_time_minutes  INT          DEFAULT 0,
    physics_avg         NUMERIC(5,2) DEFAULT 0.00,
    chemistry_avg       NUMERIC(5,2) DEFAULT 0.00,
    maths_avg           NUMERIC(5,2) DEFAULT 0.00,
    biology_avg         NUMERIC(5,2) DEFAULT 0.00,
    UNIQUE (user_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_weekly_progress_user_id ON weekly_progress (user_id);

-- ============================================================
-- 7. RECOMMENDATIONS
--    AI-generated study tasks for each user.
-- ============================================================
CREATE TABLE IF NOT EXISTS recommendations (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID        NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    title           TEXT        NOT NULL,
    description     TEXT,
    subject         TEXT        NOT NULL,
    priority        TEXT        NOT NULL DEFAULT 'Medium', -- High | Medium | Low
    type            TEXT        NOT NULL DEFAULT 'practice', -- practice | revision | concept
    estimated_time  TEXT,                                    -- e.g. "30 mins"
    is_completed    BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recommendations_user_id ON recommendations (user_id);

-- ============================================================
-- 8. SCANNED PAPERS
--    Records of answer-sheet images uploaded for OCR.
-- ============================================================
CREATE TABLE IF NOT EXISTS scanned_papers (
    id                   UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id              UUID        NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    exam_type            TEXT        NOT NULL DEFAULT 'JEE Main',
    year                 INT,
    image_url            TEXT,
    extracted_text       TEXT,
    questions_extracted  INT          NOT NULL DEFAULT 0,
    status               TEXT        NOT NULL DEFAULT 'processing', -- processing | done | failed
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scanned_papers_user_id ON scanned_papers (user_id);

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Enable RLS on every user-data table
ALTER TABLE profiles          ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_attempts     ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_progress   ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendations   ENABLE ROW LEVEL SECURITY;
ALTER TABLE scanned_papers    ENABLE ROW LEVEL SECURITY;

-- Tests and questions are public (read) — no RLS needed unless you want private tests.
-- Uncomment the lines below if you want only admins to create tests/questions.
-- ALTER TABLE tests     ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE questions ENABLE ROW LEVEL SECURITY;

-- ── Profiles ──────────────────────────────────────────────────────
CREATE POLICY "profiles: owner can view"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "profiles: owner can update"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "profiles: service role can insert"
    ON profiles FOR INSERT
    WITH CHECK (TRUE);   -- backend uses service-role key

-- ── Test Attempts ─────────────────────────────────────────────────
CREATE POLICY "test_attempts: owner can view"
    ON test_attempts FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "test_attempts: service role can insert"
    ON test_attempts FOR INSERT
    WITH CHECK (TRUE);

-- ── Question Responses ────────────────────────────────────────────
CREATE POLICY "question_responses: owner can view via attempt"
    ON question_responses FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM test_attempts ta
            WHERE ta.id = question_responses.attempt_id
              AND ta.user_id = auth.uid()
        )
    );

CREATE POLICY "question_responses: service role can insert"
    ON question_responses FOR INSERT
    WITH CHECK (TRUE);

-- ── Weekly Progress ───────────────────────────────────────────────
CREATE POLICY "weekly_progress: owner can view"
    ON weekly_progress FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "weekly_progress: service role can upsert"
    ON weekly_progress FOR ALL
    WITH CHECK (TRUE);

-- ── Recommendations ───────────────────────────────────────────────
CREATE POLICY "recommendations: owner can view"
    ON recommendations FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "recommendations: owner can update (mark complete)"
    ON recommendations FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "recommendations: service role can insert"
    ON recommendations FOR INSERT
    WITH CHECK (TRUE);

-- ── Scanned Papers ────────────────────────────────────────────────
CREATE POLICY "scanned_papers: owner can view"
    ON scanned_papers FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "scanned_papers: service role can all"
    ON scanned_papers FOR ALL
    WITH CHECK (TRUE);

-- ============================================================
-- STORAGE BUCKET  (run via Supabase dashboard or API)
-- ============================================================
-- Create a public bucket named "scanned-papers" for OCR image uploads.
-- You can do this from: Storage → New Bucket → name: scanned-papers → Public: true
-- Or via the management API:
--   POST /storage/v1/bucket  { "id": "scanned-papers", "public": true }

-- ============================================================
-- SEED DATA — sample tests & questions (optional)
-- ============================================================
-- Uncomment the block below to insert a sample JEE Main test with
-- two questions so the app has content to display immediately.

/*
INSERT INTO tests (id, title, description, exam_type, duration_minutes, total_marks)
VALUES (
    'aaaaaaaa-0000-0000-0000-000000000001',
    'JEE Main — Full Mock Test 1',
    'Complete 90-question mock test covering Physics, Chemistry & Maths.',
    'JEE Main', 180, 300
);

INSERT INTO questions
    (test_id, subject, topic, difficulty, question_text,
     option_a, option_b, option_c, option_d, correct_option, explanation, marks, negative_marks)
VALUES
(
    'aaaaaaaa-0000-0000-0000-000000000001',
    'Physics', 'Kinematics', 'Medium',
    'A particle moves with velocity v = 3t² − 6t + 4 m/s. What is the acceleration at t = 2 s?',
    '6 m/s²', '12 m/s²', '4 m/s²', '0 m/s²',
    'A',
    'a = dv/dt = 6t − 6; at t=2 s → 12 − 6 = 6 m/s².',
    4, 1
),
(
    'aaaaaaaa-0000-0000-0000-000000000001',
    'Chemistry', 'Periodic Table', 'Easy',
    'Which element has the highest electronegativity?',
    'Oxygen', 'Chlorine', 'Fluorine', 'Nitrogen',
    'C',
    'Fluorine (F) has the highest electronegativity value of 3.98 on the Pauling scale.',
    4, 1
);
*/
