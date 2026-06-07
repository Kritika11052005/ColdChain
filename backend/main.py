from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import pipeline, websocket, history
from models.database import init_db

app = FastAPI(
    title="ColdChain API",
    description="Automated B2B Cold Outreach Pipeline Engine",
    version="1.0.0"
)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

@app.on_event("startup")
async def startup_event():
    await init_db()

# Include Routers
app.include_router(pipeline.router)
app.include_router(websocket.router)
app.include_router(history.router)

@app.get("/")
async def root():
    return {"status": "online", "service": "coldchain-backend"}
