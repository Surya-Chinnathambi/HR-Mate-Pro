import sys
import asyncio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from app.database import create_db_and_tables

# Set Windows event loop policy for psycopg async compatibility
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Import API routers
from app.api import (
    auth, employees, attendance, leaves, payroll, realtime, ai, policies, chatbot, 
    work_assignments, approvals, websocket, scheduler as scheduler_api, analytics, 
    chat, broadcasts, group_chat, performance, onboarding, training, helpdesk
)
from app.services.scheduler import start_scheduler, stop_scheduler

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "avatars").mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting HRMS Backend...")
    create_db_and_tables()
    print("✅ Database tables created")
    
    # Start background scheduler
    start_scheduler()
    print("✅ APScheduler started with 5 background jobs")
    
    yield
    
    # Shutdown
    print("👋 Shutting down HRMS Backend...")
    stop_scheduler()
    print("✅ APScheduler stopped")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return JSONResponse(
        content={
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION
        }
    )

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(leaves.router, prefix="/api/leaves", tags=["Leaves"])
app.include_router(payroll.router, prefix="/api/payroll", tags=["Payroll"])
app.include_router(realtime.router, prefix="/api/realtime", tags=["Realtime"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(policies.router, prefix="/api", tags=["Policies"])
app.include_router(chatbot.router, prefix="/api", tags=["AI Chatbot"])
app.include_router(work_assignments.router, prefix="/api", tags=["Work Assignments"])
app.include_router(approvals.router, prefix="/api", tags=["Approvals"])
app.include_router(websocket.router, prefix="/api", tags=["WebSocket"])
app.include_router(scheduler_api.router, prefix="/api/scheduler", tags=["Scheduler"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(broadcasts.router, prefix="/api", tags=["Broadcasts"])
app.include_router(group_chat.router, prefix="/api", tags=["Group Chat"])

# New Feature Routers (6-10)
app.include_router(performance.router, prefix="/api", tags=["Performance"])
app.include_router(onboarding.router, prefix="/api", tags=["Onboarding"])
app.include_router(training.router, prefix="/api", tags=["Training"])
app.include_router(helpdesk.router, prefix="/api", tags=["IT Helpdesk"])

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Mount Socket.IO app for WebSocket connections
app.mount("/ws", websocket.socket_app)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to HRMS Backend API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )