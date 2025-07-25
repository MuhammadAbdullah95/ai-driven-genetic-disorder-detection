from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

import app.models as models, app.schemas as schemas
from app.database import SessionLocal
from .auth_utils import get_current_user
from app.schemas import MessageCreate, MessageOut
from utils import _handle_chat_logic

router = APIRouter(tags=["Chats"])

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 📥 Create a new chat
@router.post("/", response_model=schemas.ChatOut)
def create_chat(chat: schemas.ChatCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    new_chat = models.Chat(user_id=user.id, title=chat.title, chat_type=chat.chat_type)
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return new_chat

# 🥗 Create a new diet planner chat
@router.post("/diet-planner", response_model=schemas.ChatOut)
def create_diet_planner_chat(chat: schemas.ChatCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    new_chat = models.Chat(user_id=user.id, title=chat.title or "Diet Planner Chat", chat_type="diet_planner")
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return new_chat
    

# 📜 Get all chats for a user
@router.get("/", response_model=List[schemas.ChatOut])
def list_chats(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Chat).filter(models.Chat.user_id == user.id).order_by(models.Chat.created_at.desc()).all()

# 🔁 Get full chat (with messages)
@router.get("/{chat_id}", response_model=schemas.ChatWithMessages)
def get_chat(chat_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    chat = db.query(models.Chat).filter_by(id=chat_id, user_id=user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    return chat

# 🗑️ Delete a chat
@router.delete("/{chat_id}", status_code=204)
def delete_chat(chat_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    chat = db.query(models.Chat).filter_by(id=chat_id, user_id=user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    db.delete(chat)
    db.commit()
    return None

@router.post("/{chat_id}/messages", response_model=dict)
async def send_message(chat_id: int, message: MessageCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    chat = db.query(models.Chat).filter_by(id=chat_id, user_id=user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return await _handle_chat_logic(chat, message.content, None, db)

@router.post("/{chat_id}/messages/file", response_model=dict)
async def send_file_message(chat_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    chat = db.query(models.Chat).filter_by(id=chat_id, user_id=user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return await _handle_chat_logic(chat, None, file, db)

@router.delete("/messages/{message_id}", status_code=204)
def delete_message(message_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    msg = db.query(models.Message).join(models.Chat).filter(models.Message.id == message_id, models.Chat.user_id == user.id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    db.delete(msg)
    db.commit()
    return None
