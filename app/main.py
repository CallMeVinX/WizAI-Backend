"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import engine, Base

from app.models import Lead, DedupeCandidate, FormSubmission  # noqa: F401
from app.routers import leads, ingest, dedupe, dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database schemas on startup."""
    logger.info("Initializing database schemas...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schemas initialized successfully")
    yield
    logger.info("Shutting down application...")


settings = get_settings()

app = FastAPI(
    title="WizzAI Lead Management System",
    description="Enterprise AI-Assisted Lead Management & Deduplication Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure Cross-Origin Resource Sharing (CORS)
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount application routers (specific paths first before parameterized {lead_id})
app.include_router(dedupe.router)
app.include_router(ingest.router)
app.include_router(leads.router)
app.include_router(dashboard.router)



@app.get("/", tags=["system"])
def root():
    """Root metadata probe returning service name, version, and OpenAPI docs link."""
    return {"message": "WizzAI Lead Management API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health", tags=["system"])
def health():
    """Liveness probe endpoint for container orchestrators and frontend telemetry."""
    return {"status": "ok"}

