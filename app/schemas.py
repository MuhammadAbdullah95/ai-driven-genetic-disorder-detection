from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# 📧 User Schema
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True

# 💬 Chat Schema
class ChatCreate(BaseModel):
    title: Optional[str] = "New Chat"
    chat_type: Optional[str] = "genetic"

class ChatOut(BaseModel):
    id: int
    title: str
    chat_type: str
    created_at: datetime

    class Config:
        from_attributes = True

# 🧾 Message Schema
class MessageCreate(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

# 📦 Full Chat with Messages (for frontend resume)
class ChatWithMessages(BaseModel):
    id: int
    title: str
    chat_type: str
    messages: List[MessageOut]

    class Config:
        from_attributes = True
