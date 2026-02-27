"""
ExamAI Backend — FastAPI Entry Point
AI-Powered Competitive Exam Performance Analytics API
"""
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
from routers import auth, tests, analytics, recommendations, ocr

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(tests.router, prefix="/api/tests", tags=["Tests"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recommendations"])
app.include_router(ocr.router, prefix="/api/ocr", tags=["OCR"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
