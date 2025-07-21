from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Path
from sqlalchemy.orm import Session
from app.models import User, Chat, Message
from app.schemas import MessageOut
from app.database import SessionLocal
from .auth_utils import get_current_user
from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI
from agents.run import RunConfig
from tools.google_search_tool import google_search
from tools.tavily_search_tool import tavily_search
from utils import _handle_chat_logic
from typing import Optional
import shutil
import os

router = APIRouter(tags=["Messages"])

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# external_client = AsyncOpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)

external_client = AsyncOpenAI(api_key=GEMINI_API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
model = OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=external_client)
run_config = RunConfig(model=model, model_provider=external_client, tracing_disabled=True)

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_agent():
    """Get the configured agent for genetic disorder detection."""
    return Agent(
        name="Genetic Disorder Detector",
        instructions=(
            "You are a clinical geneticist assistant AI focused on genetic disorders and variant analysis. "
            "You have access to two search tools:\n"
            "1. 'tavily_search' — for scientific, gene-specific, mutation-level medical information from databases like ClinVar, OMIM, PubMed.\n"
            "2. 'google_search' — for broader context such as symptoms, patient-facing content, and public information.\n\n"
            "IMPORTANT INSTRUCTIONS:\n"
            "- ALWAYS use the search tools to find information about the genetic variant provided.\n"
            "- Search for the specific gene name, variant position, and mutation details.\n"
            "- Look for disease associations, clinical significance, and reported risks.\n"
            "- Provide detailed, accurate information about the genetic variant's medical implications.\n"
            "- Use scientific terminology appropriately but explain in accessible language.\n"
            "- If no specific information is found, search for general information about the gene and its function.\n"
            "- Do not make up information - only report what you find through searches.\n\n"
            "When analyzing a variant, provide:\n"
            "1. Gene function and normal role in the body\n"
            "2. Disease associations and clinical significance\n"
            "3. Inheritance patterns if known\n"
            "4. Available treatments or management strategies\n"
            "5. Risk assessment and recommendations"
        ),
        tools=[google_search, tavily_search]
    )



# @router.post("/{chat_id}/message")
# async def send_message(
#     chat_id: int = Path(..., description="ID of the chat to send a message to"),
#     message: Optional[str] = Form(None),
#     file: Optional[UploadFile] = File(None),
#     db: Session = Depends(get_db),
#     user: User = Depends(get_current_user)
# ):
#     chat = db.query(Chat).filter_by(id=chat_id, user_id=user.id).first()
#     if not chat:
#         raise HTTPException(status_code=404, detail="Chat not found")
#     return await _handle_chat_logic(chat, message, file, db)


# Helper for VCF parsing and annotation (reuse from main.py or import if possible)

