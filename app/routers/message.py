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
from typing import Optional
import shutil
import os

router = APIRouter(prefix="/chats", tags=["Messages"])

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_agent():
    return Agent(
        name="Genetic Disorder Detector",
        instructions=(
            "You are a clinical assistant AI focused on genetic disorders. "
            "You have access to two tools:\n"
            "1. 'tavily_search' — for scientific, gene-specific, mutation-level medical information.\n"
            "2. 'google_search' — for broader context such as symptoms, patient-facing content, and public info.\n"
            "Use 'tavily_search' first. If the result is weak or empty, try 'google_search'.\n"
            "Do not search anything unrelated to genetics or medicine.\n\n"
            "Given variant data and search results, summarize the variant's disease association, clinical relevance, and any reported risks. "
            "Be concise, accurate, and use non-technical language where possible."
        ),
        tools=[google_search, tavily_search]
    )

async def handle_agentic_message(chat, message, file, db):
    response_text = None
    last_user_content = None

    if file is not None:
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        variants = parse_vcf(file_path)
        summaries = await annotate_with_search(variants)
        summary_text = "\n".join([
            f"{v['chromosome']}:{v['position']} {v['gene']} {v['reference']}->{v['alternate']}: {v['search_summary']}" for v in summaries
        ])
        user_msg = Message(chat_id=chat.id, role="user", content=f"Uploaded VCF: {file.filename}")
        assistant_msg = Message(chat_id=chat.id, role="assistant", content=summary_text)
        db.add_all([user_msg, assistant_msg])
        db.commit()
        response_text = summary_text
        last_user_content = f"Uploaded VCF: {file.filename}"

    if message is not None and message.strip():
        user_msg = Message(chat_id=chat.id, role="user", content=message.strip())
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        history = db.query(Message).filter_by(chat_id=chat.id).order_by(Message.created_at.asc()).all()
        chat_history = [{"role": m.role, "content": m.content} for m in history]
        try:
            result = await Runner.run(
                starting_agent=get_agent(),
                input=chat_history,
                run_config=RunConfig(model=None, model_provider=None, tracing_disabled=True)  # Use your config
            )
            bot_reply = result.final_output or "🤖 (no reply generated)"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
        assistant_msg = Message(chat_id=chat.id, role="assistant", content=bot_reply)
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
        response_text = bot_reply
        last_user_content = message.strip()

    if not message and not file:
        raise HTTPException(status_code=400, detail="You must provide either a message or a VCF file.")

    # Auto-generate chat title if needed
    if chat.title == "New Chat" and last_user_content:
        title_rename_agent = Agent(name="Title renamer", instructions="Generate a short, clear title for this conversation.")
        try:
            title_result = await Runner.run(
                starting_agent=title_rename_agent,
                input=last_user_content,
                run_config=RunConfig(model=None, model_provider=None, tracing_disabled=True)  # Use your config
            )
            new_title = title_result.final_output.strip().replace('"', '')
            chat.title = new_title
            db.commit()
        except Exception as e:
            print(f"[Warning] Failed to auto-generate title: {e}")

    # Return the chat history and title
    messages = db.query(Message).filter_by(chat_id=chat.id).order_by(Message.created_at.asc()).all()
    chat_history = [
        {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages
    ]
    return {
        "session_id": str(chat.id),
        "response": response_text,
        "chat_history": chat_history,
        "chat_title": chat.title
    }

@router.post("/{chat_id}/message")
async def send_message(
    chat_id: int = Path(..., description="ID of the chat to send a message to"),
    message: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    chat = db.query(Chat).filter_by(id=chat_id, user_id=user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return await handle_agentic_message(chat, message, file, db)

# Helper for VCF parsing and annotation (reuse from main.py or import if possible)
def parse_vcf(file_path: str):
    results = []
    with open(file_path) as f:
        for line in f:
            if line.startswith("#"):
                continue
            fields = line.strip().split("\t")
            if len(fields) < 8:
                continue
            chrom, pos, _id, ref, alt, qual, filt, info = fields[:8]
            gene = "Unknown"
            for entry in info.split(";"):
                if entry.startswith("GENE="):
                    gene = entry.split("=", 1)[1]
            results.append({
                "chromosome": chrom,
                "position": int(pos),
                "gene": gene,
                "reference": ref,
                "alternate": alt,
            })
    return results

async def annotate_with_search(variants):
    enriched = []
    agent = get_agent()
    for var in variants:
        query = f"{var['gene']} gene variant {var['reference']}->{var['alternate']} disease association"
        result = await Runner.run(agent, input=[{"role": "user", "content": query}], run_config=RunConfig(model=None, model_provider=None, tracing_disabled=True))
        enriched.append({
            "chromosome": var["chromosome"],
            "position": var["position"],
            "gene": var["gene"],
            "reference": var["reference"],
            "alternate": var["alternate"],
            "search_summary": result.final_output
        })
    return enriched
