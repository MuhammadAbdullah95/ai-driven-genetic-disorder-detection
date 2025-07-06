"""
AI-Driven Genetic Disorder Detection API

A FastAPI-based application for analyzing genetic variants and providing
clinical insights using AI agents with search capabilities.

Author: MuhammadAbdullah95
Version: 1.0.0
"""

import os
import logging
import shutil
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from tools.google_search_tool import google_search
from tools.tavily_search_tool import tavily_search

from app.routers import auth, chat, message
from app.routers.auth_utils import get_current_user
from app.database import SessionLocal, engine
import app.models as models
from utils import parse_vcf_comprehensive, parse_vcf, get_agent, annotate_with_search, _handle_chat_logic
from custom_types import VariantInfo

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY environment variable is required")

# Set environment variables for tools
os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY

# Create uploads directory
os.makedirs("uploads", exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting AI-Driven Genetic Disorder Detection API...")
    
    # Create database tables
    try:
        models.Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI-Driven Genetic Disorder Detection API...")

# Initialize FastAPI app
app = FastAPI(
    title="AI-Driven Genetic Disorder Detection API",
    description="""
    A comprehensive API for analyzing genetic variants and providing clinical insights.
    
    ## Features
    
    * **VCF File Analysis**: Upload and analyze VCF files containing genetic variants
    * **AI-Powered Insights**: Get detailed clinical analysis using AI agents
    * **Chat Interface**: Interactive chat sessions for genetic analysis
    * **Authentication**: Secure user authentication and session management
    * **Sample Genotype Support**: Handle VCF files with sample genotype data
    
    ## Authentication
    
    Most endpoints require authentication. Use the `/auth/register` and `/auth/login` 
    endpoints to create an account and get an access token.
    
    Include the token in the Authorization header: `Bearer <your-token>`
    """,
    version="1.0.0",
    contact={
        "name": "MuhammadAbdullah95",
        "email": "ma2404374@gmail.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/chats", tags=["Chat Management"])
app.include_router(message.router, prefix="/chats", tags=["Chat Messages"])

# Pydantic models for API documentation
class MessageInput(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the chat session")
    message: str = Field(..., min_length=1, description="The user's message")

class ChatResponse(BaseModel):
    session_id: str = Field(..., description="Chat session identifier")
    response: str = Field(..., description="AI response to the user message")
    chat_history: List[Dict] = Field(..., description="Complete chat history")
    chat_title: str = Field(..., description="Title of the chat session")

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for frontend handling")

# Database dependency
def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses."""
    logger.info(f"Request: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        logger.info(f"Response: {request.method} {request.url} - Status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url} - Error: {str(e)}")
        raise

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }
    )

@app.get("/", tags=["Health Check"])
async def root():
    """
    Health check endpoint.
    
    Returns basic information about the API status.
    """
    return {
        "message": "AI-Driven Genetic Disorder Detection API",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs"
    }

@app.get("/health", tags=["Health Check"])
async def health_check():
    """
    Detailed health check endpoint.
    
    Checks the status of all critical components.
    """
    health_status = {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "components": {
            "database": "healthy",
            "ai_model": "healthy",
            "search_tools": "healthy"
        }
    }
    
    # Check database connection
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = f"error: {str(e)}"
    
    # Check AI model
    try:
        if not GEMINI_API_KEY:
            health_status["components"]["ai_model"] = "error: Missing API key"
    except Exception as e:
        health_status["components"]["ai_model"] = f"error: {str(e)}"
    
    # Check search tools
    try:
        if not TAVILY_API_KEY:
            health_status["components"]["search_tools"] = "error: Missing API key"
    except Exception as e:
        health_status["components"]["search_tools"] = f"error: {str(e)}"
    
    return health_status

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(
    session_id: Optional[str] = Form(None, description="Existing chat session ID"),
    message: Optional[str] = Form(None, description="Text message from user"),
    file: Optional[UploadFile] = File(None, description="VCF file to analyze"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """
    Unified chat endpoint for genetic analysis.
    
    This endpoint handles both text messages and VCF file uploads for genetic analysis.
    It supports both new chat sessions and continuing existing ones.
    
    **Features:**
    - Text-based genetic queries
    - VCF file analysis with comprehensive variant parsing
    - Sample genotype data support
    - AI-powered clinical insights
    - Persistent chat history
    
    **Authentication:** Required
    
    **File Formats:** VCF (Variant Call Format) files
    
    **Response:** Chat session with AI analysis and complete history
    """
    try:
        # Validate input
        if not message and not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either message or file must be provided"
            )
        
        # Validate file type if provided
        if file:
            if not file.filename.lower().endswith(('.vcf', '.vcf.gz')):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only VCF files are supported"
                )
            
            # Check file size (limit to 10MB)
            if file.size and file.size > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File size must be less than 10MB"
                )
        
        # Get or create chat session
        chat = None
        if session_id:
            chat = db.query(models.Chat).filter_by(id=session_id, user_id=user.id).first()
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )
        
        if not chat:
            chat = models.Chat(user_id=user.id, title="New Chat")
            db.add(chat)
            db.commit()
            db.refresh(chat)
        
        session_id = str(chat.id)
        
        # Process the request
        result = await _handle_chat_logic(chat, message, file, db)
        
        return ChatResponse(
            session_id=result["session_id"],
            response=result["response"],
            chat_history=result["chat_history"],
            chat_title=result["chat_title"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )

@app.post("/analyze", tags=["Analysis"])
async def analyze_vcf_endpoint(
    file: UploadFile = File(..., description="VCF file to analyze"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """
    Direct VCF analysis endpoint.
    
    Analyzes a VCF file and returns detailed genetic variant information
    without creating a chat session. Useful for one-time analysis.
    
    **Authentication:** Required
    
    **File Formats:** VCF (Variant Call Format) files
    
    **Response:** Detailed analysis of all variants in the file
    """
    try:
        # Validate file
        if not file.filename.lower().endswith(('.vcf', '.vcf.gz')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only VCF files are supported"
            )
        
        # Save file
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved: {file_path}")
        
        # Parse VCF file
        try:
            variants = parse_vcf_comprehensive(file_path)
        except Exception as e:
            logger.warning(f"Comprehensive parsing failed, trying basic: {e}")
            variants = parse_vcf(file_path)
        
        if not variants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid variants found in VCF file"
            )
        
        # Analyze variants
        summaries = await annotate_with_search(variants)
        
        # Create or get chat for storage
        chat = db.query(models.Chat).filter_by(user_id=user.id).order_by(models.Chat.created_at.desc()).first()
        if not chat:
            chat = models.Chat(user_id=user.id, title=f"Analysis: {file.filename}")
            db.add(chat)
            db.commit()
            db.refresh(chat)
        
        # Store analysis
        user_msg = models.Message(chat_id=chat.id, role="user", content=f"Analyze file: {file.filename}")
        db.add(user_msg)
        
        summary_text = "\n".join([
            f"{v.chromosome}:{v.position} {v.gene} {v.reference}->{v.alternate}: {v.search_summary}" 
            for v in summaries
        ])
        assistant_msg = models.Message(chat_id=chat.id, role="assistant", content=summary_text)
        db.add(assistant_msg)
        db.commit()
        
        return {
            "message": "Analysis complete",
            "chat_id": str(chat.id),
            "variants_analyzed": len(summaries),
            "results": [s.model_dump() for s in summaries]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analyze endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the VCF file"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
