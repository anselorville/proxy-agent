"""Main application entry point for FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from src.api import auth, stocks
from src.models.database import engine
from src.tasks.celery_app import celery_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting China Stock Proxy Service...")
    yield
    # Shutdown
    logger.info("Shutting down China Stock Proxy Service...")


# Create FastAPI app
app = FastAPI(
    title="A股金融数据代理服务",
    description="通过代理轮换和频率控制规避IP封禁的A股数据获取服务",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["Stock Data"])


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "China Stock Proxy Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "china-stock-proxy",
        "celery": "connected" if celery_app else "not configured"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
