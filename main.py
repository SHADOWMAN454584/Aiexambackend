"""
ExamAI Backend — FastAPI Entry Point
AI-Powered Competitive Exam Performance Analytics API

Run locally:   python main.py
Deployed on:   Vercel (via vercel.json)
"""
import subprocess
import sys
import os


def _ensure_dependencies():
    """Auto-install requirements.txt if a key package is missing."""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError:
        print("[*] First run — installing dependencies …")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )


if __name__ == "__main__":
    _ensure_dependencies()

# ── App setup (always runs — needed for Vercel and local) ─────────
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="ExamAI Backend",
    description="AI-Powered Competitive Exam Performance Analytics API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow Flutter app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "ExamAI API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}


# Import and include routers
from routers import auth, tests, analytics, recommendations, ocr, documents

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(tests.router, prefix="/api/tests", tags=["Tests"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recommendations"])
app.include_router(ocr.router, prefix="/api/ocr", tags=["OCR"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])

if __name__ == "__main__":
    import uvicorn
    print()
    print("=" * 55)
    print("  ExamAI Backend running at http://localhost:8000")
    print("  API docs at        http://localhost:8000/docs")
    print("  Press Ctrl+C to stop")
    print("=" * 55)
    print()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
