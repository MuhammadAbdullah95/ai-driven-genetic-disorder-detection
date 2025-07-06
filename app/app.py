from fastapi import FastAPI
from routers import auth, chat

app = FastAPI()

app.include_router(chat.router)
app.include_router(auth.router)
